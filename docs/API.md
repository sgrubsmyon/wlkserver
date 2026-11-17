# Weltladenkasse API - Documentation

The FastAPI backend behind the shop's POS. It owns the business logic and all
database access; the web client only renders what this API returns.

- [API_REFERENCE.md](API_REFERENCE.md) - every endpoint with parameters,
  request bodies and responses (generated from the OpenAPI schema)
- [DATABASE.md](DATABASE.md) - tables, keys and bookkeeping rules
- [KASSENSTAND_UND_ABRECHNUNG.md](KASSENSTAND_UND_ABRECHNUNG.md) - cash
  register and settlement flow with request/response examples
- [MIGRATION_JAVA_TO_API.md](MIGRATION_JAVA_TO_API.md) - cutover from the Java POS
- [VAT_ROUNDING.md](VAT_ROUNDING.md) - rounding method and its legal background
- `python/README.md` - development setup; `deployment/README.md` - production

## Base URL

- Production (same-origin behind nginx): `https://<host>/api/...`
- Development / direct server access: `http://localhost:8000/...`

Behind nginx the API is mounted at `/api`; the proxy strips the prefix and
Uvicorn's `--root-path /api` puts it back into generated URLs. Swagger UI is at
`/api/docs`, ReDoc at `/api/redoc`, the OpenAPI JSON at `/api/openapi.json`
(without the prefix when calling the API directly).

## Authentication

`POST /auth/login` with `{username, password}` returns
`{access_token, token_type, user}`. Send `Authorization: Bearer <token>` on
every other request - including reads. Tokens expire after `AUTH_TOKEN_TTL`
(default one hour); use `POST /auth/refresh` before or `POST /auth/login`
again after expiry.

- Failed logins are rate limited (5 per minute per client and username).
- `GET /auth/me`, `PATCH /auth/me` (theme preference) and
  `POST /auth/passwort` (password change) are self-service.
- Roles: `mitarbeiter` (POS operations and reads) and `admin` (additionally
  MwSt/Pfand/user management, `GET /auth/anmeldungen`, all TSE operations).
- Every transaction records the authenticated user (`user_id` from the token);
  a client-supplied `user_id` is ignored.
- Logout (`POST /auth/logout`) records the logout time and invalidates the
  token.

The API is stateless: a browser client may keep the token in an httpOnly
cookie, but the API itself only reads the `Authorization` header. Scripts log
in per run with a dedicated service account (visible in the `anmeldung` audit).

## Errors

Errors are JSON: `{"detail": "message"}` (validation errors from FastAPI use
`{"detail": [{"loc": [...], "msg": ...}]}`).

| Status | Meaning |
|---|---|
| 400 | Domain rule violated (e.g. amount too high, discount not applicable, unknown article) |
| 401 | Missing, invalid or expired token |
| 403 | Authenticated but not `admin` |
| 404 | Unknown id / receipt / settlement |
| 422 | Request body or query parameter failed schema validation (types, ranges, `storno_von` set by a client, ...) |

Business errors are raised as `DomainError`/`NotFoundError` in
`python/business/` and mapped at the HTTP boundary only, so the same rules apply
to every caller.

## Conventions

- **Pagination:** every list endpoint takes `offset` (default 0) and `limit`
  (default and maximum 100). Responses are plain JSON arrays, without a total
  count.
- **Filters:** `search_string` on the master-data lists; `aktiv_only`,
  `barcode`, `artikel_nr`, `lieferant_id`, `produktgruppen_id` on `/artikel`;
  `von`/`bis` ISO-8601 datetimes on `/verkauf` and `/bestellung`; `typ`
  (`LM`/`KHW`/`IVT`) on `/bestellung`; `rechnungen` on `/kassenstand`;
  `desc=true` on the settlement lists.
- **Money** is a JSON number in euros (stored as `DECIMAL(13,2)`); VAT rates are
  fractions (`0.19`). Clients display, they do not recalculate.
- **Dates** are ISO-8601 and stored/returned in UTC. Send timezone offsets or
  `Z`; naive values are treated as UTC.
- **No updates on bookkeeping tables.** `verkauf`, `verkauf_mwst`,
  `verkauf_details`, `kassenstand`, `gutschein`, `anzahlung` and the
  settlements are immutable. Correct with a storno (`POST
  /verkauf/{rechnungs_nr}/storno`) or a new entry; a receipt inside a completed
  Tagesabschluss cannot be stornoed (400).
- **Concurrency:** keep the API at one worker. Voucher and cash-register
  updates are serialized with a process lock and `SELECT ... FOR UPDATE`.

## Endpoint groups

| Prefix | Purpose |
|---|---|
| `/artikel`, `/lieferant`, `/produktgruppe`, `/rabattaktion` | Master data; deactivation instead of deletion, price edits create article versions, pictures at `/artikel/{id}/bild` |
| `/mwst`, `/pfand` | VAT rates and deposit items (writes admin-only) |
| `/verkauf` | Sales and stornos: Pfand, discounts, vouchers, installments, cash register and TSE side effects |
| `/warenkorb` | Stateless cart helpers (add article, Leergut, discount, Anzahlung, totals) using the same rules as `POST /verkauf` |
| `/kassenstand` | Cash-drawer ledger, current balance, reset suggestion (`POST /kassenstand/zuruecksetzen/vorschau`) |
| `/gutschein` | Voucher ledger: create, redeem, outstanding/redeemed |
| `/anzahlung` | Down payments: create, resolve, open/resolved, details |
| `/abrechnung/tag`, `/monat`, `/jahr` | Daily, monthly and yearly settlements; `vorschau` previews the open day |
| `/zaehlprotokoll` | Cash count protocols (attached to a settlement) |
| `/bestellung` | Orders and inventory counts with positions |
| `/tse` | TSE status, commissioning/preflight/unblock, transaction lifecycle, exports |
| `/import`, `/export` | CSV import (articles, orders) and exports (articles, orders, inventory, settlement, DSFinV-K zip) |
| `/users` | Admin user management, deactivation, password reset |
| `/training` | Training-mode status and reset (sandbox database) |

## Setup

See `python/README.md` for development and `deployment/README.md` for
production (database, systemd units, TLS, nginx, backups).
