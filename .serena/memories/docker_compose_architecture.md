# Gultix - Pretix Docker Compose Setup (GDG Bogor)

## Project Overview
Gultix is a customized Pretix (event ticketing) deployment for GDG Bogor, with a Midtrans payment plugin and Google Font plugin. Based on `pretix/standalone:stable` image.

**Location**: `/home/avei/GithubRepo/GDGBogor/gultix/`

## Services

### postgres
- PostgreSQL 17
- Credentials from `.env` (`DB_USER`, `DB_PASSWORD`, `DB_SCHEMA`)
- Port 6666:5432 (host:container)
- Persistent volume: `postgres-data`

### redis
- Redis latest (with modules: RedisBloom, RediSearch, RedisTimeSeries, ReJSON)
- Persistent volume: `redis-data`

### task (anchor: `&pretix-common`)
- Runs celery task worker (`command: taskworker`)
- Uses original `pretix` entrypoint which runs `migrate` on startup
- Shares `pretix-data` volume at `/data`
- All pretix environment variables defined here (inherited by `web`)

### web
- Inherits from `&pretix-common` anchor
- `entrypoint: []` — bypasses the pretix entrypoint script
- Runs gunicorn directly: `gunicorn pretix.wsgi --bind 0.0.0.0:80`
- Port 8222:80
- Static files exist at `/pretix/src/pretix/static.dist/` (built at image build time via `pretix collectstatic --no-input` in Dockerfile)
- Django runs in production mode (DEBUG=False) — does NOT serve static files itself

### nginx
- Custom-built from `nginx:latest` via multi-stage Dockerfile (`target: nginx`)
- Static files are `COPY --from=pretix-build` at build time — no runtime copying or volume sharing needed
- Port 80:80
- Uses custom `nginx.conf` (mounted read-only)
- Routes:
  - `/static/*` → alias to `/pretix/src/pretix/static.dist/` (served directly by nginx, files baked into image)
  - `/media/*` → alias to `/data/media/` (shared volume)
  - `/*` → proxy_pass to `http://web:80` (gunicorn)

## Key Configuration Decisions

1. **Gunicorn on TCP port, not unix socket**: The original pretix entrypoint uses `--bind=unix:/tmp/pretix.sock`. We changed to `--bind 0.0.0.0:80` for Docker network compatibility.

2. **Entrypoint bypassed on web**: The `pretix` entrypoint script routes commands (`webworker`, `taskworker`, etc.). Since we override with `entrypoint: []` and run gunicorn directly, the script's `migrate` step is skipped on web. The `task` service handles migrations via its entrypoint.

3. **Static files served by nginx, not Django**: Django `DEBUG=False` returns 404 for static files. Nginx serves them directly from `/pretix/src/pretix/static.dist/`, which is baked into the nginx image via multi-stage `COPY --from=pretix-build`.

4. **nginx.conf**: Removed `include /etc/nginx/conf.d/*.conf;` to prevent the default nginx welcome page from conflicting. Removed `daemon off;` as the official nginx image handles this via its entrypoint.

5. **Postgres stale volumes**: If credentials change in `.env`, the postgres volume must be reset (`docker compose down -v`) since `POSTGRES_USER`/`POSTGRES_PASSWORD` only apply on first initialization.

## Dockerfile (Multi-Stage)

### Stage 1: `pretix-build` (used by `web` and `task` services)
- Based on `pretix/standalone:stable`
- Installs: `git`, `midtransclient`, `pretix-midtrans` plugin (private repo), `gultix-google-font` plugin (private repo)
- Runs `pretix collectstatic --no-input` at build time
- Runs as `pretixuser`
- Entrypoint: `pretix` (the shell script)

### Stage 2: `nginx` (used by `nginx` service)
- Based on `nginx:latest`
- Uses `COPY --from=pretix-build` to copy only `/pretix/src/pretix/static.dist/` from stage 1
- Static files are always in sync with the pretix build — no volumes or runtime copying needed

## Issues Resolved During Setup

1. **EMAIL_PORT ValueError**: Empty env var for mail port. Fixed by ensuring no empty env vars in docker-compose environment block.
2. **Postgres auth failed**: Stale volume with old credentials. Fixed by `docker compose down -v`.
3. **Gunicorn bind**: Changed from unix socket to TCP port (`0.0.0.0:80`) for Docker networking.
4. **nginx default page**: Removed `include /etc/nginx/conf.d/*.conf;` from nginx.conf.
5. **nginx daemon duplicate**: Removed `daemon off;` from nginx.conf (official image handles it).
6. **Static files 404**: Django DEBUG=False won't serve static files. Initially tried `volumes_from: web:ro` but `volumes_from` only shares declared volumes, not image layers. Fixed by using a multi-stage Dockerfile: nginx image gets static files via `COPY --from=pretix-build` at build time.
