# Server operations log

**Rule:** Every SSH session and every change on a live VPS is recorded here in the same turn. No secrets (keys, tokens, `.env` values).

Hostnames:

- `plesk.ashbystudios.com` — 4 GB Plesk; YetiBets + WordPress; FPL target `fpl.ashbystudios.com`
- `ubuntu` — 62 GB; Ollama / trading-research (not FPL for now)

---

## 2026-08-21 — Squad is the home page; model tabs switch the team

- **Host:** `plesk.ashbystudios.com`
- **Who:** `fplpredictor`
- **Done:** pulled latest main. Restarted API. Ran daily refresh so 3GW/5GW squads are stored. Home is now the selected model's 15-man squad (XI, bench, C/VC). League tabs show that one team's XI. Rankings labelled as research. Cache-Control no-store on HTML.
- **Follow-up:** hard-refresh `https://fpl.ashbystudios.com` (Ctrl+F5). A/B/C/D tabs now change the squad.

## 2026-08-21 — Model league now uses real £100m FPL squads

- **Host:** `plesk.ashbystudios.com`
- **Who:** `fplpredictor`
- **Done:** pulled `74335a2` then lock-without-rebuild follow-up. `systemctl restart fpl-predictor`. Ran `scripts/run_daily_refresh.py` after the squad commit: models A–D runs 9–12. League GW1 squads: A 3-4-3 Watkins C £100.0m; B 4-4-2 Watkins C £100.0m; C 5-4-1 B.Fernandes C £100.0m; D 5-4-1 B.Fernandes C £97.5m. 15-man squads, XI, captain, max 3 per club. Still provisional until 17:30 UTC deadline, then the existing squad locks (no rebuild).
- **Note:** stashed local `docs/PREDICTIONS_2026_27_GW1.md` so pull could fast-forward.
- **Follow-up:** hard-refresh `https://fpl.ashbystudios.com/league`.

## 2026-08-21 — Deploy Model D CS calibration + live league; rerun GW1

- **Host:** `plesk.ashbystudios.com`
- **Who:** `fplpredictor`
- **Done:** `git pull --ff-only origin main` to `6d870a5`. `sudo systemctl restart fpl-predictor` (active). Ran `scripts/run_daily_refresh.py` (~19s, 600 players). New model runs 5–8. `/league` HTTP 200. Model D top is now B.Fernandes (5.82), not a Brighton defender; CS component capped (~1.66). League GW1 picks (still provisional before 17:30 UTC deadline): A/B Watkins, C/D B.Fernandes, actuals 0.
- **Note:** server still has a local uncommitted `docs/PREDICTIONS_2026_27_GW1.md` from the refresh.
- **Follow-up:** hard-refresh `https://fpl.ashbystudios.com` and open `/league`.

## 2026-08-21 — Model A/B/C/D tabs on the live site

- **Host:** `plesk.ashbystudios.com`
- **Who:** `fplpredictor`
- **Done:** `git pull --ff-only origin main` to `7d93f2e`. `sudo systemctl restart fpl-predictor`. `GET /?model=D` → 200. Dashboard now has tabs for all four models; default remains B.
- **Note:** server had a local edit to `docs/PREDICTIONS_2026_27_GW1.md` from the first refresh (left uncommitted).
- **Follow-up:** hard-refresh the browser on `https://fpl.ashbystudios.com`.

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

