import logging
import os
import sys
import warnings

from cfi_ai import __version__
from cfi_ai.config import Config
from cfi_ai.client import Client
from cfi_ai.workspace import Workspace
from cfi_ai.prompts.system import build_system_prompt
from cfi_ai.ui import UI
from cfi_ai.agent import run_agent_loop


class _ConsoleLogHandler(logging.Handler):
    """Routes log output through Rich Console for Live-safe display."""

    def __init__(self, console):
        super().__init__()
        self._console = console

    def emit(self, record):
        try:
            msg = self.format(record)
            self._console.print(msg, highlight=False, markup=False, style="dim")
        except Exception:
            self.handleError(record)


def _check_adc() -> None:
    """Verify Application Default Credentials are available and valid."""
    try:
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default()
        credentials.refresh(google.auth.transport.requests.Request())
    except google.auth.exceptions.DefaultCredentialsError:
        print(
            "Error: Google Cloud Application Default Credentials not found.\n"
            "Run: gcloud auth application-default login",
            file=sys.stderr,
        )
        sys.exit(1)
    except google.auth.exceptions.RefreshError:
        import subprocess

        print(
            "Google Cloud credentials have expired. Launching reauthentication...",
            file=sys.stderr,
        )
        try:
            result = subprocess.run(
                ["gcloud", "auth", "application-default", "login"],
            )
        except FileNotFoundError:
            print(
                "Error: gcloud CLI not found. Install it from\n"
                "https://cloud.google.com/sdk/docs/install and run:\n"
                "  gcloud auth application-default login",
                file=sys.stderr,
            )
            sys.exit(1)
        if result.returncode != 0:
            print(
                "Error: Reauthentication failed. Please try manually:\n"
                "  gcloud auth application-default login",
                file=sys.stderr,
            )
            sys.exit(1)


def main() -> None:
    level = os.environ.get("CFI_AI_LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(
        format="%(name)s %(levelname)s %(message)s",
    )
    logging.getLogger("cfi_ai").setLevel(getattr(logging, level, logging.WARNING))

    # Handle --version, --help, and --update
    if "--version" in sys.argv:
        print(f"cfi-ai {__version__}")
        return
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: cfi-ai [--version] [--model MODEL] [--setup] [--update]")
        print("\nTerminal-first agentic assistant.")
        print(f"\nConfig file: ~/.config/cfi-ai/config.toml")
        print("\nOptions:")
        print("  --setup    Run interactive setup (creates/updates config file)")
        print("  --model    Override the model name")
        print("  --update   Update to the latest version")
        print("  --version  Show version and exit")
        print("\nEnvironment variable overrides:")
        print("  GOOGLE_CLOUD_PROJECT    GCP project ID")
        print("  GOOGLE_CLOUD_LOCATION   Vertex AI location (default: global)")
        print("  CFI_AI_MODEL            Model name (default: gemini-3-flash-preview)")
        print("  CFI_AI_MAX_TOKENS       Max tokens (default: 8192)")
        return
    if "--update" in sys.argv:
        import shutil
        import subprocess as sp

        uv_path = shutil.which("uv")
        if not uv_path:
            print(
                "Error: 'uv' is not installed or not on your PATH.\n"
                "\n"
                "To fix this, run:\n"
                "  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
                "\n"
                "Then restart your terminal and try again:\n"
                "  cfi-ai --update",
                file=sys.stderr,
            )
            sys.exit(1)

        result = sp.run([uv_path, "tool", "upgrade", "cfi-ai"])
        sys.exit(result.returncode)

    # Check for updates (reads cache synchronously, spawns refresh if stale)
    from cfi_ai.update_check import check_for_update

    update_msg = check_for_update(__version__)

    # Parse --model flag
    model_override = None
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model_override = sys.argv[idx + 1]
        else:
            print("Error: --model requires a value.", file=sys.stderr)
            sys.exit(1)

    is_setup = "--setup" in sys.argv
    config = Config.load(run_setup=is_setup)

    if is_setup:
        print("Setup complete.")
        return

    if model_override:
        config = Config(
            project=config.project,
            location=config.location,
            model=model_override,
            max_tokens=config.max_tokens,
        )

    warnings.filterwarnings(
        "ignore",
        message="Your application has authenticated using end user credentials.*quota project",
        category=UserWarning,
        module=r"google\.auth\._default",
    )
    _check_adc()

    workspace = Workspace()
    system_prompt = build_system_prompt(str(workspace.root), workspace.summary(), workspace=workspace)
    client = Client(config)
    ui = UI()

    # Route all log output through Rich console for Live-safe display
    _fmt = logging.Formatter("%(name)s %(levelname)s %(message)s")
    _handler = _ConsoleLogHandler(ui.console)
    _handler.setFormatter(_fmt)

    # Replace root logger's StreamHandler (which holds a stale stderr reference)
    root = logging.getLogger()
    for h in list(root.handlers):
        if isinstance(h, logging.StreamHandler):
            root.removeHandler(h)
    root.addHandler(_handler)

    # Dedicated cfi_ai handler (propagate=False avoids double output via root)
    cfi_logger = logging.getLogger("cfi_ai")
    cfi_logger.propagate = False
    cfi_logger.addHandler(_handler)

    ui.print_welcome(str(workspace.root))

    if update_msg:
        ui.print_info(update_msg)

    try:
        run_agent_loop(client, ui, workspace, system_prompt, config)
    except KeyboardInterrupt:
        ui.print_info("\nClawdius waves goodbye.")
