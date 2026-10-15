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

* https://fastapi.tiangolo.com/tutorial/bigger-applications/#another-module-with-apirouter
* https://fastapi.tiangolo.com/tutorial/sql-databases/
