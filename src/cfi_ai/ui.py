from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
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


@dataclass
class UserInput:
    """Result from get_input() carrying the text and which mode was active."""
    text: str
    plan_mode: bool = False


class PlanApproval(Enum):
    CLEAR_BYPASS = auto()   # Y - clear context, bypass permissions
    BYPASS = auto()         # b - keep context, bypass permissions
    PERMISSIONS = auto()    # p - clear context, keep permissions
    REJECT = auto()         # n - reject

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
    "approval": "#af8700",
})

MODE_DISPLAY = {
    "chatting": "ready",
    "chatting_plan": "plan mode",
    "thinking": "thinking ..",
    "thinking_plan": "researching ..",
    "planning": "planning ..",
    "awaiting_approval": "awaiting approval",
    "executing": "executing ..",
}


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
    """Key bindings for the main chat prompt.

    Escape → cancel (return ""), Ctrl+D → disabled (no-op),
    Shift+Tab → toggle plan mode (if callback provided).
    Ctrl+C raises KeyboardInterrupt by default; get_input() catches it to exit.
    """
    kb = KeyBindings()

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


class SlashCommandCompleter(Completer):
    """Autocomplete for slash commands."""

    def __init__(self) -> None:
        self._commands: dict[str, str] = {}

    def set_commands(self, commands: dict[str, str]) -> None:
        self._commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if " " in text or not text.startswith("/"):
            return
        prefix = text[1:]
        for name, desc in sorted(self._commands.items()):
            if name.startswith(prefix):
                yield Completion(name, start_position=-len(prefix), display_meta=desc)


class UI:
    def __init__(self) -> None:
        self.console = Console(theme=CFI_THEME)
        self.status = StatusManager()
        self._completer = SlashCommandCompleter()
        self._plan_mode = False
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
        self._plan_mode = not self._plan_mode
        mode = "chatting_plan" if self._plan_mode else "chatting"
        self.status.set_mode(mode)

    def set_commands(self, commands: dict[str, str]) -> None:
        """Set the available slash commands for autocomplete."""
        self._completer.set_commands(commands)

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
        self.console.print()

    def get_input(self) -> UserInput | None:
        """Prompt the user for input. Returns UserInput or None on Ctrl+C (exit)."""
        try:
            def _prompt_message():
                prompt_class = "class:prompt-plan" if self._plan_mode else "class:prompt"
                prompt_char = "@ " if self._plan_mode else "~ "
                return [(prompt_class, prompt_char)]

            def _toolbar():
                mode = "chatting_plan" if self._plan_mode else "chatting"
                self.status.set_mode(mode)
                display = self.status.display
                return HTML(
                    f"cfi-ai | {display}"
                    "  <i>Shift+Tab to toggle plan mode</i>"
                )

            text = self.session.prompt(
                _prompt_message,
                bottom_toolbar=_toolbar,
                multiline=False,
                key_bindings=_chat_key_bindings(on_toggle_plan=self.toggle_plan_mode),
            )
            was_plan_mode = self._plan_mode
            if was_plan_mode:
                self._plan_mode = False
            return UserInput(text=text, plan_mode=was_plan_mode)
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
        """Prompt user to approve or reject a plan with execution options."""
        self.status.set_mode("awaiting_approval")
        self.console.print(
            "[muted]  Y = clear context + bypass permissions (default)  "
            "b = bypass permissions  p = keep permissions  n = reject[/muted]"
        )
        try:
            response = self.session.prompt(
                [("class:approval", "execute plan? [Y/b/p/n] ")],
                bottom_toolbar=HTML(f"cfi-ai | {self.status.display}"),
                key_bindings=_chat_key_bindings(),
            )
            key = response.strip().lower()
            if key in ("", "y", "yes"):
                return PlanApproval.CLEAR_BYPASS
            if key == "b":
                return PlanApproval.BYPASS
            if key == "p":
                return PlanApproval.PERMISSIONS
            return PlanApproval.REJECT
        except KeyboardInterrupt:
            raise
        except EOFError:
            return PlanApproval.REJECT

    def prompt_approval(self) -> bool:
        self.status.set_mode("awaiting_approval")
        try:
            response = self.session.prompt(
                [("class:approval", "approve? [Y/n] ")],
                bottom_toolbar=HTML(f"cfi-ai | {self.status.display}"),
                key_bindings=_chat_key_bindings(),
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
