# wlkserver

This repository contains the server backend with the HTTP-based API to interact with the SQL database.

This is meant as being part of a new, more modern, more modular server/client architecture of the fair trade shop point-of-sale system [Weltladenkasse](https://github.com/sgrubsmyon/Weltladenkasse).

The API is written with Python's [FastAPI](https://fastapi.tiangolo.com/), so you only need a
minimal amount of code to get an API running. It also provides automatic
documentation/testing via Swagger at `/docs`. The database is MariaDB.

## Documentation

- [`docs/API.md`](docs/API.md) - overview: base URL, authentication, errors,
  conventions, endpoint groups
- [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) - every endpoint with
  parameters, request bodies and responses (generated from the OpenAPI schema)
- [`docs/DATABASE.md`](docs/DATABASE.md) - tables, keys and bookkeeping rules
- [`docs/KASSENSTAND_UND_ABRECHNUNG.md`](docs/KASSENSTAND_UND_ABRECHNUNG.md) -
  cash register and settlement flow with examples
- [`docs/MIGRATION_JAVA_TO_API.md`](docs/MIGRATION_JAVA_TO_API.md) - cutover
  from the Java POS
- [`docs/VAT_ROUNDING.md`](docs/VAT_ROUNDING.md) - VAT rounding and its legal
  background
- `python/README.md` - development setup and environment variables;
  `deployment/README.md` - production: systemd, TLS, nginx, backups, training
  instance

## Install from scratch on Ubuntu

The following instructions assume a fresh Ubuntu Linux (24.04 or newer) with
nothing installed and a checkout of this repository. All commands are run from
the repository root.

### 1. Install the system packages

```
sudo apt update
sudo apt install -y mariadb-server python3-venv build-essential pkg-config libmariadb-dev git
sudo systemctl enable --now mariadb
```

`build-essential`, `pkg-config` and `libmariadb-dev` are needed to build the
Python MariaDB connector (`mariadb`).

Harden the MariaDB installation (set a root password, remove anonymous users
and the test database):

```
sudo mariadb-secure-installation
```

### 2. Create the database users

The API connects as `kassenadmin`; `mitarbeiter` keeps the limited privileges
of the Java POS cashier software. Pick your own passwords:

```
sudo mariadb
```

```sql
CREATE USER 'kassenadmin'@'localhost' IDENTIFIED BY 'your-admin-password';
CREATE USER 'mitarbeiter'@'localhost' IDENTIFIED BY 'your-cashier-password';
```

The users must exist before the next step, because the creation script grants
their privileges.

### 3. Create and seed the database

```
sudo mariadb < deployment/create_db.sql
```

This **drops and recreates** the databases `kasse` and `kasse_training`, creates all tables
(the Java POS schema plus all migrations from `migrations/`), fills in the
master data (VAT rates, internal articles/groups, deposit articles, plus the
example suppliers/groups/articles of `../git/mysql/fillWithExampleData.sql`),
creates the bootstrap `admin` user and grants the privileges for both database
users. There is no separate migration step for a fresh install.

Check the result:

```
sudo mariadb kasse -e "SHOW TABLES; SELECT username, role FROM user;"
```

### 4. Install the Python environment and configure the API

```
python3 -m venv python/venv
python/venv/bin/pip install --upgrade pip
python/venv/bin/pip install -r python/requirements.txt
```

Create `python/.env` (git-ignored — never commit it) with at least:

```
DBHOST=localhost
DBNAME=kasse
DBUSER=kassenadmin
DBPASS=your-admin-password
AUTH_SECRET=<long random value>
```

Generate the secret with
`python3 -c "import secrets; print(secrets.token_hex(32))"`.
`AUTH_SECRET` must not be the dev placeholder in production. All further
variables (TSE, DSFinV-K, CORS, images, training mode) are listed in the table
in `python/README.md`.

### 5. Start the API

For development (auto-reload, docs at http://localhost:8000/docs):

```
python/venv/bin/fastapi dev
```

For production, run it from the repository root (one worker only, the TSE
client needs a per-process lock). It listens on localhost and is published
under `/api` by nginx:

```
python/venv/bin/uvicorn python.main:app --host 127.0.0.1 --port 8000 --workers 1 --root-path /api
```

To run it as a systemd service with TLS, nginx and backups, follow
`deployment/README.md` (service user, `/opt/wlkserver` layout,
`wlkserver.service`, `nginx-wlkserver.conf`, `wlkserver-backup.timer`).

### 6. Change the bootstrap admin password

The database ships with the `admin` user and the password `changeme`.
Log in and reset it right away — either in the Swagger UI at `/docs` or with:

```
curl -X POST http://localhost:8000/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"username": "admin", "password": "changeme"}'
```

Take the `access_token` from the response and call:

```
curl -X POST "http://localhost:8000/users/1/reset-password?new_password=your-new-password" \
    -H "Authorization: Bearer <access_token>"
```

Additional cashier accounts can then be created via `POST /users/`
(admin only).

### Optional: training database

`deployment/create_db.sql` already creates the empty `kasse_training` database
and grants `kassenadmin` access to it. The training schema and test catalog are
created automatically on API startup of the training instance.

Use a **second** API instance for it, never the production instance:
`deployment/wlkserver-training.service` sets `TRAINING_MODE=1` itself. Add only
the sandbox URL to `python/.env` (ignored while training mode is off):

```
TRAINING_DB_URL=mariadb+mariadbconnector://kassenadmin:your-admin-password@localhost/kasse_training
```

Do not put `TRAINING_MODE` into `.env`: the production unit reads the same file.
See `deployment/README.md`, step 8.

### Run the tests

```
cd python
venv/bin/pytest -q              # whole suite
venv/bin/pytest -q tests/unit   # domain/service tests, no HTTP client
venv/bin/pytest -q tests/api    # endpoint contract tests via TestClient
```

`tests/unit/` calls the business/use-case functions directly; `tests/api/` covers
status codes, payload shapes, auth and filters through the app's test client.
