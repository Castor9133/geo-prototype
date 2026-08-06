---
name: georank
description: Operate a running GEOrank instance via HTTP API (login, companies, diagnostics, keywords, admin settings). Not for GEO strategy writing or code changes unrelated to a live instance.
---

# GEOrank Operator

Resolve paths relative to this Skill directory.

## Workflow

1. Base URL: `http://localhost:8000` for local; require HTTPS for remote.
2. Auth: `python3 scripts/georank_client.py login --account <account>` then `whoami`. Enable admin branches only when `role=admin`.
3. Reads: `scripts/georank_client.py call GET <path>`.
4. Writes: dry-run first (no `--execute`); execute only when the user clearly authorizes that change.
5. Admin mutations: read `references/safety-policy.md` and supply the required confirmation phrase.
6. Return a short receipt: action, status, IDs/request id, next step. Redact secrets.

## Safety

- Never pass passwords/tokens on the CLI; use env/session store.
- Non-reads need `--execute`. Admin writes need `APPLY_ADMIN_CHANGE`; deletes need `DELETE:<api-path-with-query>`.
- Stop if role lacks permission, target is ambiguous, or high-impact change lacks rollback info.

## References (on demand)

- `references/user-capabilities.md`
- `references/admin-capabilities.md`
- `references/safety-policy.md`
- `scripts/georank_client.py`
