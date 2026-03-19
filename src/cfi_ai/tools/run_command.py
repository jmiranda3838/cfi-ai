import shlex
import subprocess

from cfi_ai.tools.base import BaseTool, ToolDefinition

READONLY_COMMANDS = frozenset({
    "pwd", "ls", "find", "rg", "cat", "head", "tail", "wc", "grep", "diff", "file",
})
MUTATING_COMMANDS = frozenset({"mv", "cp", "mkdir", "rm"})
ALLOWED_COMMANDS = READONLY_COMMANDS | MUTATING_COMMANDS

_SHELL_METACHARS = frozenset({"|", ">", ">>", "<", ";", "&&", "||", "`", "$(", "$((", "\n"})

_RM_RECURSIVE_FLAGS = frozenset({"-r", "-rf", "-R", "--recursive", "-fr"})

_MAX_OUTPUT = 100_000
_TIMEOUT = 30


def is_command_mutating(command: str) -> bool:
    """Check if a command string uses a mutating command."""
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    if not argv:
        return False
    return argv[0] in MUTATING_COMMANDS


class RunCommandTool(BaseTool):
    name = "run_command"
    mutating = False  # Dynamic — handled by classify_mutation in registry

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Run a terminal command in the workspace directory. "
                "Allowed read commands: pwd, ls, find, rg, cat, head, tail, wc, grep, diff, file. "
                "Allowed mutating commands (require approval): mv, cp, mkdir, rm (files only, no recursive delete). "
                "Pipes, redirection, and chaining are not supported — run separate commands."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to run (e.g. 'ls -la src/' or 'rg TODO').",
                    },
                },
                "required": ["command"],
            },
        )

    def execute(self, workspace, client=None, **kwargs) -> str:
        command = kwargs["command"]

        # Parse command
        try:
            argv = shlex.split(command)
        except ValueError as e:
            return f"Error: failed to parse command: {e}"

        if not argv:
            return "Error: empty command"

        # Check allowlist
        prog = argv[0]
        if prog not in ALLOWED_COMMANDS:
            return (
                f"Error: '{prog}' is not allowed. "
                f"Allowed commands: {', '.join(sorted(ALLOWED_COMMANDS))}"
            )

        # Reject shell metacharacters in any argument
        for token in argv:
            for meta in _SHELL_METACHARS:
                if meta in token:
                    return (
                        f"Error: shell metacharacter '{meta}' is not allowed. "
                        "Run separate commands instead of using pipes or chaining."
                    )

        # rm: reject recursive flags
        if prog == "rm":
            for arg in argv[1:]:
                if arg in _RM_RECURSIVE_FLAGS:
                    return "Error: recursive delete is not allowed. rm can only delete individual files."

        # Mutating commands: validate paths
        if prog in MUTATING_COMMANDS:
            for arg in argv[1:]:
                if arg.startswith("-"):
                    continue
                try:
                    workspace.validate_path(arg)
                except ValueError as e:
                    return f"Error: {e}"

        # Execute
        try:
            result = subprocess.run(
                argv,
                cwd=workspace.root,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
        except FileNotFoundError:
            return f"Error: command '{prog}' not found on this system"
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {_TIMEOUT} seconds"

        output = result.stdout
        if result.stderr:
            output = output + result.stderr if output else result.stderr

        if not output:
            return "(no output)"

        if len(output) > _MAX_OUTPUT:
            return output[:_MAX_OUTPUT] + "\n\n... (truncated at 100k characters)"

        return output
