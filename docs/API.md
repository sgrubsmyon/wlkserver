# Weltladenkasse API - Documentation

## Interactive API documentation

FastAPI generates interactive documentation automatically:

- Swagger UI: `http://<host>:8000/docs`
- ReDoc: `http://<host>:8000/redoc`
- OpenAPI JSON: `http://<host>:8000/openapi.json`

## Base URL

All endpoints are served from the root of the API (default `http://localhost:8000`).

## Authentication

- `POST /auth/login` — `{username, password}` → `{access_token, token_type, user}` (rate limited)
- `POST /auth/refresh` — new token for a valid session (Bearer token)
- `POST /auth/logout` — records logout and invalidates the token (Bearer token)
- `GET /auth/me` — current user
- `GET /auth/anmeldungen` — login audit, admin only

Every endpoint except `POST /auth/login` requires
`Authorization: Bearer <token>`. Admin-only endpoints (`/mwst`, `/pfand`,
`/users` writes, `GET /auth/anmeldungen`) require a user with role `admin`.

## Endpoint groups

- `/artikel`, `/lieferant`, `/produktgruppe`, `/rabattaktion` — master data (CRUD)
- `/mwst`, `/pfand` — VAT rates and deposits (admin-only write)
- `/verkauf` — sales (create, read, storno)
- `/kassenstand` — cash register balance
- `/gutschein` — vouchers
- `/anzahlung` — installment payments
- `/abrechnung/tag`, `/abrechnung/monat`, `/abrechnung/jahr` — settlements
- `/zaehlprotokoll` — counting protocols
- `/bestellung` — orders incl. positions (details)
- `/tse` — TSE transactions and exports
- `/import`, `/export` — CSV import/export
- `/users` — admin user management

## Bookkeeping integrity

Tables `verkauf`, `kassenstand`, `gutschein`, `anzahlung`, `abrechnung_tag`
are immutable: no UPDATE/DELETE endpoints. Corrections are made via Storno
(`POST /verkauf/{rechnungs_nr}/storno`) and new entries.

## Setup

See `python/README.md`.