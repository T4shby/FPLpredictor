# Server operations log

**Rule:** Every SSH session and every change on a live VPS is recorded here in the same turn. No secrets (keys, tokens, `.env` values).

Hostnames:

- `plesk.ashbystudios.com` — 4 GB Plesk; YetiBets + WordPress; FPL target `fpl.ashbystudios.com`
- `ubuntu` — 62 GB; Ollama / trading-research (not FPL for now)

---

## 2026-08-21 — Rule created (no SSH yet)

- **Host:** n/a (repo only)
- **Who:** local agent
- **Done:** Added this log and `.cursor/rules/server-ops.mdc`. FPL public hostname agreed: `fpl.ashbystudios.com`. Deploy user to be `fplpredictor` with a dedicated SSH key. No commands run on Plesk in this turn.
- **Follow-up:** User creates the key and `authorized_keys`; then first SSH install.
