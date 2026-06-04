# AGENTS.md

This repository contains a personal MCP server for Zighang job search,
recommendation, daily digest generation, notifications, and local analytics.

## Guidelines For Coding Agents

- Keep user resumes, portfolios, generated reports, local cache, credentials,
  `.env` files, and notification secrets out of version control.
- Prefer deterministic local logic for recommendation scoring and digest
  analytics. Do not add external LLM calls to core scoring without an explicit
  design decision.
- Keep MCP tool behavior documented in `docs/mcp-tools.md` when changing tool
  inputs, outputs, defaults, or routing guidance.
- Update README examples when changing user-facing workflows, scheduler usage,
  notification setup, or public installation behavior.
- Add or update unit tests when changing scoring, storage schema, digest
  rendering, notification delivery, MCP tool registration, or analytics output.
- Run `.venv/bin/python -m unittest discover -s tests` before committing when
  the local environment is available.
- Do not add high-volume scraping, authentication bypass, token harvesting, or
  behavior that conflicts with upstream service policies.

## Data And Privacy Boundaries

- `data/cache/`, `reports/daily/`, `resumes/`, and `portfolios/` are local data
  areas. Only their `.gitkeep` files should be committed.
- `ZIGHANG_AUTH_TOKEN`, `ZIGHANG_COOKIE`, webhook URLs, SMTP credentials,
  Telegram bot tokens, and Discord webhook URLs must remain user-provided local
  configuration.
- Live API and live notification tests must remain opt-in and should not run as
  part of the default test suite.

## Project Conventions

- Keep public documentation concise and user-workflow oriented.
- Keep new dependencies minimal and justify them in the relevant docs or commit
  message.
- Preserve compatibility aliases such as `list_saved_jobs` and
  `mark_job_status` unless a migration plan is documented.
