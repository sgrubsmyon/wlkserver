## Do this only once

Source: https://fastapi.tiangolo.com/tutorial/

```
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run in dev mode

```
source venv/bin/activate
fastapi dev
# (or:)
fastapi dev --port 8080
```

## Run in production mode

Run from the `python/` directory, where the venv lives. `--app-dir ..` puts the
repository root on the import path, so the `python.main` package resolves:

```
venv/bin/uvicorn --app-dir .. python.main:app --host 127.0.0.1 --port 8000 --root-path /api
```

Or from the repository root:

```
python/venv/bin/uvicorn --app-dir . python.main:app --host 127.0.0.1 --port 8000 --root-path /api
```

`--root-path /api` makes generated URLs (`/docs`, `/openapi.json`) match the
nginx prefix; see `../deployment/nginx-wlkserver.conf`. Without nginx, use
`--host 0.0.0.0` and drop `--root-path` for direct access on the LAN.

Without `--app-dir`, or when started from any other directory, uvicorn cannot
find the package and fails with `ModuleNotFoundError: No module named 'python'`.

Keep it at one worker (`--workers 1`, the default): the TSE client serializes
SE-API calls with a per-process lock, so a second worker would break that
guarantee.

For a server, use the systemd unit in `../deployment/wlkserver.service` (its
`WorkingDirectory` is the repository root, so no `--app-dir` is needed there):
adjust its paths and `User`, then from the repository root

```
sudo cp deployment/wlkserver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wlkserver
```

## Run tests

```
pytest -q              # whole suite
pytest -q tests/unit   # domain/service tests, no HTTP client
pytest -q tests/api    # endpoint contract tests via TestClient
```

`tests/unit/` calls the business/use-case functions directly; `tests/api/` covers
status codes, payload shapes, auth and filters through the app's test client.

## Configuration

Unlike the Java POS (`config.properties`), the Python API is configured through
**environment variables**. Every variable is read in one place, `python/config.py`
(which also loads the optional `python/.env` via `python-dotenv`); real environment
variables take precedence over `.env`. Values are read on access, not cached, so a
changed variable applies without a restart (except the DB engine, which is created
once). `.env` is git-ignored — never commit secrets.

| Variable | Default | Meaning |
|---|---|---|
| `DBHOST`, `DBNAME`, `DBUSER`, `DBPASS` | — | MariaDB connection used by `session.py` (`config.database_url()`) |
| `AUTH_SECRET` | dev placeholder | JWT signing secret — **must** be set in production |
| `AUTH_TOKEN_TTL` | `3600` | JWT lifetime in seconds |
| `CORS_ORIGINS` | SvelteKit dev server (`localhost:5173`, `127.0.0.1:5173`) | Comma-separated allowed browser origins |
| `TRAINING_MODE` | off | `1`/`true`/`yes`/`on` runs the whole instance against the training database |
| `TRAINING_DB_URL` | — | SQLAlchemy URL of the **persistent** training sandbox (a separate MariaDB database); required when `TRAINING_MODE` is set. In-memory SQLite is rejected |
| `TSE_DEVICE_PATH`, `TSE_LIB_PATH`, `TSE_CLIENT_ID` | unset / `WeltladenKasse` | TSE (cryptovision SE-API) adapter settings |
| `TSE_TIME_ADMIN_PIN` | unset | TimeAdmin PIN, needed for the time update the TSE requires after every power-up |
| `TSE_ID` | unset | TSE number stored in `abrechnung_tag_tse` (Java `bc.TSE_ID`, used by DSFinV-K) |
| `TSE_COMMISSIONING_LOG` | `python/tse_commissioning.jsonl` | JSONL file recording the TSE commissioning steps (no PINs/PUKs) |
| `VAT_ROUNDING_METHOD` | `horizontal` | Receipt VAT rounding: `horizontal` (per position, Java POS) or `vertical` (per VAT rate, e-invoice compatible). Invalid values abort startup |
| `DSFINVK_EXPORT_DIR` | unset | Directory for the DSFinV-K ZIP written after every Tagesabschluss; unset means on-demand only |
| `IMAGES_DIR` | unset | Directory with the article pictures (`<artikel_id>.jpg|png|webp`); unset disables the picture endpoints (503) |
| `VORLAGEN_DIR` | `../git/vorlagen` | ODS templates for the exports (`Bestellvorlage_*.ods`, `Inventur.ods`, `Tages-/Monats-/Jahresabrechnung.ods`); a missing template fails that export |

Article pictures are files, not DB rows: `PUT /artikel/{id}/bild` (multipart
field `bild`, max. 5 MB, JPEG/PNG/WebP detected by magic bytes) stores
`<id>.<ext>`, `GET /artikel/{id}/bild` serves the bytes with `ETag` and
`DELETE /artikel/{id}/bild` removes them. All three require a login. When
`PATCH /artikel/{id}` creates a new version, the picture is hardlinked to the
new id, so both ids share one file on disk.
| `DSFINVK_<KEY>` | see below | DSFinV-K Stammdaten (`Z_KASSE_ID`, `TAXONOMIE_VERSION`, `NAME`, `STRASSE`, `PLZ`, `ORT`, `LAND`, `STNR`, `USTID`, `LOC_*`, `KASSE_*`, `TERMINAL_*`) |

`VAT_ROUNDING_METHOD` affects only receipts/sales created from now on (the value
is stored in `verkauf_mwst`); existing sales keep their stored amounts. Invoices
must always use the vertical method (EN 16931 BR-CO-17) — see
`docs/VAT_ROUNDING.md` for the legal background.

## TSE C library

The TSE adapter (`utils/tse_client.py`) calls the cryptovision SE-API through
ctypes. The compiled Linux x86-64 libraries are vendored in
`../assets/SE-API-C/bin/` and committed, so no compiler is needed: `pip install
-r requirements.txt` is the complete setup. The library is loaded from
`TSE_LIB_PATH` if set, otherwise from `assets/SE-API-C/bin/libse-api-c.so`,
otherwise from the system search path (`ldd` must find
`libse-msc-io_linux-x86-64.so` next to it).

The `.c` sources in `assets/SE-API-C/` are only needed to rebuild the binaries,
e.g. for another architecture or a new vendor release:

```
cd assets/SE-API-C
rm -rf build              # build-c-linux.sh refuses to reuse an existing build dir
./build-c-linux.sh        # needs cmake and gcc, writes into bin/
```

Keep the complete `bin/` folder in sync — the main library loads the MSC I/O
shared object at runtime.

## Training mode

The Java POS only redirects the cashier tables to `training_*` tables; editing
articles or discount actions there still changes production master data. The API
instead runs the **whole instance** against a separate, **persistent** database.
It has to be persistent because training receipts are signed on the real TSE:
they consume real transaction numbers and signature counters, so their
`tse_transaction` rows must stay reconcilable after a restart.

```sql
CREATE DATABASE weltladen_training CHARACTER SET utf8 COLLATE utf8_general_ci;
GRANT ALL PRIVILEGES ON weltladen_training.* TO 'kassenadmin'@'localhost';
```

```sh
TRAINING_MODE=1 \
TRAINING_DB_URL='mariadb+mariadbconnector://kassenadmin:PASS@localhost/weltladen_training' \
fastapi run
```

On startup the API creates the schema in the sandbox (from `models/tables.py`), mirrors
the production users (authentication and the `user_id` attributes need them)
and seeds a short test catalog. The catalog is only seeded when the sandbox has
no articles yet; startup never wipes existing training data, and `POST
/training/reset` (below) is the only reset. The catalog covers:

| Article | Purpose |
|---|---|
| `T-19`, `T-7`, `T-0` | fixed prices at 19 %, 7 % and 0 % VAT |
| `T-VAR` | variable price (send `ges_preis` on the sale line) |
| `T-PFAND` | product group with a deposit; the Pfand line is added automatically |
| `T-AKTION` | 19 % article with an active 10 % discount action |
| `RABATT1`, `RABATT2`, `ANPASSUNG`, `ANZAHLUNG`, `ANZAHLAUFLOES`, `GUTSCHEIN`, `GUTSCHEINEINLOES`, `PFAND` | internal articles required by the sale workflows |

Sales, storno, vouchers, installments, counting protocols and all three
settlements write to the sandbox; `POST /training/reset` (admin only, training
mode only) clears it and seeds the catalog again. TSE exports and the automatic
DSFinV-K files are skipped in training mode (the DSFinV-K download endpoint
still works on sandbox data).

The training instance needs access to the production database for the user
mirror. Never point `TRAINING_DB_URL` at the production database — startup
refuses a matching non-SQLite URL. The legacy `training_*` tables of the Java
POS are not used by the API anymore and are dropped by
`migrations/05_drop_training_tables/`.

## DSFinV-K export

`GET /export/dsfinvk/{abrechnung_tag_id}` builds the DSFinV-K files of one
Tagesabschluss (`cashpointclosing.csv`, `location.csv`, `cashregister.csv`,
`slaves.csv`, `pa.csv`, `vat.csv`, `tse.csv`, `businesscases.csv`,
`transactions_tse.csv` plus the official `index.xml` and DTD) and returns them
as a ZIP archive. Training receipts (`training = TRUE`, from the training
database) are never included in `transactions_tse.csv`.
`POST /abrechnung/tag` also writes `dsfinvk_<id>.zip` to
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
internal CA certificate and terminate TLS in nginx, which also serves the
SvelteKit client and proxies the API under `/api/` (same origin, so CORS is not
involved). The files and step-by-step guide are in `deployment/`:
`nginx-wlkserver.conf`, `make_tls_cert.sh`, `README.md`. Plain HTTP is only
acceptable on a managed, isolated POS VLAN.

## Database migration

Run `migrations/02_user_auth/migrate.sh` (as kassenadmin) to create the
`user`/`anmeldung` tables and add `user_id` columns, then
`migrations/03_gutschein_counter/migrate.sh` to create and seed the
`gutschein_counter` row used for server-side voucher numbers. Back up first.

## Testing

```
source venv/bin/activate
pytest -q
```

The suite defaults to a fresh in-memory SQLite database. To run it against
MariaDB, create the disposable `kasse_test` database once
(`../deployment/create_test_db.sh`, asks for sudo) and then run
`./run_tests_mariadb.sh` (asks for the `kassenadmin` password).

Coverage (optional): `pip install pytest-cov && pytest --cov=python --cov-report=term-missing`

## Documentation

The docs live in `../docs/`: `API.md` (overview, auth, errors, conventions),
`API_REFERENCE.md` (all endpoints, generated from the OpenAPI schema),
`DATABASE.md` (schema and bookkeeping rules), `KASSENSTAND_UND_ABRECHNUNG.md`,
`MIGRATION_JAVA_TO_API.md` and `VAT_ROUNDING.md`. Deployment is covered by
`../deployment/README.md`.

Regenerate the generated files after changing endpoints or the schema:

```
python/venv/bin/python ../docs/generate_api_reference.py
python/venv/bin/python ../docs/generate_db_reference.py
```

* https://fastapi.tiangolo.com/tutorial/bigger-applications/#another-module-with-apirouter
* https://fastapi.tiangolo.com/tutorial/sql-databases/
