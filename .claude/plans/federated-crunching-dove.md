# Plan: Auto-detect version in `/release` skill

## Context

The user currently has to remember and pass the exact version number when running `/release 0.11.0`. They want the skill to read the current version from `pyproject.toml`, analyze git changes since the last tag, and auto-determine the next version (patch/minor/major) per the project convention: bug fix → patch, new feature or breaking change → minor.

## Changes

### 1. Update `SKILL.md` (`.claude/skills/release/SKILL.md`)

Replace the "validate version argument" step with an auto-detection flow:

- **Read current version**: Run `python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"` to get the current version (e.g. `0.10.0`).
- **Get changes since last tag**: Run `git log v{current_version}..HEAD --oneline` to see what's changed.
- **Determine bump type**: Analyze the commit messages. Apply the project convention from CLAUDE.md:
  - **patch** (0.10.0 → 0.10.1): bug fixes only
  - **minor** (0.10.0 → 0.11.0): new features or breaking changes
- **Compute next version**: Increment the appropriate component, reset lower components to 0.
- **Confirm with user**: Show the proposed version and the reasoning (e.g. "Detected new feature commits → minor bump: 0.10.0 → 0.11.0"). Ask the user to confirm or override.

The rest of the skill (run tests, commit pending changes, execute release script, report result) stays the same.

Also remove `argument-hint: <version>` from the frontmatter since no argument is needed, and update allowed-tools to include the `uv run python` command for reading the version.

### 2. No changes to `scripts/release.sh`

The release script still receives the computed version as an argument — no modifications needed.

## Files to modify

- `.claude/skills/release/SKILL.md` — the only file that changes

## Verification

1. Run `/release` with no argument — it should auto-detect version and ask for confirmation
2. Verify it reads the correct current version from `pyproject.toml`
3. Verify it shows the git log analysis and proposed bump
4. Verify the rest of the flow (tests, commit, release script) still works
