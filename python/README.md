## Do this only once

Source: https://fastapi.tiangolo.com/tutorial/

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run tests

```
pytest -q
```

## Admin token

Admin-only endpoints (POST/PATCH/DELETE on `/mwst` and `/pfand`) require
`Authorization: Bearer <ADMIN_TOKEN>`, where `ADMIN_TOKEN` is set in `.env`.
If `ADMIN_TOKEN` is not set, these endpoints refuse to work (503).
This is a stopgap until per-user accounts exist (Phase 7.4).

Note: the API should run as the `kassenadmin` DB user (see
`concepts/IMPLEMENTATION_PLAN.md`, Phase 7.4) so that admin operations
like DELETE are permitted by the database grants.

## Run API in development mode

```
source .venv/bin/activate
fastapi dev main.py
```

Or simply:

```
source .venv/bin/activate
fastapi dev
```

## Run API in production mode

```
source .venv/bin/activate
fastapi run
```

## Authentication

Per-user accounts are stored in the `user` table (see `migrations/02_user_auth/`).
Login via `POST /auth/login` with `{username, password}` returns a JWT bearer
token. Send it as `Authorization: Bearer <token>` on subsequent requests.
Admin-only endpoints (`/mwst`, `/pfand`, `/users`) accept either the shared
`ADMIN_TOKEN` (stopgap) or a token for a user with role `admin`.

## Transport security (HTTPS on the LAN)

The API and web app are intended for a local network. For production use an
internal CA certificate (e.g. via `mkcert`) and terminate TLS in a reverse
proxy (Caddy/nginx) in front of uvicorn, or pass `--ssl-keyfile`/`--ssl-certfile`
to uvicorn. Plain HTTP is only acceptable on a managed, isolated POS VLAN.

## Database migration

Run `migrations/02_user_auth/migrate.sh` (as kassenadmin) to create the
`user`/`anmeldung` tables and add `user_id` columns. Back up first.

## Testing

```
source .venv/bin/activate
pytest -q
```

Coverage (optional): `pip install pytest-cov && pytest --cov=python --cov-report=term-missing`

* https://fastapi.tiangolo.com/tutorial/bigger-applications/#another-module-with-apirouter
* https://fastapi.tiangolo.com/tutorial/sql-databases/
