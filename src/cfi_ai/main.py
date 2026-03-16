import logging
import os
import sys

from cfi_ai import __version__
from cfi_ai.config import Config
from cfi_ai.client import Client
from cfi_ai.workspace import Workspace
from cfi_ai.prompts.system import build_system_prompt
from cfi_ai.ui import UI
from cfi_ai.agent import run_agent_loop


def _check_adc() -> None:
    """Verify Application Default Credentials are available."""
    try:
        import google.auth

        google.auth.default()
    except google.auth.exceptions.DefaultCredentialsError:
        print(
            "Error: Google Cloud Application Default Credentials not found.\n"
            "Run: gcloud auth application-default login",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    level = os.environ.get("CFI_AI_LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.WARNING),
        format="%(name)s %(levelname)s %(message)s",
    )

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
        print("  CFI_AI_MODEL            Model name (default: gemini-2.5-flash)")
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

    _check_adc()

    workspace = Workspace()
    system_prompt = build_system_prompt(str(workspace.root), workspace.summary(), workspace=workspace)
    client = Client(config)
    ui = UI()

    ui.print_welcome(str(workspace.root))

    if update_msg:
        ui.print_info(update_msg)

    try:
        run_agent_loop(client, ui, workspace, system_prompt, config)
    except KeyboardInterrupt:
        ui.print_info("\nClawdius waves goodbye.")
