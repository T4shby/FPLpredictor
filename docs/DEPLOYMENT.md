# Deployment (Ubuntu VPS, 16 GB RAM)

1. Install Docker and Docker Compose.
2. Clone this repository.
3. Copy `.env.example` to `.env` and set `APP_SECRET_KEY`, `ADMIN_API_TOKEN`, `POSTGRES_PASSWORD`, `DATABASE_URL`.
4. `docker compose up -d --build`
5. Check `http://<host>/health` and `/api/v1/status`.
6. Put TLS in front of nginx (Caddy, Traefik, or host nginx) — TODO if the VPS has a domain.

Resource targets are in `docker-compose.yml` (`mem_limit`). Do not load full historical tables into RAM; the worker processes Gameweeks incrementally.

Local Windows development does not require Docker. Use SQLite via `.env`.
