---
name: release
description: Release a new version — auto-detects version bump, commits pending changes, runs tests, and executes the release script
disable-model-invocation: true
allowed-tools: Bash(scripts/release.sh *), Bash(uv run pytest *), Bash(git *), Bash(uv run python *)
---

# Release skill

You are executing the `/release` skill. Follow these steps exactly:

## 1. Determine the next version

Read the current version:

```
uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
```

Then get the changes since the last release:

```
git log v<current_version>..HEAD --oneline
```

Analyze the commit messages to determine the bump type using this convention:
- **patch** (e.g. 0.10.0 → 0.10.1): bug fixes only
- **minor** (e.g. 0.10.0 → 0.11.0): new features or breaking changes

Compute the next version by incrementing the appropriate component and resetting lower components to 0.

If there are no commits since the last tag, stop and tell the user there is nothing to release.

Show the user the proposed version with a brief explanation (e.g. "Detected new feature commits → minor bump: 0.10.0 → 0.11.0") and ask them to confirm or provide an override.

## 2. Run tests

Run `uv run pytest tests/ -v`. If any test fails, stop and report the failures. Do not proceed with the release.

## 3. Commit pending changes

Run `git status` to check for uncommitted changes (staged, unstaged, or untracked). If there are changes:
- Show the user what has changed
- Ask the user for a commit message
- Stage the relevant files and commit

If the working tree is clean, skip this step.

## 4. Execute the release script

Run `scripts/release.sh <computed_version>` (substituting the version confirmed in step 1).

## 5. Report result

Tell the user whether the release succeeded or failed. If it succeeded, mention the tag that was created (e.g. `v0.11.0`).
