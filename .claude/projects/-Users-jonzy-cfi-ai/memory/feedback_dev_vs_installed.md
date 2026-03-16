---
name: Dev repo is separate from installed app
description: The cfi-ai repo is a development copy — the installed version on the user's machine is a separate install, not running from this repo
type: feedback
---

The cfi-ai app installed on the user's machine is a separate installation from the development repo we work in. Do not assume that changes made in the repo (like version bumps) affect the locally installed app.

**Why:** The user installs cfi-ai via `uv tool install`, which creates an independent copy. The dev repo at ~/cfi-ai is just for development. When reasoning about what the user's installed app will do (update prompts, version checks, etc.), treat it the same as any other end user's install.

**How to apply:** When the user asks about behavior of their installed cfi-ai, reason about it as an end-user install at the previous version, not as the dev repo. Never say "you already have the latest" just because the repo was bumped.
