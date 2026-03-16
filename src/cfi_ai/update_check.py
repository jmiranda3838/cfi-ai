"""Non-blocking startup version check against GitHub Releases.

Uses a detached subprocess pattern: the current invocation reads from cache,
and if the cache is stale, spawns a fire-and-forget child process to refresh it.
The update notification is therefore one run behind — zero startup latency.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import textwrap
import time
from pathlib import Path

log = logging.getLogger(__name__)

GITHUB_REPO = "jmiranda3838/cfi-ai"
CACHE_FILE = Path.home() / ".config" / "cfi-ai" / "update-check.json"
CHECK_INTERVAL = 3_600  # 1 hour
_NETWORK_TIMEOUT = 5  # seconds


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a version string like '0.8.0' into a comparable tuple."""
    return tuple(int(x) for x in v.lstrip("v").split("."))


def _read_cache() -> dict | None:
    try:
        data = json.loads(CACHE_FILE.read_text())
        if "last_check" in data and "latest_version" in data:
            return data
    except (OSError, json.JSONDecodeError, KeyError):
        pass
    return None


def _write_cache(latest_version: str) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps({"last_check": time.time(), "latest_version": latest_version})
        )
    except OSError:
        pass


def _spawn_refresh() -> None:
    """Spawn a detached child process to fetch the latest version and update the cache."""
    script = textwrap.dedent(f"""\
        import json, os, subprocess, time, urllib.request
        from pathlib import Path

        GITHUB_REPO = {GITHUB_REPO!r}
        CACHE_FILE = Path({str(CACHE_FILE)!r})
        NETWORK_TIMEOUT = {_NETWORK_TIMEOUT!r}

        def discover_token():
            for var in ("GITHUB_TOKEN", "GH_TOKEN"):
                token = os.environ.get(var)
                if token:
                    return token
            try:
                result = subprocess.run(
                    ["gh", "auth", "token"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception:
                pass
            return None

        url = f"https://api.github.com/repos/{{GITHUB_REPO}}/releases/latest"
        req = urllib.request.Request(url, headers={{"Accept": "application/vnd.github+json"}})
        token = discover_token()
        if token:
            req.add_header("Authorization", f"Bearer {{token}}")
        try:
            with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT) as resp:
                data = json.loads(resp.read())
                tag = data.get("tag_name", "")
                latest = tag.lstrip("v") if tag else None
        except Exception:
            latest = None

        if latest:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps({{"last_check": time.time(), "latest_version": latest}})
            )
    """)
    try:
        subprocess.Popen(
            [sys.executable, "-c", script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        log.debug("Update check: failed to spawn refresh subprocess", exc_info=True)


def check_for_update(current_version: str) -> str | None:
    """Check for updates synchronously using the cache file.

    Returns an update message if a newer version is cached, or None.
    Spawns a detached subprocess to refresh the cache if it's stale or missing.
    """
    try:
        cache = _read_cache()

        # Spawn refresh if cache is stale or missing
        if not cache or (time.time() - cache["last_check"]) >= CHECK_INTERVAL:
            _spawn_refresh()

        # Build message from cache (if present and newer)
        if cache:
            latest = cache["latest_version"]
            if _parse_version(latest) > _parse_version(current_version):
                return (
                    f"Update available: {current_version} → {latest}"
                    f" — run 'cfi-ai --update' to update"
                )
    except Exception:
        log.debug("Update check failed", exc_info=True)

    return None
