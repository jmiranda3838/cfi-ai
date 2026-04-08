from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window, FormattedTextControl
from prompt_toolkit.styles import Style as PTStyle
from rich import box
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.theme import Theme

from cfi_ai import __version__

if TYPE_CHECKING:
    from cfi_ai.cost_tracker import CostTracker
    from cfi_ai.sessions import SessionMeta


@dataclass
class UserInput:
    """Result from get_input() carrying the text and which mode was active."""
    text: str
    plan_mode: bool = False


class PlanApproval(Enum):
    BYPASS = auto()    # Approve plan, auto-approve all edits
    APPROVE = auto()   # Approve plan, confirm each edit
    REJECT = auto()    # Reject, keep iterating

_APPROVAL_OPTIONS: list[tuple[PlanApproval, str]] = [
    (PlanApproval.BYPASS,  "Approve + bypass permissions"),
    (PlanApproval.APPROVE, "Approve + review each edit"),
    (PlanApproval.REJECT,  "Reject (keep iterating)"),
]

CFI_THEME = Theme({
    "primary": "dark_cyan",
    "accent": "dark_goldenrod",
    "muted": "grey62",
    "dim": "grey42",
    "border": "grey37",
    "error": "indian_red",
    "status": "cadet_blue",
})

MASCOT = """\
       /\\    /\\
      ( ■■  ■■ )
       \\ \\--/ /
        |    |
       /|~~~~|\\
      / | )( | \\
        |    |
        d    b"""

TAGLINE = "terminal clarity, one prompt at a time."

PT_STYLE = PTStyle.from_dict({
    "prompt": "#5f8787",
    "prompt-plan": "#af8700",
    "bottom-toolbar": "bg:#1c1c1c #585858",
    "bottom-toolbar-plan": "bg:#6b5300 #ffffff",
    "approval": "#af8700",
    "muted": "#9e9e9e",
})

MODE_DISPLAY = {
    "chatting": "ready",
    "chatting_plan": "PLAN MODE",
    "thinking": "thinking ..",
    "thinking_plan": "researching ..",
    "planning": "planning ..",
    "awaiting_approval": "awaiting approval",
    "interviewing": "interview ..",
    "executing": "executing ..",
}


def _format_tokens(n: int) -> str:
    """Compact token count: 950 -> '950', 12345 -> '12k', 1500000 -> '1.5M'."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def _format_cost_segment(tracker: "CostTracker | None") -> str:
    """Format the bottom-toolbar context/cost readout. Empty string before
    the first turn or when there's no tracker."""
    if tracker is None or tracker.last_prompt_tokens == 0:
        return ""

    used = _format_tokens(tracker.last_prompt_tokens)
    window = tracker.context_window()
    if window:
        pct = (tracker.last_prompt_tokens / window) * 100
        ctx = f"ctx {used}/{_format_tokens(window)} ({pct:.0f}%)"
    else:
        ctx = f"ctx {used}"

    if tracker.has_pricing():
        return f"{ctx} \u2022 ${tracker.total_cost_usd:.4f}"
    return ctx


class StatusManager:
    def __init__(self) -> None:
        self._mode = "chatting"

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        self._mode = mode

    @property
    def display(self) -> str:
        return MODE_DISPLAY.get(self._mode, self._mode)


def _chat_key_bindings(on_toggle_plan=None) -> KeyBindings:
    """Key bindings for the main multi-line chat prompt.

    Enter        → submit the buffer
    Alt+Enter    → insert a literal newline (compose multi-line messages)
    Escape       → cancel (return "")
    Ctrl+D       → disabled (no-op)
    Shift+Tab    → toggle plan mode (if callback provided)
    Ctrl+C raises KeyboardInterrupt by default; get_input() catches it to exit.

    The prompt runs with multiline=True so pasted multi-line content stays
    visible (single-line mode would hide everything except the line under the
    cursor). Enter is bound explicitly so submit-on-Enter UX is preserved.
    """
    kb = KeyBindings()

    @kb.add("enter")
    def _enter(event):
        event.current_buffer.validate_and_handle()

    @kb.add("escape", "enter")  # Alt+Enter / Option+Enter
    def _alt_enter(event):
        event.current_buffer.insert_text("\n")

    @kb.add("escape")
    def _escape(event):
        event.app.exit(result="")

    @kb.add("c-d")
    def _ctrl_d(event):
        pass  # disabled

    @kb.add("s-tab")
    def _shift_tab(event):
        if on_toggle_plan is not None:
            on_toggle_plan()
            event.app.invalidate()

    return kb


def _multiline_key_bindings() -> KeyBindings:
    """Key bindings for the multiline transcript prompt.

    Enter → submit, Escape → cancel.
    Ctrl+C raises KeyboardInterrupt which propagates up to exit.
    """
    kb = KeyBindings()

    @kb.add("enter")
    def _enter(event):
        event.current_buffer.validate_and_handle()

    @kb.add("escape")
    def _escape(event):
        event.app.exit(exception=EOFError)

    @kb.add("c-d")
    def _ctrl_d(event):
        pass  # disabled

    return kb


def _interview_key_bindings() -> KeyBindings:
    """Key bindings for interview question prompts.

    Escape → cancel (EOFError), Ctrl+D → disabled.
    Ctrl+C raises KeyboardInterrupt by default.
    """
    kb = KeyBindings()

    @kb.add("escape")
    def _escape(event):
        event.app.exit(exception=EOFError)

    @kb.add("c-d")
    def _ctrl_d(event):
        pass  # disabled

    return kb


def _approval_key_bindings() -> KeyBindings:
    """Key bindings for the approve? [Y/n] prompt.

    Escape → raise EOFError so caller returns False (reject).
    Critically: Escape MUST NOT exit with result="" the way _chat_key_bindings
    does, because prompt_approval() treats "" as YES (capital-Y default), so
    a result="" exit would silently approve a mutation. Bare Enter on an empty
    line is still a valid approval — only Escape needs the special handling.
    Ctrl+C raises KeyboardInterrupt by default.
    """
    kb = KeyBindings()

    @kb.add("escape")
    def _escape(event):
        event.app.exit(exception=EOFError)

    @kb.add("c-d")
    def _ctrl_d(event):
        pass  # disabled

    return kb


class SlashMapCompleter(Completer):
    """Autocomplete for slash maps."""

    def __init__(self) -> None:
        self._maps: dict[str, str] = {}

    def set_maps(self, maps: dict[str, str]) -> None:
        self._maps = maps

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if " " in text or not text.startswith("/"):
            return
        prefix = text[1:]
        for name, desc in sorted(self._maps.items()):
            if name.startswith(prefix):
                yield Completion(name, start_position=-len(prefix), display_meta=desc)


class UI:
    def __init__(self) -> None:
        self.console = Console(theme=CFI_THEME)
        self.status = StatusManager()
        self._completer = SlashMapCompleter()
        self._plan_mode = False
        # Set by main.py once the model is known. The bottom-toolbar callable
        # reads from this between turns to display ctx + running cost.
        self.cost_tracker: "CostTracker | None" = None
        history_dir = Path.home() / ".cfi-ai"
        history_dir.mkdir(exist_ok=True)
        self.session: PromptSession[str] = PromptSession(
            history=FileHistory(str(history_dir / "history")),
            style=PT_STYLE,
            completer=self._completer,
        )

    @property
    def plan_mode(self) -> bool:
        return self._plan_mode

    def toggle_plan_mode(self) -> None:
        self.set_plan_mode(not self._plan_mode)

    def set_plan_mode(self, active: bool) -> None:
        self._plan_mode = active
        mode = "chatting_plan" if active else "chatting"
        self.status.set_mode(mode)

    def set_maps(self, maps: dict[str, str]) -> None:
        """Set the available slash maps for autocomplete."""
        self._completer.set_maps(maps)

    def print_welcome(self, workspace_path: str) -> None:
        self.console.print(f"[primary]{MASCOT}[/primary]")
        self.console.print()
        self.console.print(
            f"[primary]cfi-ai[/primary] [dim]v{__version__}[/dim]  "
            f"[accent]{TAGLINE}[/accent]"
        )
        self.console.print(f"[grey70]{workspace_path}[/grey70]")
        self.console.print()
        self.console.print("[muted]Ctrl+C to exit, Escape to cancel, Shift+Tab for plan mode.[/muted]")
        self.console.print(
            "[muted]Chats are stored locally for 30 days in ~/.config/cfi-ai/sessions/ "
            "(use /resume to reload).[/muted]"
        )
        self.console.print()

    def get_input(self) -> UserInput | None:
        """Prompt the user for input. Returns UserInput or None on Ctrl+C (exit)."""
        try:
            def _prompt_message():
                if self._plan_mode:
                    return [("class:prompt-plan bold", "@ ")]
                return [("class:prompt", "~ ")]

            def _toolbar():
                cost_segment = _format_cost_segment(self.cost_tracker)
                if self._plan_mode:
                    self.status.set_mode("chatting_plan")
                    segments = [
                        ("class:bottom-toolbar-plan bold", " [PLAN MODE] "),
                        ("class:bottom-toolbar-plan", f"cfi-ai | {self.status.display}  "),
                    ]
                    if cost_segment:
                        segments.append(
                            ("class:bottom-toolbar-plan", f"{cost_segment}  ")
                        )
                    segments.append(
                        ("class:bottom-toolbar-plan italic", "Shift+Tab to exit plan mode ")
                    )
                    return segments
                mode = "chatting_plan" if self._plan_mode else "chatting"
                self.status.set_mode(mode)
                display = self.status.display
                cost_html = f"  {cost_segment}" if cost_segment else ""
                return HTML(
                    f"cfi-ai | {display}{cost_html}"
                    "  <i>Shift+Tab to toggle plan mode</i>"
                )

            text = self.session.prompt(
                _prompt_message,
                bottom_toolbar=_toolbar,
                multiline=True,
                key_bindings=_chat_key_bindings(on_toggle_plan=self.toggle_plan_mode),
            )
            return UserInput(text=text, plan_mode=self._plan_mode)
        except (EOFError, KeyboardInterrupt):
            return None

    def stream_markdown(self, chunks: "Iterator") -> str:
        """Stream text chunks and render as markdown. Returns full accumulated text."""
        accumulated = ""
        with Live(Markdown(""), console=self.console, refresh_per_second=8) as live:
            for chunk in chunks:
                accumulated += chunk
                live.update(Markdown(accumulated))
        return accumulated

    def render_markdown(self, text: str) -> None:
        self.console.print(Markdown(text))

    def show_tool_call(self, name: str, input_summary: str) -> None:
        self.console.print(
            f"  [primary]>[/primary] [bold]{name}[/bold] [dim]{input_summary}[/dim]"
        )

    def show_tool_result(self, name: str, result: str) -> None:
        truncated = result[:1000] + ("..." if len(result) > 1000 else "")
        indented = "\n".join(f"    {line}" for line in truncated.splitlines())
        self.console.print(Text(indented, style="dim"))

    def show_plan(self, formatted_plan: str) -> None:
        self.console.print(
            Panel(
                formatted_plan,
                title="[accent]Execution Plan[/accent]",
                border_style="primary",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    def show_research_plan(self, plan_text: str) -> None:
        """Display the LLM's research plan for user review."""
        self.console.print(
            Panel(
                Markdown(plan_text),
                title="[accent]Implementation Plan[/accent]",
                border_style="accent",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    def prompt_plan_approval(self) -> PlanApproval:
        """Prompt user to approve or reject a plan with an interactive menu."""
        self.status.set_mode("awaiting_approval")
        try:
            return self._run_plan_approval_app()
        except KeyboardInterrupt:
            raise
        except EOFError:
            return PlanApproval.REJECT

    def _run_plan_approval_app(self) -> PlanApproval:
        """Run an interactive arrow-key selection menu for plan approval."""
        selected = [0]

        def _get_menu_text():
            fragments = [("class:approval", "  execute plan?\n\n")]
            for i, (_, label) in enumerate(_APPROVAL_OPTIONS):
                if i == selected[0]:
                    fragments.append(("class:approval", f"    \u25b6 {label}\n"))
                else:
                    fragments.append(("class:muted", f"      {label}\n"))
            fragments.append(("", "\n"))
            fragments.append(("class:muted", "  \u2191/\u2193 select  enter confirm  esc reject"))
            return fragments

        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            selected[0] = (selected[0] - 1) % len(_APPROVAL_OPTIONS)
            event.app.invalidate()

        @kb.add("down")
        def _down(event):
            selected[0] = (selected[0] + 1) % len(_APPROVAL_OPTIONS)
            event.app.invalidate()

        @kb.add("enter")
        def _enter(event):
            event.app.exit(result=_APPROVAL_OPTIONS[selected[0]][0])

        @kb.add("escape")
        def _escape(event):
            event.app.exit(result=PlanApproval.REJECT)

        @kb.add("c-c")
        def _ctrl_c(event):
            event.app.exit(exception=KeyboardInterrupt)

        layout = Layout(
            Window(
                FormattedTextControl(_get_menu_text, show_cursor=False),
                dont_extend_height=True,
            )
        )

        app: Application[PlanApproval] = Application(
            layout=layout,
            key_bindings=kb,
            style=PT_STYLE,
            erase_when_done=True,
            full_screen=False,
        )

        return app.run()

    def prompt_session_select(self, sessions: list[SessionMeta]) -> SessionMeta | None:
        """Show an arrow-key menu for picking a previous chat session.

        Returns the selected ``SessionMeta``, or ``None`` on Escape/Ctrl-C.
        """
        if not sessions:
            return None

        selected = [0]

        def _fmt_row(meta, is_selected: bool) -> str:
            from datetime import datetime as _dt

            try:
                ts = _dt.fromtimestamp(meta.updated_at).strftime("%b %d %H:%M")
            except (ValueError, OSError):
                ts = "???"
            preview = (meta.first_user_message or "(no text)").replace("\n", " ")
            if len(preview) > 70:
                preview = preview[:67] + "..."
            marker = "\u25b6" if is_selected else " "
            return f"  {marker} [{ts}] ({meta.message_count} msgs) {preview}"

        def _get_menu_text():
            fragments = [("class:approval", "  resume which session?\n\n")]
            for i, meta in enumerate(sessions):
                is_sel = i == selected[0]
                style = "class:approval" if is_sel else "class:muted"
                fragments.append((style, _fmt_row(meta, is_sel) + "\n"))
            fragments.append(("", "\n"))
            fragments.append(("class:muted", "  \u2191/\u2193 select  enter confirm  esc cancel"))
            return fragments

        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            selected[0] = (selected[0] - 1) % len(sessions)
            event.app.invalidate()

        @kb.add("down")
        def _down(event):
            selected[0] = (selected[0] + 1) % len(sessions)
            event.app.invalidate()

        @kb.add("enter")
        def _enter(event):
            event.app.exit(result=sessions[selected[0]])

        @kb.add("escape")
        def _escape(event):
            event.app.exit(result=None)

        @kb.add("c-c")
        def _ctrl_c(event):
            event.app.exit(exception=KeyboardInterrupt)

        layout = Layout(
            Window(
                FormattedTextControl(_get_menu_text, show_cursor=False),
                dont_extend_height=True,
            )
        )

        app: Application = Application(
            layout=layout,
            key_bindings=kb,
            style=PT_STYLE,
            erase_when_done=True,
            full_screen=False,
        )

        try:
            return app.run()
        except KeyboardInterrupt:
            return None
        except EOFError:
            return None

    def run_interview(self, questions: list[dict]) -> list[dict] | None:
        """Present interview questions one at a time.

        Returns list of {"id": ..., "answer": ...} dicts, or None if cancelled.
        Raises KeyboardInterrupt if Ctrl+C is pressed.
        """
        self.status.set_mode("interviewing")
        answers: list[dict] = []
        total = len(questions)

        for i, q in enumerate(questions, 1):
            qid = q.get("id", f"q{i}")
            text = q.get("text", "")
            options = q.get("options") or []
            multiline = q.get("multiline", False)
            default = q.get("default", "")

            # Header and question
            self.console.print(f"\n  [accent]Question {i} of {total}[/accent]")
            self.console.print(f"  [bold]{text}[/bold]")

            if options:
                for j, opt in enumerate(options, 1):
                    self.console.print(f"    [primary]{j}.[/primary] {opt}")
                self.console.print(f"  [dim]Enter a number, or type a custom answer.[/dim]")

            while True:
                try:
                    if multiline:
                        self.console.print("[dim]Enter to submit, Escape to cancel.[/dim]")
                        raw = self.session.prompt(
                            [("class:prompt", f"  {qid}> ")],
                            multiline=True,
                            key_bindings=_multiline_key_bindings(),
                        )
                    else:
                        if default:
                            prompt_text = f"  {qid} [{default}]> "
                        else:
                            prompt_text = f"  {qid}> "
                        raw = self.session.prompt(
                            [("class:prompt", prompt_text)],
                            multiline=False,
                            key_bindings=_interview_key_bindings(),
                        )
                except EOFError:
                    return None  # Escape → cancel entire interview

                if not raw.strip() and default:
                    raw = default
                    break
                if raw.strip():
                    break
                # Empty/whitespace input, no default — hint and re-prompt
                self.console.print("  [dim]Please enter a response, or press Escape to cancel.[/dim]")

            # Resolve numbered option selection
            if options and raw.strip().isdigit():
                idx = int(raw.strip()) - 1
                if 0 <= idx < len(options):
                    raw = options[idx]

            answers.append({"id": qid, "answer": raw.strip()})

        return answers

    def prompt_approval(self) -> bool:
        self.status.set_mode("awaiting_approval")
        try:
            response = self.session.prompt(
                [("class:approval", "approve? [Y/n] ")],
                bottom_toolbar=HTML(f"cfi-ai | {self.status.display}"),
                multiline=False,
                key_bindings=_approval_key_bindings(),
            )
            return response.strip().lower() in ("", "y", "yes")
        except KeyboardInterrupt:
            raise
        except EOFError:
            return False

    def prompt_multiline(self, instruction: str) -> str | None:
        """Prompt for multi-line input. Returns text or None on cancel."""
        self.console.print(f"[muted]{instruction}[/muted]")
        self.console.print("[dim]Enter to submit, Escape to cancel.[/dim]")
        try:
            return self.session.prompt(
                [("class:prompt", "transcript> ")],
                multiline=True,
                key_bindings=_multiline_key_bindings(),
            )
        except EOFError:
            return None

    def print_error(self, message: str) -> None:
        self.console.print(f"[error]error:[/error] {message}")

    def print_info(self, message: str) -> None:
        self.console.print(f"[muted]{message}[/muted]")

    def print_separator(self) -> None:
        self.console.print(Rule(style="dim"))

    def print_elapsed(self, seconds: float) -> None:
        if seconds >= 60:
            m = int(seconds) // 60
            s = int(seconds) % 60
            label = f"{m}m {s}s"
        else:
            label = f"{seconds:.1f}s"
        self.console.print(Text(label, style="dim"), justify="right")
