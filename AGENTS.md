# Working in this repository

- **Project verification:** `.claude/skills/verify/SKILL.md` says how to launch, check,
  drive and prove this app, and where evidence goes. Read it before you change behaviour
  and follow its Launch, Doctor, Drive, Evidence and Cleanup sections to prove a change.
  The feature map is in `.claude/skills/verify/features/`. The file is read by path on
  purpose: it is the same instructions for Pi, Claude Code and Codex.
- **Commands:** `uv sync --frozen` installs; `scripts/db.sh up|url|reset|down` manages the
  disposable PostgreSQL; `uv run --frozen pytest -q` runs the unit tests;
  `uv run --frozen python scripts/verify_browser.py` runs the browser verification;
  `scripts/check.sh` runs everything against a fresh database.
- **Report with evidence.** Name the `evidence/<timestamp>/` directory in your result.
  Prose is not verification.
- **Stop what you started, never by process name.** Leave `evidence/` in place.
