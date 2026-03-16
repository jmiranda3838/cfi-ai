#!/usr/bin/env bash
set -euo pipefail

# Release script: bumps version in pyproject.toml, commits, tags, and pushes.
# Usage: scripts/release.sh <version>
#   e.g. scripts/release.sh 0.10.0

VERSION="${1:-}"

if [ -z "$VERSION" ]; then
  echo "Usage: scripts/release.sh <version>" >&2
  echo "  e.g. scripts/release.sh 0.10.0" >&2
  exit 1
fi

if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Error: version must be in X.Y.Z format (got: $VERSION)" >&2
  exit 1
fi

# Must be on main with a clean working tree
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" != "main" ]; then
  echo "Error: must be on main branch (currently on: $BRANCH)" >&2
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Error: working tree is not clean — commit or stash changes first" >&2
  exit 1
fi

TAG="v$VERSION"
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Error: tag $TAG already exists" >&2
  exit 1
fi

# Update version in pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# Verify the version was written correctly
TOML_VERSION="$(uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")"
if [ "$TOML_VERSION" != "$VERSION" ]; then
  echo "Error: pyproject.toml version mismatch after sed (expected $VERSION, got $TOML_VERSION)" >&2
  git checkout pyproject.toml
  exit 1
fi

# Reinstall to refresh importlib.metadata
uv pip install -e .

# Verify runtime version matches
RUNTIME_VERSION="$(uv run python -c "from cfi_ai import __version__; print(__version__)")"
if [ "$RUNTIME_VERSION" != "$VERSION" ]; then
  echo "Error: runtime __version__ mismatch (expected $VERSION, got $RUNTIME_VERSION)" >&2
  git checkout pyproject.toml
  exit 1
fi

# Commit, tag, push
git add pyproject.toml
git commit -m "Bump version to $VERSION"
git tag "$TAG"
git push origin main --tags

echo "Released $TAG — GitHub Actions will create the release."
