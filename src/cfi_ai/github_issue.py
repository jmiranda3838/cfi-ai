"""GitHub REST API helper for /bugreport.

Single public entry point: :func:`create_issue`. Keeps the token-discovery
pattern from ``update_check.py`` but lives separately because /bugreport runs
in-process (not in a detached subprocess) and needs to raise on failure so the
user sees the error.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request

_BODY_LIMIT = 65_536  # GitHub issue body max length
_NETWORK_TIMEOUT = 10  # seconds


def discover_token() -> str | None:
    """Find a GitHub token via env vars, then the `gh` CLI. Matches the
    precedence used in ``update_check.py`` so users with either set-up work."""
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        token = os.environ.get(var)
        if token:
            return token.strip() or None
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _truncate_body(body: str) -> str:
    if len(body) <= _BODY_LIMIT:
        return body
    excess = len(body) - _BODY_LIMIT
    marker = f"\n\n... [truncated {excess} chars]"
    return body[: _BODY_LIMIT - len(marker)] + marker


def create_issue(
    repo: str,
    title: str,
    body: str,
    labels: list[str],
    token: str | None = None,
) -> str:
    """POST an issue to ``https://api.github.com/repos/{repo}/issues``.

    Returns the created issue's ``html_url``. Raises ``RuntimeError`` on any
    failure (no token, network error, non-201 response) with a message suitable
    for display to the user.
    """
    token = token or discover_token()
    if not token:
        raise RuntimeError(
            "No GitHub token found. Set GITHUB_TOKEN or GH_TOKEN, or run 'gh auth login'."
        )

    payload = {
        "title": title,
        "body": _truncate_body(body),
        "labels": labels,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=data,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "cfi-ai-bugreport",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=_NETWORK_TIMEOUT) as resp:
            if resp.status != 201:
                raise RuntimeError(
                    f"GitHub returned HTTP {resp.status} when creating the issue."
                )
            response = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")
            err_data = json.loads(err_body)
            detail = f" — {err_data.get('message', err_body[:200])}"
        except Exception:
            pass
        raise RuntimeError(f"GitHub API error: HTTP {e.code}{detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error reaching GitHub: {e.reason}") from e

    url = response.get("html_url")
    if not url:
        raise RuntimeError("GitHub response did not include html_url.")
    return url
