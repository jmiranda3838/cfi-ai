"""The /bugreport slash map — scrub PHI from the current conversation and
open a GitHub issue.

Flow: load the current session JSON from disk → serialize to plaintext →
send to Gemini for a PHI-scrubbed bug summary → preview to user → (p)ost,
(e)dit, (s)ave, or (q)uit. The /bugreport invocation itself is not injected
into the therapy conversation (the handler returns ``handled=True``).
"""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from google import genai
from google.genai import types

from cfi_ai.config import Config
from cfi_ai.github_issue import create_issue, discover_token
from cfi_ai.maps import MapResult, register_map
from cfi_ai.prompts.bugreport import BUGREPORT_SUMMARY_PROMPT
from cfi_ai.sessions import SessionStore

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


_MAX_TITLE_LEN = 70
_LABELS = ["bug", "auto-reported"]

_SUMMARY_MAX_OUTPUT_TOKENS = 8192
_SUMMARY_TIMEOUT_MS = 240_000


def _serialize_content(msg: types.Content, idx: int) -> list[str]:
    role = msg.role or "unknown"
    lines: list[str] = []
    parts = msg.parts or []
    if not parts:
        lines.append(f"[turn {idx} - {role}]: (empty)")
        return lines
    for part in parts:
        if part.text:
            lines.append(f"[turn {idx} - {role}]: {part.text}")
        elif part.function_call is not None:
            name = part.function_call.name or "?"
            args = dict(part.function_call.args or {})
            try:
                args_str = json.dumps(args, default=str)
            except (TypeError, ValueError):
                args_str = str(args)
            lines.append(f"[turn {idx} - model tool_call]: {name}({args_str})")
        elif part.function_response is not None:
            name = part.function_response.name or "?"
            resp = part.function_response.response or {}
            try:
                resp_str = json.dumps(resp, default=str)
            except (TypeError, ValueError):
                resp_str = str(resp)
            lines.append(f"[turn {idx} - tool_result {name}]: {resp_str}")
        elif part.inline_data is not None:
            mime = part.inline_data.mime_type or "?"
            size = len(part.inline_data.data) if part.inline_data.data else 0
            lines.append(f"[turn {idx} - {role} inline_data]: {mime}, {size} bytes")
        else:
            lines.append(f"[turn {idx} - {role} other]: <unrecognized part>")
    return lines


def _build_transcript(
    messages: list[types.Content],
    session_id: str,
    first_user_message: str,
    usage: dict | None,
) -> str:
    header = [
        f"session_id: {session_id}",
        f"first_user_message: {first_user_message[:200]}",
        f"turn_count: {len(messages)}",
    ]
    if usage:
        header.append(
            "usage: "
            f"prompt_tokens={usage.get('last_prompt_tokens', '?')} "
            f"total_input_billed={usage.get('total_input_billed', '?')} "
            f"total_cached={usage.get('total_cached', '?')} "
            f"total_output={usage.get('total_output', '?')} "
            f"total_cost_usd={usage.get('total_cost_usd', '?')}"
        )
    body_lines: list[str] = ["## Session metadata", *header, "", "## Conversation"]
    for idx, msg in enumerate(messages, 1):
        body_lines.extend(_serialize_content(msg, idx))
    return "\n".join(body_lines)


def _normalize_finish_reason(fr) -> str:
    """Return an uppercase name like ``"STOP"`` or ``"MAX_TOKENS"`` regardless
    of whether the SDK returned an enum member, an enum's ``str()`` form
    (``"FinishReason.STOP"``), or a raw string (``"STOP"`` / ``"stop"``)."""
    if fr is None:
        return ""
    name = getattr(fr, "name", None)
    if name:
        return name.upper()
    s = str(fr)
    if "." in s:
        s = s.rsplit(".", 1)[-1]
    return s.upper()


def _call_summarizer(config: Config, transcript: str) -> str:
    """One-shot non-streaming call to Gemini with the bug-summary prompt.

    Returns the summary text. Raises ``RuntimeError`` on any non-success
    finish reason, empty candidates, or empty text — we fail closed on
    anything abnormal rather than posting a partial or policy-redacted
    summary to a public repo.
    """
    gclient = genai.Client(
        vertexai=True,
        project=config.project,
        location=config.location,
    )
    response = gclient.models.generate_content(
        model=config.model,
        contents=transcript,
        config=types.GenerateContentConfig(
            system_instruction=BUGREPORT_SUMMARY_PROMPT,
            max_output_tokens=_SUMMARY_MAX_OUTPUT_TOKENS,
            temperature=0.0,
            http_options=types.HttpOptions(timeout=_SUMMARY_TIMEOUT_MS),
        ),
    )

    candidates = response.candidates or []
    if candidates:
        fr_normalized = _normalize_finish_reason(candidates[0].finish_reason)
        if fr_normalized and fr_normalized != "STOP":
            if "MAX_TOKENS" in fr_normalized:
                raise RuntimeError(
                    "Summarizer response was truncated (MAX_TOKENS). The "
                    "session may be unusually large or the model produced "
                    "an overly long summary. Try /clear and retry with a "
                    "smaller session."
                )
            raise RuntimeError(
                f"Summarizer stopped with non-success finish reason: "
                f"{fr_normalized}. Refusing to post — output may be partial "
                "or policy-redacted."
            )

    text = response.text or ""
    if not text.strip():
        raise RuntimeError("Summarizer returned an empty response.")
    return text


def _build_issue_body(
    user_description: str,
    bug_summary: str,
    session_id: str,
    usage: dict | None,
) -> str:
    try:
        version = importlib.metadata.version("cfi-ai")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    env_lines = [
        f"- cfi-ai: {version}",
        f"- Python: {sys.version.split()[0]}",
        f"- Platform: {platform.system()} {platform.release()}",
        f"- session_id: {session_id}",
    ]
    if usage:
        env_lines.append(
            f"- usage: {usage.get('last_prompt_tokens', '?')} prompt tokens, "
            f"${usage.get('total_cost_usd', 0):.4f} total"
        )
    return (
        "## Description\n"
        f"{user_description.strip() or '(no description provided)'}\n\n"
        "## Bug summary\n"
        f"{bug_summary.strip()}\n\n"
        "## Environment\n"
        + "\n".join(env_lines)
        + "\n"
    )


def _build_title(args: str | None, first_user_message: str) -> str:
    if args and args.strip():
        raw = args.strip()
    else:
        raw = f"Bug report: {first_user_message.strip() or 'cfi-ai session'}"
    if len(raw) > _MAX_TITLE_LEN:
        raw = raw[: _MAX_TITLE_LEN - 1].rstrip() + "…"
    return raw


def _resolve_editor_command() -> list[str] | None:
    """Pick an editor command. VS Code (with ``--wait``) when available, then
    nano, then vi. Returns None if no editor is on PATH."""
    if shutil.which("code"):
        return ["code", "--wait"]
    for fallback in ("nano", "vi"):
        if shutil.which(fallback):
            return [fallback]
    return None


def _edit_in_editor(initial_text: str) -> str | None:
    """Open an editor on a temp file seeded with ``initial_text``. Returns the
    edited contents, or None if no editor is available, the editor exited
    abnormally, or it exited cleanly without saving (e.g. vim ``:q!``)."""
    cmd = _resolve_editor_command()
    if cmd is None:
        return None
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(initial_text)
        tmp_path = tf.name
    try:
        before = Path(tmp_path).stat().st_mtime_ns
        result = subprocess.run([*cmd, tmp_path])
        if result.returncode != 0:
            return None
        after = Path(tmp_path).stat().st_mtime_ns
        if after == before:
            return None
        return Path(tmp_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _render_preview(ui: UI, title: str, body: str) -> None:
    ui.console.print()
    ui.console.print(f"[accent]Title:[/accent] {title}")
    ui.console.print()
    ui.render_markdown(body)
    ui.console.print()


def _prompt_action(ui: UI) -> str:
    ui.console.print("[muted]Actions: (p)ost, (e)dit, (s)ave to file, (q)uit[/muted]")
    try:
        choice = ui.console.input("[accent]> [/accent]").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "q"
    if not choice:
        return ""
    return choice[0]


def _confirm_post(ui: UI, repo: str) -> bool:
    """Second-stage gate after the user presses ``p``. Accepts only the exact
    string ``POST`` (case-sensitive). Anything else — empty input, Ctrl-C,
    EOF, lowercase, typo — returns False so the caller can loop back to the
    action menu."""
    ui.console.print(
        f"[accent]About to POST to {repo} (public). "
        f"Type POST to confirm:[/accent]"
    )
    try:
        answer = ui.console.input("[accent]> [/accent]")
    except (EOFError, KeyboardInterrupt):
        return False
    return answer == "POST"


@register_map(
    "bugreport",
    description="Scrub PHI from the current conversation and open a GitHub issue",
)
def handle_bugreport(
    args: str | None,
    ui: UI,
    workspace: Workspace,
    session_store: SessionStore,
) -> MapResult:
    # Load config fresh — maps don't receive the startup Config instance.
    try:
        config = Config.load()
    except SystemExit:
        return MapResult(error="Could not load config. Run 'cfi-ai --setup'.")

    if not config.bugreport_enabled:
        return MapResult(
            error="Bug reporting is disabled. Set [bugreport] enabled = true "
            "in config, or unset CFI_AI_BUGREPORT_ENABLED."
        )

    session_path = session_store.path
    if not session_path.exists():
        return MapResult(
            error="No saved conversation yet. Have at least one full exchange "
            "with cfi-ai before running /bugreport."
        )

    try:
        messages = SessionStore.load(session_path)
    except Exception as e:
        return MapResult(error=f"Could not read session file: {e}")

    if not messages:
        return MapResult(
            error="Saved session contains no messages — nothing to report."
        )

    try:
        session_data = json.loads(session_path.read_text())
    except (OSError, json.JSONDecodeError):
        session_data = {}
    first_user_message = session_data.get("first_user_message") or ""
    usage = session_data.get("usage") or None

    ui.print_info(f"Loading conversation ({len(messages)} turns)...")
    transcript = _build_transcript(
        messages, session_store.session_id, first_user_message, usage
    )

    ui.print_info("Summarizing via Gemini (this may take a moment)...")
    try:
        bug_summary = _call_summarizer(config, transcript)
    except Exception as e:
        return MapResult(error=f"Summarizer call failed: {e}")

    title = _build_title(args, first_user_message)
    user_description = args.strip() if args and args.strip() else ""
    body = _build_issue_body(
        user_description=user_description,
        bug_summary=bug_summary,
        session_id=session_store.session_id,
        usage=usage,
    )

    while True:
        _render_preview(ui, title, body)
        action = _prompt_action(ui)

        if action == "p":
            if not _confirm_post(ui, config.bugreport_repo):
                ui.print_info("Post cancelled.")
                continue
            if config.bugreport_dry_run:
                ts = time.strftime("%Y%m%d-%H%M%S")
                out_path = Path(workspace.root) / f"bugreport-dryrun-{ts}.md"
                try:
                    out_path.write_text(
                        f"# Title: {title}\n\n{body}", encoding="utf-8"
                    )
                except OSError as e:
                    ui.print_error(f"Could not write {out_path}: {e}")
                    return MapResult(handled=True)
                ui.console.print(
                    f"[muted]DRY RUN — saved to {out_path}, not posted[/muted]"
                )
                return MapResult(handled=True)
            token = discover_token()
            if token is None:
                ui.print_error(
                    "No GitHub token found. Set GITHUB_TOKEN or GH_TOKEN, "
                    "or run 'gh auth login'."
                )
                return MapResult(handled=True)
            try:
                url = create_issue(
                    repo=config.bugreport_repo,
                    title=title,
                    body=body,
                    labels=_LABELS,
                    token=token,
                )
            except RuntimeError as e:
                ui.print_error(str(e))
                return MapResult(handled=True)
            ui.console.print(f"[primary]Posted:[/primary] {url}")
            return MapResult(handled=True)

        if action == "e":
            edited = _edit_in_editor(f"# Title: {title}\n\n{body}")
            if edited is None:
                ui.print_error("Editor exited without saving. Keeping original draft.")
                continue
            edited = edited.lstrip()
            if edited.startswith("# Title:"):
                first_line, _, rest = edited.partition("\n")
                new_title = first_line[len("# Title:") :].strip()
                if new_title:
                    title = new_title[:_MAX_TITLE_LEN]
                body = rest.lstrip("\n")
            else:
                body = edited
            continue

        if action == "s":
            ts = time.strftime("%Y%m%d-%H%M%S")
            out_path = Path(workspace.root) / f"bugreport-{ts}.md"
            try:
                out_path.write_text(
                    f"# Title: {title}\n\n{body}",
                    encoding="utf-8",
                )
            except OSError as e:
                ui.print_error(f"Could not write {out_path}: {e}")
                return MapResult(handled=True)
            ui.console.print(f"[primary]Saved:[/primary] {out_path}")
            return MapResult(handled=True)

        if action == "q":
            ui.print_info("Cancelled. No issue posted.")
            return MapResult(handled=True)

        ui.print_error("Unrecognized action. Choose p, e, s, or q.")
