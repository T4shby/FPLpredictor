# Plesk: YetiBets-style FPL (no Docker)

FPL on this box is the same shape as YetiBets: `uvicorn` on `127.0.0.1`, Plesk nginx reverse-proxy, cron that **exits**. Port **8001** so we do not clash with YetiBets on **8000**.

## What to clear up first

Safe now (you said 2AJ can go):

1. **Disable `2AJ.ashbystudios.com`** in Plesk (Domains → Disable or Remove). That stops the Passenger Node app (~90 MB).
2. **Vacuum journals** (journald was ~132 MB):

```bash
journalctl --disk-usage
journalctl --vacuum-size=80M
```

3. After that, check RAM:

```bash
free -h
ps aux --sort=-%mem | head -n 15
```

Confirm before touching:

| Thing | Why it is there | If unused |
| --- | --- | --- |
| **PolyBettingApp** (`polybetting-api.service`, `polybetting-worker.service`, `/opt/PolyBettingApp`) | Not YetiBets or WP | `systemctl disable --now polybetting-api polybetting-worker` |
| **PostgreSQL 16** | Extra DB beside MariaDB | Keep if PolyBetting/YetiBets uses it; otherwise leave running until you know |
| **Redis** | Often leftover | `systemctl disable --now redis-server` only if nothing connects |
| **Dovecot + Postfix** | Plesk mail | Keep if you use mail on this droplet |
| **PHP 8.3 and 8.4** | WP staging | Keep the version WordPress uses; you can uninstall the other later in Plesk |
| **Apache workers (~600 MB)** | Plesk backend for PHP/WP | **Do not uninstall.** Staging WordPress needs it. YetiBets is nginx → uvicorn; WP is nginx → Apache |
| **YetiHorses worker `--poll-seconds 2`** | Always-on, not 8–9am only | Product choice. FPL will **not** copy this; we use a 06:00 cron that exits |

Do not remove: nginx, MariaDB, Plesk panel, fail2ban, BIND, Imunify, YetiBets uvicorn.

Stale swap (570 MB) with 2.8 GB still available can stay. After 2AJ + journal vacuum it often shrinks on its own.

## Deploy FPL

Need Python 3.12+, git, DNS for **`fpl.ashbystudios.com`** at this VPS, and SSH as `fplpredictor` (see commands in chat / `docs/SERVER_OPS_LOG.md`).

```bash
sudo adduser --disabled-password --gecos "FPL" fplpredictor
sudo mkdir -p /opt/fplpredictor/data /opt/fplpredictor/logs
sudo chown -R fplpredictor:fplpredictor /opt/fplpredictor

sudo -u fplpredictor git clone https://github.com/T4shby/FPLpredictor.git /opt/fplpredictor
cd /opt/fplpredictor
sudo -u fplpredictor python3.12 -m venv .venv
sudo -u fplpredictor .venv/bin/pip install -e .
sudo -u fplpredictor cp deploy/plesk/env.plesk.example .env
# edit .env: APP_SECRET_KEY, ADMIN_API_TOKEN

sudo cp deploy/plesk/fpl-predictor.service /etc/systemd/system/
sudo cp deploy/plesk/fpl-predictor.cron /etc/cron.d/fpl-predictor
sudo chmod 644 /etc/cron.d/fpl-predictor
sudo systemctl daemon-reload
sudo systemctl enable --now fpl-predictor

# First prediction (can take 1–3 GB for a minute — run at a quiet time, not 8–9am)
sudo -u fplpredictor /opt/fplpredictor/.venv/bin/python scripts/run_daily_refresh.py
```

Plesk: add domain/subdomain → Apache & nginx → **nginx reverse proxy** to `http://127.0.0.1:8001`. Same pattern as YetiBets → `8000`. Issue SSL.

Check: `curl -sS http://127.0.0.1:8001/health`

## Daily behaviour

- **06:00 Europe/London:** cron runs `scripts/run_daily_refresh.py` and exits.
- **All day:** one uvicorn, MemoryMax 512 MB, SQLite, HTML from FastAPI (no Node).
