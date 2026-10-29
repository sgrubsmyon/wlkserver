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

## Configuration

Unlike the Java POS (`config.properties`), the Python API is configured through
**environment variables**. `python-dotenv` loads an optional `python/.env` file
at import time (`session.py`, `dependencies.py`); real environment variables take
precedence over `.env`. `.env` is git-ignored — never commit secrets.

| Variable | Default | Meaning |
|---|---|---|
| `DBHOST`, `DBNAME`, `DBUSER`, `DBPASS` | — | MariaDB connection used by `session.py` |
| `AUTH_SECRET` | dev placeholder | JWT signing secret — **must** be set in production |
| `AUTH_TOKEN_TTL` | `3600` | JWT lifetime in seconds |
| `CORS_ORIGINS` | SvelteKit dev server (`localhost:5173`, `127.0.0.1:5173`) | Comma-separated allowed browser origins |
| `TRAINING_MODE` | off | `1`/`true`/`yes`/`on` marks the instance as training mode |
| `TSE_DEVICE_PATH`, `TSE_LIB_PATH`, `TSE_CLIENT_ID` | unset / `WeltladenKasse` | TSE (cryptovision SE-API) adapter settings |
| `VAT_ROUNDING_METHOD` | `horizontal` | Receipt VAT rounding: `horizontal` (per position, Java POS) or `vertical` (per VAT rate, e-invoice compatible). Invalid values abort startup |
| `DSFINVK_EXPORT_DIR` | unset | Directory for the DSFinV-K ZIP written after every Tagesabschluss; unset means on-demand only |
| `DSFINVK_<KEY>` | see below | DSFinV-K Stammdaten (`Z_KASSE_ID`, `TAXONOMIE_VERSION`, `NAME`, `STRASSE`, `PLZ`, `ORT`, `LAND`, `STNR`, `USTID`, `LOC_*`, `KASSE_*`, `TERMINAL_*`) |

`VAT_ROUNDING_METHOD` affects only receipts/sales created from now on (the value
is stored in `verkauf_mwst`); existing sales keep their stored amounts. Invoices
must always use the vertical method (EN 16931 BR-CO-17) — see
`docs/VAT_ROUNDING.md` for the legal background.

## DSFinV-K export

`GET /export/dsfinvk/{abrechnung_tag_id}` builds the DSFinV-K files of one
Tagesabschluss (`cashpointclosing.csv`, `location.csv`, `cashregister.csv`,
`slaves.csv`, `pa.csv`, `vat.csv`, `tse.csv`, `businesscases.csv`,
`transactions_tse.csv` plus the official `index.xml` and DTD) and returns them
as a ZIP archive. `POST /abrechnung/tag` also writes `dsfinvk_<id>.zip` to
`DSFINVK_EXPORT_DIR` when that variable is set.

The Stammdaten come from `DSFINVK_*` environment variables; the shop's name,
address and tax numbers must be configured for a usable export (defaults match
the Java POS: `Z_KASSE_ID=YLUE036019`, `TAXONOMIE_VERSION=2.2`,
`KASSE_SW_BRAND=Weltladenkasse`, `KASSE_BASISWAEH_CODE=EUR`). Unconfigured
fields are exported empty. The column order, delimiters and number formatting
are read from `python/assets/dsfinvk/index.xml`.

## Admin access

Admin-only endpoints (POST/PATCH/DELETE on `/mwst` and `/pfand`, all `/users`
writes and `GET /auth/anmeldungen`) require a JWT for a user with role `admin`.
The API should run as the `kassenadmin` DB user (see
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
token and records a row in `anmeldung`. All endpoints except `/auth/login`
require `Authorization: Bearer <token>`. `POST /auth/refresh` issues a new
token, `POST /auth/logout` records the logout and invalidates the token, and
`GET /auth/me` returns the current user. `GET /auth/anmeldungen` (admin only)
lists the login audit. Failed logins are rate limited (5 per minute per
client and username).

## User administration

There is no public registration and no self-service password reset. The auth
migration (`migrations/02_user_auth/user_auth.sql`) bootstraps one admin:
username `admin`, password `changeme` — change it immediately. All other
accounts are created by an admin.

Authenticate first (`POST /auth/login`), then send
`Authorization: Bearer <token>` to the user endpoints (writes require `admin`,
reads are available to every logged-in user):

| Action | Endpoint |
|---|---|
| Create user | `POST /users/` with `{"username", "password", "role", "active"}` |
| List / read users | `GET /users/`, `GET /users/{user_id}` |
| Update user | `PATCH /users/{user_id}` (`username`, `role`, `active`, `password`) |
| Deactivate user | `POST /users/{user_id}/deactivate` (no delete endpoint) |
| Reset password | `POST /users/{user_id}/reset-password?new_password=...` |

Roles are `mitarbeiter` (normal POS operations and reads) and `admin`
(additionally MwSt/Pfand/user management and `GET /auth/anmeldungen`). Set or
change a role with `POST /users/` or `PATCH /users/{user_id}`. Deactivating a
user blocks existing tokens on the next request. Passwords are bcrypt-hashed;
the only password rule currently is non-empty.

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
