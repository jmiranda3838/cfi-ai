from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from rich.markup import escape


@dataclass
class PlannedOperation:
    tool_name: str
    description: str
    args_summary: str
    diff_lines: list[str] | None = None


@dataclass
class ExecutionPlan:
    operations: list[PlannedOperation] = field(default_factory=list)

    def add(self, tool_name: str, tool_input: dict, workspace=None) -> None:
        if tool_name == "write_file":
            path = tool_input.get("path", "?")
            content = tool_input.get("content", "")
            args_summary = f"path={path}"

            if not content:
                desc = f"Create empty file {path}"
            else:
                desc = f"Write to {path} ({len(content)} chars)"

            self.operations.append(PlannedOperation(tool_name, desc, args_summary))

        elif tool_name == "apply_patch":
            path = tool_input.get("path", "?")
            edits = tool_input.get("edits", [])
            args_summary = f"path={path}"
            diff = None

            if workspace:
                try:
                    target = workspace.validate_path(path)
                    if target.is_file():
                        old_content = target.read_text()
                        new_content = old_content
                        for edit in edits:
                            old_text = edit.get("old_text", "")
                            new_text = edit.get("new_text", "")
                            replace_all = edit.get("replace_all", False)
                            if old_text:
                                if replace_all:
                                    new_content = new_content.replace(old_text, new_text)
                                elif new_content.count(old_text) == 1:
                                    new_content = new_content.replace(old_text, new_text, 1)
                        diff = list(difflib.unified_diff(
                            old_content.splitlines(keepends=True),
                            new_content.splitlines(keepends=True),
                            fromfile=path,
                            tofile=path,
                        ))
                except Exception:
                    pass

            n = len(edits)
            desc = f"Edit {path} ({n} edit{'s' if n != 1 else ''})"
            self.operations.append(PlannedOperation(tool_name, desc, args_summary, diff))

        elif tool_name == "run_command":
            command = tool_input.get("command", "?")
            args_summary = f"command={command}"
            # Label rm as destructive
            if command.strip().startswith("rm "):
                desc = f"[red]DELETE[/red] {command}"
            else:
                desc = f"Run: {command}"
            self.operations.append(PlannedOperation(tool_name, desc, args_summary))

        else:
            desc = f"Execute {tool_name}"
            args_summary = ", ".join(f"{k}={v!r}" for k, v in tool_input.items())
            self.operations.append(PlannedOperation(tool_name, desc, args_summary))


def _format_diff(diff_lines: list[str], max_lines: int = 50) -> str:
    """Format diff lines with Rich color markup, truncating if needed."""
    output: list[str] = []
    for i, line in enumerate(diff_lines):
        if i >= max_lines:
            remaining = len(diff_lines) - max_lines
            output.append(f"   [dim]... {remaining} more lines ...[/dim]")
            break
        escaped = escape(line.rstrip("\n"))
        if line.startswith("+") and not line.startswith("+++"):
            output.append(f"   [green]{escaped}[/green]")
        elif line.startswith("-") and not line.startswith("---"):
            output.append(f"   [red]{escaped}[/red]")
        else:
            output.append(f"   [dim]{escaped}[/dim]")
    return "\n".join(output)


def format_plan(plan: ExecutionPlan) -> str:
    """Render the plan as a text summary for display inside a Rich panel."""
    lines: list[str] = []
    for i, op in enumerate(plan.operations, 1):
        lines.append(f"[primary]{i}.[/primary] [bold]{op.description}[/bold]")
        lines.append(f"   [dim]{op.args_summary}[/dim]")
        if op.diff_lines:
            lines.append(_format_diff(op.diff_lines))
    return "\n".join(lines)
