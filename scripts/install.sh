#!/usr/bin/env bash
set -euo pipefail

# cfi-ai installer for macOS
# Usage: curl -fsSL https://raw.githubusercontent.com/jmiranda3838/cfi-ai/main/scripts/install.sh | bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { printf "  ${GREEN}✓${NC} %s\n" "$1"; }
warn() { printf "  ${YELLOW}!${NC} %s\n" "$1"; }
err()  { printf "  ${RED}✗${NC} %s\n" "$1"; }
step() { printf "\n${BOLD}%s${NC}\n" "$1"; }

# -----------------------------------------------------------
printf "\n${BOLD}cfi-ai installer${NC}\n"
echo "This will set up everything you need."

# --- macOS check ---
if [[ "$(uname)" != "Darwin" ]]; then
  err "This installer is for macOS only."
  exit 1
fi

# --- Install uv ---
step "Step 1/3 — Package manager (uv)"

if command -v uv &>/dev/null; then
  ok "uv is already installed."
else
  echo "  Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null
  # Source uv into the current session
  # shellcheck disable=SC1091
  source "$HOME/.local/bin/env" 2>/dev/null || true
  if command -v uv &>/dev/null; then
    ok "uv installed."
  else
    err "Failed to install uv. Please visit https://docs.astral.sh/uv/ for help."
    exit 1
  fi
fi

# --- Install cfi-ai ---
step "Step 2/3 — cfi-ai"

REPO="git+https://github.com/jmiranda3838/cfi-ai.git"

if command -v cfi-ai &>/dev/null; then
  echo "  cfi-ai is already installed — updating..."
  uv tool upgrade cfi-ai 2>/dev/null && ok "cfi-ai updated." || ok "cfi-ai is already up to date."
else
  echo "  Installing cfi-ai..."
  uv tool install "$REPO"
  ok "cfi-ai installed."
fi

# Add ~/.local/bin to shell PATH if needed
uv tool update-shell 2>/dev/null || true

# --- Google Cloud ---
step "Step 3/3 — Google Cloud"

if command -v gcloud &>/dev/null; then
  ok "Google Cloud SDK is installed."
  echo ""
  echo "  Make sure you've run this at least once:"
  echo "    gcloud auth application-default login"
else
  warn "Google Cloud SDK is not installed."
  echo ""
  echo "  cfi-ai needs this to connect to Google Cloud."
  echo "  Install it from: https://cloud.google.com/sdk/docs/install"
  echo ""
  echo "  After installing, run:"
  echo "    gcloud auth application-default login"
fi

# --- Done ---
step "Done!"
echo ""
echo "  1. Restart your terminal (close and reopen it)"
echo "  2. Run:  cfi-ai"
echo ""
echo "  On first run, cfi-ai will ask you to set up your Google Cloud project."
echo ""
