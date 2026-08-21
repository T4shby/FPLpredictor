# Server operations log

**Rule:** Every SSH session and every change on a live VPS is recorded here in the same turn. No secrets (keys, tokens, `.env` values).

Hostnames:

- `plesk.ashbystudios.com` — 4 GB Plesk; YetiBets + WordPress; FPL target `fpl.ashbystudios.com`
- `ubuntu` — 62 GB; Ollama / trading-research (not FPL for now)

---

## 2026-08-21 — First SSH install on Plesk

- **Host:** `plesk.ashbystudios.com`
- **Who:** `fplpredictor` (ed25519 deploy key). User `fplpredictor` and `/etc/sudoers.d/fplpredictor` were created by root before this session.
- **Repo:** pushed `9365bf5` then cloned into `/opt/fplpredictor` (temp clone in `/tmp`, copied over existing `data/` and `logs/` dirs).
- **Install:** Python 3.12 venv, `pip install -e .`
- **Config:** wrote `/opt/fplpredictor/.env` from `deploy/plesk/env.plesk.example` with new secret/token (values not logged). `chmod 600`. SQLite `sqlite:////opt/fplpredictor/data/fpl.db`
- **Service:** copied `fpl-predictor.service` to systemd, `fpl-predictor.cron` to `/etc/cron.d/` (06:00 Europe/London). `systemctl enable --now fpl-predictor`
- **Check:** `curl http://127.0.0.1:8001/health` → ok. `GET /` → HTTP 200. Service `active`.
- **First refresh:** `scripts/run_daily_refresh.py` succeeded (~21s). Import 600 players / 20 teams / 380 fixtures. Models A–D run_ids 1–4, target GW1. DB ~2.3 MB. RAM after: 1.1 Gi used, 2.7 Gi available (no OOM).
- **Not done:** Plesk vhost / SSL for `fpl.ashbystudios.com` (needs DNS + nginx proxy to `127.0.0.1:8001`). Tighter sudoers file from `deploy/plesk/sudoers-fplpredictor` not installed yet (current sudoers allows generic `systemctl`/`cp`/`chmod`).
- **Follow-up:** user adds subdomain reverse proxy in Plesk; Let's Encrypt once DNS answers.

