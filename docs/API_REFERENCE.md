# API reference

Generated from the OpenAPI schema by `docs/generate_api_reference.py` - do not
edit by hand. Regenerate after changing endpoints, parameters or schemas:

```
python/venv/bin/python docs/generate_api_reference.py
```

The hand-written overview (base URL, authentication, error format, endpoint
groups) is in [`API.md`](API.md); settlement details with examples are in
[`KASSENSTAND_UND_ABRECHNUNG.md`](KASSENSTAND_UND_ABRECHNUNG.md).

## Authentication

Every endpoint except `POST /auth/login` requires
`Authorization: Bearer <token>` from `POST /auth/login`. "admin" below means
the token belongs to an active user with role `admin`; such requests also
need a logged-in user. A missing or invalid token is `401`, an insufficient
role is `403`.

## Index

| Method | Path | Access | Summary |
|---|---|---|---|
| `GET` | `/` | public | root |
| `GET` | `/abrechnung/jahr/` | logged-in user | List yearly settlements with pagination, ascending or descending by id. |
| `POST` | `/abrechnung/jahr/` | logged-in user | Settle a year from its monthly settlements (logged-in only). |
| `GET` | `/abrechnung/jahr/offen` | logged-in user | Years with monthly settlements that are not settled yet. |
| `GET` | `/abrechnung/jahr/{jahr_id}` | logged-in user | Read one yearly settlement including its VAT rows; 404 when unknown. |
| `GET` | `/abrechnung/monat/` | logged-in user | List monthly settlements with pagination, ascending or descending by id. |
| `POST` | `/abrechnung/monat/` | logged-in user | Settle a month from its daily settlements (logged-in only). |
| `GET` | `/abrechnung/monat/offen` | logged-in user | Months (`YYYY-MM`) with daily settlements that are not settled yet. |
| `GET` | `/abrechnung/monat/{monat_id}` | logged-in user | Read one monthly settlement including its VAT rows; 404 when unknown. |
| `GET` | `/abrechnung/tag/` | logged-in user | List daily settlements with pagination, ascending or descending by id. |
| `POST` | `/abrechnung/tag/` | logged-in user | Close the open period and return the new Tagesabschluss (logged-in only). |
| `GET` | `/abrechnung/tag/offen` | logged-in user | Distinct sale dates (ISO) that are not covered by a settlement yet. |
| `GET` | `/abrechnung/tag/vorschau` | logged-in user | Preview the open Tagesabschluss without writing anything. |
| `GET` | `/abrechnung/tag/{tag_id}` | logged-in user | Read one daily settlement including its VAT rows; 404 when unknown. |
| `GET` | `/anzahlung/` | logged-in user | List installment rows, optionally filtered by the two receipt references. |
| `POST` | `/anzahlung/` | logged-in user | Record a down payment for a receipt, optionally with its detail rows. |
| `GET` | `/anzahlung/aufgeloest` | logged-in user | Resolution rows, i.e. installments that were applied to a sale. |
| `POST` | `/anzahlung/details` | logged-in user | Append one installment detail row; sale and sale position must exist. |
| `GET` | `/anzahlung/offen` | logged-in user | Installments that are not yet resolved by a later sale. |
| `GET` | `/anzahlung/{anzahlung_id}` | logged-in user | Read one installment row by id; 404 when it does not exist. |
| `POST` | `/anzahlung/{anzahlung_id}/aufloesen` | logged-in user | Resolve an open installment by appending the resolution row. |
| `GET` | `/anzahlung/{anzahlung_id}/details` | logged-in user | Detail rows booked for the installment receipt; 404 for unknown installments. |
| `GET` | `/artikel/` | logged-in user | List articles with filters and pagination. |
| `POST` | `/artikel/` | logged-in user | Create an article; 400 if supplier and artikel_nr already exist. |
| `DELETE` | `/artikel/{artikel_id}` | logged-in user | Deactivate an article instead of deleting the row. |
| `GET` | `/artikel/{artikel_id}` | logged-in user | Read one article incl. product group, supplier and Pfand details. |
| `PATCH` | `/artikel/{artikel_id}` | logged-in user | Update an article, creating a new version when needed. |
| `DELETE` | `/artikel/{artikel_id}/bild` | logged-in user | Delete the picture of an article; 404 if there is none. |
| `GET` | `/artikel/{artikel_id}/bild` | logged-in user | Serve the article picture; 404 if the article has none. |
| `PUT` | `/artikel/{artikel_id}/bild` | logged-in user | Replace the picture of an article (JPEG, PNG or WebP, max. 5 MB). |
| `GET` | `/auth/anmeldungen` | admin | List login records (admin only), newest first, optionally per user. |
| `POST` | `/auth/login` | public | Verify credentials and return a bearer token for the user. |
| `POST` | `/auth/logout` | public | Record the logout time of the token's `Anmeldung`; always succeeds. |
| `GET` | `/auth/me` | logged-in user | Return the authenticated user. |
| `PATCH` | `/auth/me` | logged-in user | Self-service preferences (currently the preferred theme). |
| `POST` | `/auth/passwort` | logged-in user | Change the own password; the current one must match. |
| `POST` | `/auth/refresh` | logged-in user | Issue a new token for the current user, keeping the `anmeldung_id` claim. |
| `GET` | `/bestellung/` | logged-in user | List orders, optionally filtered by typ and order date range. |
| `POST` | `/bestellung/` | logged-in user | Create an order with optional positions and return it. |
| `DELETE` | `/bestellung/{bestell_nr}` | logged-in user | Delete an order and its positions; 404 when it does not exist. |
| `GET` | `/bestellung/{bestell_nr}` | logged-in user | Read one order including its positions; 404 when it does not exist. |
| `PATCH` | `/bestellung/{bestell_nr}` | logged-in user | Patch an order and, when details are sent, replace its positions. |
| `GET` | `/gutschein/` | logged-in user | List voucher rows with pagination, optionally filtered by voucher number. |
| `POST` | `/gutschein/` | logged-in user | Issue a voucher: allocate the next voucher number and append the start row. |
| `GET` | `/gutschein/ausstehend` | logged-in user | Vouchers that still carry a balance, with their original start value. |
| `GET` | `/gutschein/eingeloest` | logged-in user | Vouchers whose remaining balance is zero (fully redeemed). |
| `GET` | `/gutschein/{gutschein_id}` | logged-in user | Read one voucher row by id; 404 when it does not exist. |
| `POST` | `/gutschein/{gutschein_id}/einloesen` | logged-in user | Redeem (part of) a voucher and return the new balance row. |
| `GET` | `/export/abrechnung` | logged-in user | Download the settlements as a CSV file. |
| `GET` | `/export/artikel` | logged-in user | Download all articles as a CSV file. |
| `GET` | `/export/bestellung` | logged-in user | Download the orders as a CSV file. |
| `GET` | `/export/dsfinvk/{abrechnung_tag_id}` | logged-in user | DSFinV-K export of one Tagesabschluss as a ZIP archive. |
| `GET` | `/export/inventur` | logged-in user | Download the stock-taking (Inventur) list as a CSV file. |
| `POST` | `/import/artikel` | logged-in user | Import articles from an uploaded CSV and report how many were created. |
| `POST` | `/import/bestellung` | logged-in user | Import orders from an uploaded CSV and report how many were created. |
| `GET` | `/kassenstand/` | logged-in user | List cash drawer bookings, newest first. |
| `POST` | `/kassenstand/` | logged-in user | Append a manual cash drawer booking and return it. |
| `GET` | `/kassenstand/aktuell` | logged-in user | The current (latest) cash balance, or null while no booking exists. |
| `POST` | `/kassenstand/zuruecksetzen/vorschau` | logged-in user | Suggestion for bringing the counted drawer back to its target stock. |
| `GET` | `/kassenstand/{kassenstand_id}` | logged-in user | Read one ledger entry by id; 404 when it does not exist. |
| `GET` | `/lieferant/` | logged-in user | List suppliers with filters and pagination. |
| `POST` | `/lieferant/` | logged-in user | Create a supplier; 400 if the name already exists. |
| `DELETE` | `/lieferant/{lieferant_id}` | logged-in user | Deactivate a supplier instead of deleting it. |
| `GET` | `/lieferant/{lieferant_id}` | logged-in user | Read one supplier by id; 404 if unknown. |
| `PATCH` | `/lieferant/{lieferant_id}` | logged-in user | Update a supplier by deactivating it and creating a new version. |
| `GET` | `/mwst/` | logged-in user | List VAT rates with search and pagination. |
| `POST` | `/mwst/` | admin | Create a VAT rate (admin only); 400 if the rate already exists. |
| `DELETE` | `/mwst/{mwst_id}` | admin | Delete a VAT rate (admin only). |
| `GET` | `/mwst/{mwst_id}` | logged-in user | Read one VAT rate by id; 404 if unknown. |
| `PATCH` | `/mwst/{mwst_id}` | admin | Update a VAT rate (admin only); 400 if the new rate already exists. |
| `PUT` | `/mwst/{mwst_id}` | admin | Replace a VAT rate (admin only); same behaviour as PATCH. |
| `GET` | `/pfand/` | logged-in user | List Pfand entries, optionally filtered by deposit value. |
| `POST` | `/pfand/` | admin | Create a Pfand for an article (admin only). |
| `DELETE` | `/pfand/{pfand_id}` | admin | Delete a Pfand (admin only). |
| `GET` | `/pfand/{pfand_id}` | logged-in user | Read one Pfand including its value; 404 if unknown. |
| `PATCH` | `/pfand/{pfand_id}` | admin | Update a Pfand (admin only). |
| `PUT` | `/pfand/{pfand_id}` | admin | Replace a Pfand (admin only); same behaviour as PATCH. |
| `GET` | `/produktgruppe/` | logged-in user | List product groups with filters and pagination. |
| `POST` | `/produktgruppe/` | logged-in user | Create a product group; 400 if the name already exists. |
| `DELETE` | `/produktgruppe/{produktgruppen_id}` | logged-in user | Deactivate a product group instead of deleting it. |
| `GET` | `/produktgruppe/{produktgruppen_id}` | logged-in user | Read one product group by id; 404 if unknown. |
| `PATCH` | `/produktgruppe/{produktgruppen_id}` | logged-in user | Update a product group by deactivating it and creating a new version. |
| `GET` | `/rabattaktion/` | logged-in user | List discount campaigns with date, article and group filters. |
| `POST` | `/rabattaktion/` | logged-in user | Create a discount campaign and validate its discount rules. |
| `DELETE` | `/rabattaktion/{rabattaktion_id}` | logged-in user | End a campaign by moving its `bis` date instead of deleting the row. |
| `GET` | `/rabattaktion/{rabattaktion_id}` | logged-in user | Read one discount campaign; 404 if unknown. |
| `PATCH` | `/rabattaktion/{rabattaktion_id}` | logged-in user | Update a campaign; started campaigns allow only name and `bis`. |
| `POST` | `/training/reset` | admin | Clear the sandbox and seed the test catalog again (training mode only). |
| `GET` | `/training/status` | logged-in user | Report whether this API instance runs in training mode. |
| `POST` | `/tse/certificates` | logged-in user | Download the TSE certificates as a tar archive. |
| `POST` | `/tse/export/delete` | admin | Export TSE data and delete it from the device (admin-only, destructive). |
| `POST` | `/tse/export/full` | logged-in user | Download the full TSE export as a tar archive (placeholder on empty result). |
| `POST` | `/tse/export/partial` | logged-in user | Download a partial TSE export as a tar archive. |
| `POST` | `/tse/init` | admin | Commission a brand-new TSE, or keep the time of a running one set. |
| `POST` | `/tse/init/preflight` | admin | Report what `POST /tse/init` would do, without writing to the TSE (gap G10). |
| `POST` | `/tse/register-client` | admin | Map this API's client id on the TSE (idempotent, admin-only). |
| `GET` | `/tse/status` | logged-in user | Current device status from the TSE client (read-only). |
| `GET` | `/tse/transaction` | logged-in user | List TSE transactions with pagination, optionally for one receipt. |
| `POST` | `/tse/transaction` | logged-in user | Sign a transaction on the TSE and store it. |
| `POST` | `/tse/transaction/start` | logged-in user | Start the TSE transaction of a new basket (first article scanned). |
| `GET` | `/tse/transaction/verkauf/{rechnungs_nr}` | logged-in user | All TSE transactions signed for one receipt. |
| `GET` | `/tse/transaction/{transaction_id}` | logged-in user | Read one TSE transaction by id; 404 when it does not exist. |
| `POST` | `/tse/transaction/{transaction_id}/abbruch` | logged-in user | Abort a started transaction: the sale did not happen (`AVBelegabbruch`). |
| `POST` | `/tse/unblock` | admin | Repair a blocked Admin/TimeAdmin PIN with its PUK (recovery matrix). |
| `GET` | `/users/` | logged-in user | List users with role, active and name filters. |
| `POST` | `/users/` | admin | Create a user with a hashed password (admin only); 400 if the name is taken. |
| `DELETE` | `/users/{user_id}` | admin | Delete an account. Self-deletion and removing the last admin are refused. |
| `GET` | `/users/{user_id}` | logged-in user | Read one user by id; 404 if unknown. |
| `PATCH` | `/users/{user_id}` | admin | Update user fields, hashing a new password if one is given (admin only). |
| `POST` | `/users/{user_id}/deactivate` | admin | Deactivate a user account (admin only). |
| `POST` | `/users/{user_id}/reset-password` | admin | Set a new password for a user without the old one (admin only). |
| `GET` | `/verkauf/` | logged-in user | List receipts, optionally filtered by date range or storno flag. |
| `POST` | `/verkauf/` | logged-in user | Book a sale and return the stored receipt (requires a logged-in user). |
| `GET` | `/verkauf/{rechnungs_nr}` | logged-in user | Read one receipt by number; 404 when it does not exist. |
| `POST` | `/verkauf/{rechnungs_nr}/storno` | logged-in user | Storno a receipt that is not yet part of a completed Tagesabschluss. |
| `POST` | `/warenkorb/anzahlung` | logged-in user | Preview an Anzahlung (new deposit or resolving an open one). |
| `POST` | `/warenkorb/hinzufuegen` | logged-in user | Add an article to the cart. |
| `POST` | `/warenkorb/leergut` | logged-in user | Return the Pfand row of the given article with a negative price. |
| `POST` | `/warenkorb/rabatt` | logged-in user | Apply a discount and return the rows to display. |
| `POST` | `/warenkorb/summen` | logged-in user | Totals of the current cart rows (subtotal, VAT split, discounts, change). |
| `GET` | `/zaehlprotokoll/` | logged-in user | List count protocols, optionally filtered by Tagesabschluss id. |
| `POST` | `/zaehlprotokoll/` | logged-in user | Insert a count protocol for a Tagesabschluss and deactivate its predecessor. |
| `GET` | `/zaehlprotokoll/abrechnung/{abrechnung_tag_id}` | logged-in user | All count protocols of one Tagesabschluss, including inactive ones. |
| `GET` | `/zaehlprotokoll/{zp_id}` | logged-in user | Read one count protocol by id; 404 when it does not exist. |
| `PATCH` | `/zaehlprotokoll/{zp_id}` | logged-in user | Patch an existing count protocol with the supplied fields only. |

## main

### `GET /`

root

**Access:** public

**Responses**

| Status | Body |
|---|---|
| 200 | object |


## Abrechnung Jahr (yearly settlement)

### `GET /abrechnung/jahr/`

List yearly settlements with pagination, ascending or descending by id.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| desc | query | boolean | no | default False |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of AbrechnungJahrPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /abrechnung/jahr/`

Settle a year from its monthly settlements (logged-in only).

Without `jahr` the earliest unsettled year is chosen, falling back to the
current one. The receipt id range may be overridden by
`abrechnung_tag_id_von` / `_bis`. Fails with 400 when the year has no monthly
settlements. An existing settlement for the year and its VAT rows are deleted
and rebuilt.

**Access:** logged-in user

**Request body** (`application/json`)

| Field | Type | Required | Constraints |
|---|---|---|---|
| jahr | integer | no |  |
| abrechnung_tag_id_von | integer | no |  |
| abrechnung_tag_id_bis | integer | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | AbrechnungJahrPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /abrechnung/jahr/offen`

Years with monthly settlements that are not settled yet.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | array of integer |
| 404 | Not found |

### `GET /abrechnung/jahr/{jahr_id}`

Read one yearly settlement including its VAT rows; 404 when unknown.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| jahr_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |


## Abrechnung Monat (monthly settlement)

### `GET /abrechnung/monat/`

List monthly settlements with pagination, ascending or descending by id.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| desc | query | boolean | no | default False |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of AbrechnungMonatPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /abrechnung/monat/`

Settle a month from its daily settlements (logged-in only).

Without `monat` the earliest unsettled month is chosen, falling back to the
current one. The daily settlement id range may be overridden by
`abrechnung_tag_id_von` / `_bis`. Fails with 400 when the month has no daily
settlements. An existing settlement for the month and its VAT rows are
deleted and rebuilt.

**Access:** logged-in user

**Request body** (`application/json`)

| Field | Type | Required | Constraints |
|---|---|---|---|
| monat | string | no |  |
| abrechnung_tag_id_von | integer | no |  |
| abrechnung_tag_id_bis | integer | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | AbrechnungMonatPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /abrechnung/monat/offen`

Months (`YYYY-MM`) with daily settlements that are not settled yet.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | array of string |
| 404 | Not found |

### `GET /abrechnung/monat/{monat_id}`

Read one monthly settlement including its VAT rows; 404 when unknown.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| monat_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |


## Abrechnung Tag (daily settlement)

### `GET /abrechnung/tag/`

List daily settlements with pagination, ascending or descending by id.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| desc | query | boolean | no | default False |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of AbrechnungTagPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /abrechnung/tag/`

Close the open period and return the new Tagesabschluss (logged-in only).

The payload carries the counted drawer and comment; the whole settlement runs
in one transaction including the incremental TSE export, the invalidation of
the affected month/year, the count protocol and the DSFinV-K file write.

**Access:** logged-in user

**Request body** (`application/json`)

| Field | Type | Required | Constraints |
|---|---|---|---|
| z_kasse_id | string | no |  |
| zeitpunkt | string | no |  |
| zeitpunkt_real | string | no |  |
| kassenstand_id | integer | no |  |
| rechnungs_nr_von | integer | no |  |
| rechnungs_nr_bis | integer | no |  |
| last_tse_sig_counter | integer | no |  |
| zaehlprotokoll | object | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | AbrechnungTagPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /abrechnung/tag/offen`

Distinct sale dates (ISO) that are not covered by a settlement yet.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | array of string |
| 404 | Not found |

### `GET /abrechnung/tag/vorschau`

Preview the open Tagesabschluss without writing anything.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |

### `GET /abrechnung/tag/{tag_id}`

Read one daily settlement including its VAT rows; 404 when unknown.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| tag_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |


## anzahlung

### `GET /anzahlung/`

List installment rows, optionally filtered by the two receipt references.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| anzahlung_in_rech_nr | query | integer | no |  |
| aufloesung_in_rech_nr | query | integer | no |  |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of AnzahlungPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /anzahlung/`

Record a down payment for a receipt, optionally with its detail rows.

Both referenced sales (`anzahlung_in_rech_nr` and, if given,
`aufloesung_in_rech_nr`) must exist, otherwise the request fails with 400.
Detail rows default their `rechnungs_nr` to the installment receipt.

**Access:** logged-in user

**Request body** (`application/json`) - `AnzahlungCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| datum | string | no |  |
| anzahlung_in_rech_nr | integer | yes |  |
| aufloesung_in_rech_nr | integer | no |  |
| details | array of object | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | AnzahlungPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /anzahlung/aufgeloest`

Resolution rows, i.e. installments that were applied to a sale.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | array of AnzahlungPublic |
| 404 | Not found |

### `POST /anzahlung/details`

Append one installment detail row; sale and sale position must exist.

**Access:** logged-in user

**Request body** (`application/json`) - `AnzahlungDetailsCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| rechnungs_nr | integer | yes |  |
| vd_id | integer | yes |  |
| ges_preis | number | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | AnzahlungDetailsPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /anzahlung/offen`

Installments that are not yet resolved by a later sale.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | array of AnzahlungPublic |
| 404 | Not found |

### `GET /anzahlung/{anzahlung_id}`

Read one installment row by id; 404 when it does not exist.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| anzahlung_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | AnzahlungPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /anzahlung/{anzahlung_id}/aufloesen`

Resolve an open installment by appending the resolution row.

`aufloesung_in_rech_nr` (body or query) is required and must reference an
existing sale; 400 otherwise. The original row is left untouched.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| anzahlung_id | path | integer | yes |  |
| aufloesung_in_rech_nr | query | integer | no |  |
| datum | query | string | no |  |

**Request body** (`application/json`)

| Field | Type | Required | Constraints |
|---|---|---|---|
| datum | string | no |  |
| aufloesung_in_rech_nr | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | AnzahlungPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /anzahlung/{anzahlung_id}/details`

Detail rows booked for the installment receipt; 404 for unknown installments.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| anzahlung_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | array of AnzahlungDetailsPublic |
| 404 | Not found |
| 422 | HTTPValidationError |


## artikel

### `GET /artikel/`

List articles with filters and pagination.

`aktiv_only` (default) hides deactivated versions. Filters are applied in
this precedence: `search_string` (all space separated terms must match),
`barcode`, `artikel_nr` (plus `lieferant_id`), `lieferant_id`,
`produktgruppen_id`, `artikel_name`.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| aktiv_only | query | boolean | no | default True |
| search_string | query | string | no | default |
| barcode | query | string | no | default |
| artikel_nr | query | string | no | default |
| artikel_name | query | string | no | default |
| lieferant_id | query | integer | no | default 0 |
| produktgruppen_id | query | integer | no | default 0 |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of ArtikelPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /artikel/`

Create an article; 400 if supplier and artikel_nr already exist.

**Access:** logged-in user

**Request body** (`application/json`) - `ArtikelCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| artikel_nr | string | yes | max length 30 |
| artikel_name | string | yes | max length 180 |
| kurzname | string | no | max length 50 |
| menge | number | no | min 0.0 |
| einheit | string | no | max length 10 |
| barcode | string | no | max length 30 |
| herkunft | string | no | max length 100 |
| vpe | integer | no |  |
| setgroesse | integer | no | min 1.0, default 1 |
| vk_preis | number | no | min 0.0 |
| empf_vk_preis | number | no | min 0.0 |
| ek_rabatt | number | no | min 0.0, max 1.0 |
| ek_preis | number | no | min 0.0 |
| variabler_preis | boolean | no | default False |
| sortiment | boolean | no | default False |
| lieferbar | boolean | no | default False |
| beliebtheit | integer | no | default 0 |
| bestand | integer | no |  |
| bio | boolean | no |  |
| vegan | boolean | no |  |
| produktgruppen_id | integer | yes |  |
| lieferant_id | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | ArtikelPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `DELETE /artikel/{artikel_id}`

Deactivate an article instead of deleting the row.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| artikel_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /artikel/{artikel_id}`

Read one article incl. product group, supplier and Pfand details.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| artikel_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | ArtikelPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PATCH /artikel/{artikel_id}`

Update an article, creating a new version when needed.

Changes to `bestand`, `beliebtheit`, `lieferbar` and `sortiment` are applied
in place. Any other change deactivates the row and creates a new version
that shares the picture. Raises 400 for deactivated articles or no changes.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| artikel_id | path | integer | yes |  |

**Request body** (`application/json`) - `ArtikelUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| produktgruppen_id | integer | no |  |
| lieferant_id | integer | no |  |
| artikel_nr | string | no |  |
| artikel_name | string | no |  |
| kurzname | string | no |  |
| menge | number | no | min 0.0 |
| einheit | string | no |  |
| barcode | string | no |  |
| herkunft | string | no |  |
| vpe | integer | no |  |
| setgroesse | integer | no | min 1.0 |
| vk_preis | number | no | min 0.0 |
| empf_vk_preis | number | no | min 0.0 |
| ek_rabatt | number | no | min 0.0, max 1.0 |
| ek_preis | number | no | min 0.0 |
| variabler_preis | boolean | no |  |
| sortiment | boolean | no |  |
| lieferbar | boolean | no |  |
| beliebtheit | integer | no |  |
| bestand | integer | no |  |
| bio | boolean | no |  |
| vegan | boolean | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | ArtikelPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `DELETE /artikel/{artikel_id}/bild`

Delete the picture of an article; 404 if there is none.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| artikel_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /artikel/{artikel_id}/bild`

Serve the article picture; 404 if the article has none.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| artikel_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PUT /artikel/{artikel_id}/bild`

Replace the picture of an article (JPEG, PNG or WebP, max. 5 MB).

Raises 404 for an unknown article, 413 for oversized uploads and 415 for
other formats. The type comes from the content; the old file is removed.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| artikel_id | path | integer | yes |  |

**Request body** (`multipart/form-data`) - `Body_upload_artikel_bild_artikel__artikel_id__bild_put`

| Field | Type | Required | Constraints |
|---|---|---|---|
| bild | string | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |


## auth

### `GET /auth/anmeldungen`

List login records (admin only), newest first, optionally per user.

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| user_id | query | integer | no |  |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of AnmeldungPublic |
| 422 | HTTPValidationError |

### `POST /auth/login`

Verify credentials and return a bearer token for the user.

Records the login in `Anmeldung` and puts its id into the token. Raises 401
for unknown or inactive users and wrong passwords, 429 after too many
failures (5 per 60 s per host and username).

**Access:** public

**Request body** (`application/json`) - `LoginPayload`

| Field | Type | Required | Constraints |
|---|---|---|---|
| username | string | yes |  |
| password | string | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 422 | HTTPValidationError |

### `POST /auth/logout`

Record the logout time of the token's `Anmeldung`; always succeeds.

Accepts the token from the Authorization header or the `token` query
parameter. A missing or invalid token is not an error.

**Access:** public

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| token | query | string | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 422 | HTTPValidationError |

### `GET /auth/me`

Return the authenticated user.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |

### `PATCH /auth/me`

Self-service preferences (currently the preferred theme).

**Access:** logged-in user

**Request body** (`application/json`) - `ThemePayload`

| Field | Type | Required | Constraints |
|---|---|---|---|
| pref_theme | string | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | UserPublic |
| 422 | HTTPValidationError |

### `POST /auth/passwort`

Change the own password; the current one must match.

**Access:** logged-in user

**Request body** (`application/json`) - `PasswordChangePayload`

| Field | Type | Required | Constraints |
|---|---|---|---|
| current_password | string | yes |  |
| new_password | string | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 422 | HTTPValidationError |

### `POST /auth/refresh`

Issue a new token for the current user, keeping the `anmeldung_id` claim.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |


## bestellung

### `GET /bestellung/`

List orders, optionally filtered by typ and order date range.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| typ | query | one of `LM`, `KHW`, `IVT` | no |  |
| von | query | string | no |  |
| bis | query | string | no |  |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of BestellungPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /bestellung/`

Create an order with optional positions and return it.

Missing `typ`, `bestell_datum`, `jahr` and `kw` default to LM, now, the
current year and KW 1. Positions must have unique `position` values and
existing articles (400 otherwise).

**Access:** logged-in user

**Request body** (`application/json`) - `BestellungCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| typ | one of `LM`, `KHW`, `IVT` | no |  |
| bestell_datum | string | no |  |
| jahr | integer | no |  |
| kw | integer | no |  |
| details | array of object | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | BestellungPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `DELETE /bestellung/{bestell_nr}`

Delete an order and its positions; 404 when it does not exist.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| bestell_nr | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /bestellung/{bestell_nr}`

Read one order including its positions; 404 when it does not exist.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| bestell_nr | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PATCH /bestellung/{bestell_nr}`

Patch an order and, when details are sent, replace its positions.

Details are validated like on creation; replacing them deletes the rows of the
old typ first. A typ change without details re-keys the existing child rows.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| bestell_nr | path | integer | yes |  |

**Request body** (`application/json`) - `BestellungUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| typ | one of `LM`, `KHW`, `IVT` | no |  |
| bestell_datum | string | no |  |
| jahr | integer | no |  |
| kw | integer | no |  |
| details | array of object | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | BestellungPublic |
| 404 | Not found |
| 422 | HTTPValidationError |


## gutschein

### `GET /gutschein/`

List voucher rows with pagination, optionally filtered by voucher number.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| gutschein_nr | query | integer | no |  |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of GutscheinPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /gutschein/`

Issue a voucher: allocate the next voucher number and append the start row.

The number is drawn under `VOUCHER_LOCK` so parallel issuances cannot collide.
Referenced sale positions (`gutschein_in_vd_id`, `einloesung_in_vd_id`) must
exist, otherwise the request fails with 400.

**Access:** logged-in user

**Request body** (`application/json`) - `GutscheinCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| datum | string | no |  |
| gutschein_in_vd_id | integer | no |  |
| einloesung_in_vd_id | integer | no |  |
| restbetrag | number | yes | min 0.0 |

**Responses**

| Status | Body |
|---|---|
| 200 | GutscheinPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /gutschein/ausstehend`

Vouchers that still carry a balance, with their original start value.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | array of GutscheinPublic |
| 404 | Not found |

### `GET /gutschein/eingeloest`

Vouchers whose remaining balance is zero (fully redeemed).

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | array of GutscheinPublic |
| 404 | Not found |

### `GET /gutschein/{gutschein_id}`

Read one voucher row by id; 404 when it does not exist.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| gutschein_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | GutscheinPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /gutschein/{gutschein_id}/einloesen`

Redeem (part of) a voucher and return the new balance row.

The amount comes from the linked sale position `einloesung_in_vd_id`, the
explicit `betrag` or the requested new `restbetrag`, which may be sent either
in the body or as query parameters. `redeem_voucher` rejects non-positive
amounts, amounts above the balance and a sale position used twice.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| gutschein_id | path | integer | yes |  |
| einloesung_in_vd_id | query | integer | no |  |
| restbetrag | query | number | no |  |
| betrag | query | number | no |  |
| gutschein_in_vd_id | query | integer | no |  |

**Request body** (`application/json`)

| Field | Type | Required | Constraints |
|---|---|---|---|
| datum | string | no |  |
| gutschein_in_vd_id | integer | no |  |
| einloesung_in_vd_id | integer | no |  |
| restbetrag | number | no |  |
| betrag | number | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | GutscheinPublic |
| 404 | Not found |
| 422 | HTTPValidationError |


## Import / export (CSV, DSFinV-K)

### `GET /export/abrechnung`

Download the settlements as a CSV file.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |

### `GET /export/artikel`

Download all articles as a CSV file.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |

### `GET /export/bestellung`

Download the orders as a CSV file.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |

### `GET /export/dsfinvk/{abrechnung_tag_id}`

DSFinV-K export of one Tagesabschluss as a ZIP archive.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| abrechnung_tag_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 422 | HTTPValidationError |

### `GET /export/inventur`

Download the stock-taking (Inventur) list as a CSV file.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |

### `POST /import/artikel`

Import articles from an uploaded CSV and report how many were created.

**Access:** logged-in user

**Request body** (`multipart/form-data`) - `Body_import_artikel_import_artikel_post`

| Field | Type | Required | Constraints |
|---|---|---|---|
| file | string | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 422 | HTTPValidationError |

### `POST /import/bestellung`

Import orders from an uploaded CSV and report how many were created.

**Access:** logged-in user

**Request body** (`multipart/form-data`) - `Body_import_bestellung_import_bestellung_post`

| Field | Type | Required | Constraints |
|---|---|---|---|
| file | string | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 422 | HTTPValidationError |


## kassenstand

### `GET /kassenstand/`

List cash drawer bookings, newest first.

By default only manual bookings are returned; `rechnungen=true` also includes
the automatic entries written by sales and stornos.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| rechnungen | query | boolean | no | default False |
| von | query | string | no |  |
| bis | query | string | no |  |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of KassenstandPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /kassenstand/`

Append a manual cash drawer booking and return it.

Validates the new balance against the current one (Entnahme must not
increase it, a withdrawal must not exceed the cash in the drawer) and inserts
the row under `KASSENSTAND_LOCK`. A referenced `rechnungs_nr` must exist, and
the booking user is taken from the body or the bearer token.

**Access:** logged-in user

**Request body** (`application/json`) - `KassenstandCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| buchungsdatum | string | no |  |
| neuer_kassenstand | number | yes | min 0.0 |
| manuell | boolean | no | default False |
| entnahme | boolean | no | default False |
| rechnungs_nr | integer | no |  |
| kommentar | string | no | max length 70 |

**Responses**

| Status | Body |
|---|---|
| 200 | KassenstandPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /kassenstand/aktuell`

The current (latest) cash balance, or null while no booking exists.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |

### `POST /kassenstand/zuruecksetzen/vorschau`

Suggestion for bringing the counted drawer back to its target stock.

Read-only: takes the count in the same shape as the `zaehlprotokoll` detail
rows of `POST /abrechnung/tag`. The reset itself is the manual
`POST /kassenstand/` entry, exactly like the Java dialogue's
`insertIntoKassenstand`.

**Access:** logged-in user

**Request body** (`application/json`) - `array of ZaehlprotokollDetailsCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| (free form) | array of object |  |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /kassenstand/{kassenstand_id}`

Read one ledger entry by id; 404 when it does not exist.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| kassenstand_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | KassenstandPublic |
| 404 | Not found |
| 422 | HTTPValidationError |


## lieferant

### `GET /lieferant/`

List suppliers with filters and pagination.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| aktiv_only | query | boolean | no | default True |
| search_string | query | string | no | default |
| lieferant_name | query | string | no | default |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of Lieferant |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /lieferant/`

Create a supplier; 400 if the name already exists.

**Access:** logged-in user

**Request body** (`application/json`) - `LieferantBase`

| Field | Type | Required | Constraints |
|---|---|---|---|
| lieferant_name | string | yes | max length 50 |
| lieferant_kurzname | string | yes | max length 10 |

**Responses**

| Status | Body |
|---|---|
| 200 | LieferantPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `DELETE /lieferant/{lieferant_id}`

Deactivate a supplier instead of deleting it.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| lieferant_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /lieferant/{lieferant_id}`

Read one supplier by id; 404 if unknown.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| lieferant_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | Lieferant |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PATCH /lieferant/{lieferant_id}`

Update a supplier by deactivating it and creating a new version.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| lieferant_id | path | integer | yes |  |

**Request body** (`application/json`) - `LieferantUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| lieferant_name | string | no |  |
| lieferant_kurzname | string | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | LieferantPublic |
| 404 | Not found |
| 422 | HTTPValidationError |


## mwst

### `GET /mwst/`

List VAT rates with search and pagination.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| search_string | query | string | no | default |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of Mwst |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /mwst/`

Create a VAT rate (admin only); 400 if the rate already exists.

**Access:** admin

**Request body** (`application/json`) - `MwstCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| mwst_satz | number | yes | min 0.0, max 1.0 |
| dsfinvk_ust_schluessel | integer | yes | min 0.0 |
| dsfinvk_ust_beschr | string | no | max length 55 |

**Responses**

| Status | Body |
|---|---|
| 200 | MwstPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `DELETE /mwst/{mwst_id}`

Delete a VAT rate (admin only).

Raises 409 if product groups still use the rate and 503 if the database
user lacks DELETE permission.

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| mwst_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /mwst/{mwst_id}`

Read one VAT rate by id; 404 if unknown.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| mwst_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | Mwst |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PATCH /mwst/{mwst_id}`

Update a VAT rate (admin only); 400 if the new rate already exists.

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| mwst_id | path | integer | yes |  |

**Request body** (`application/json`) - `MwstUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| mwst_satz | number | no | min 0.0, max 1.0 |
| dsfinvk_ust_schluessel | integer | no | min 0.0 |
| dsfinvk_ust_beschr | string | no | max length 55 |

**Responses**

| Status | Body |
|---|---|
| 200 | MwstPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PUT /mwst/{mwst_id}`

Replace a VAT rate (admin only); same behaviour as PATCH.

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| mwst_id | path | integer | yes |  |

**Request body** (`application/json`) - `MwstUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| mwst_satz | number | no | min 0.0, max 1.0 |
| dsfinvk_ust_schluessel | integer | no | min 0.0 |
| dsfinvk_ust_beschr | string | no | max length 55 |

**Responses**

| Status | Body |
|---|---|
| 200 | MwstPublic |
| 404 | Not found |
| 422 | HTTPValidationError |


## pfand

### `GET /pfand/`

List Pfand entries, optionally filtered by deposit value.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| wert | query | number | no |  |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of PfandPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /pfand/`

Create a Pfand for an article (admin only).

Raises 400 if the article does not exist or already has a Pfand.

**Access:** admin

**Request body** (`application/json`) - `PfandCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| artikel_id | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | PfandPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `DELETE /pfand/{pfand_id}`

Delete a Pfand (admin only).

Raises 409 if a product group still uses it and 503 if the database user
lacks DELETE permission.

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| pfand_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /pfand/{pfand_id}`

Read one Pfand including its value; 404 if unknown.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| pfand_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | PfandPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PATCH /pfand/{pfand_id}`

Update a Pfand (admin only).

Raises 400 if a new `artikel_id` does not exist or already has a Pfand.

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| pfand_id | path | integer | yes |  |

**Request body** (`application/json`) - `PfandUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| artikel_id | integer | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | PfandPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PUT /pfand/{pfand_id}`

Replace a Pfand (admin only); same behaviour as PATCH.

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| pfand_id | path | integer | yes |  |

**Request body** (`application/json`) - `PfandUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| artikel_id | integer | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | PfandPublic |
| 404 | Not found |
| 422 | HTTPValidationError |


## produktgruppe

### `GET /produktgruppe/`

List product groups with filters and pagination.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| aktiv_only | query | boolean | no | default True |
| search_string | query | string | no | default |
| toplevel_id | query | integer | no | default 0 |
| sub_id | query | integer | no | default 0 |
| subsub_id | query | integer | no | default 0 |
| produktgruppen_name | query | string | no | default |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of Produktgruppe |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /produktgruppe/`

Create a product group; 400 if the name already exists.

**Access:** logged-in user

**Request body** (`application/json`) - `ProduktgruppeCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| toplevel_id | integer | no | default 1 |
| sub_id | integer | no |  |
| subsub_id | integer | no |  |
| produktgruppen_name | string | yes | max length 50 |
| std_einheit | string | yes | max length 10 |
| mwst_id | integer | yes |  |
| pfand_id | integer | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | ProduktgruppePublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `DELETE /produktgruppe/{produktgruppen_id}`

Deactivate a product group instead of deleting it.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| produktgruppen_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /produktgruppe/{produktgruppen_id}`

Read one product group by id; 404 if unknown.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| produktgruppen_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | Produktgruppe |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PATCH /produktgruppe/{produktgruppen_id}`

Update a product group by deactivating it and creating a new version.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| produktgruppen_id | path | integer | yes |  |

**Request body** (`application/json`) - `ProduktgruppeUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| mwst_id | integer | no |  |
| pfand_id | integer | no |  |
| toplevel_id | integer | no |  |
| sub_id | integer | no |  |
| subsub_id | integer | no |  |
| produktgruppen_name | string | no |  |
| std_einheit | string | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | ProduktgruppePublic |
| 404 | Not found |
| 422 | HTTPValidationError |


## rabattaktion

### `GET /rabattaktion/`

List discount campaigns with date, article and group filters.

Open-ended campaigns (`bis IS NULL`) match every `von` filter. `current_only`
returns only campaigns running now. `exclude_deleted` hides rows where
`bis == von`, the state used to mark a campaign deleted.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| von | query | string | no |  |
| bis | query | string | no |  |
| artikel_id | query | integer | no |  |
| produktgruppen_id | query | integer | no |  |
| search_string | query | string | no | default |
| current_only | query | boolean | no | default False |
| exclude_deleted | query | boolean | no | default True |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of RabattaktionPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /rabattaktion/`

Create a discount campaign and validate its discount rules.

**Access:** logged-in user

**Request body** (`application/json`) - `RabattaktionCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| aktionsname | string | no | max length 50 |
| rabatt_relativ | number | no | min 0.0, max 1.0 |
| rabatt_absolut | number | no | min 0.0 |
| mengenrabatt_schwelle | integer | no | min 1.0 |
| mengenrabatt_anzahl_kostenlos | integer | no | min 1.0 |
| mengenrabatt_relativ | number | no | min 0.0, max 1.0 |
| von | string | yes |  |
| bis | string | no |  |
| produktgruppen_id | integer | no |  |
| artikel_id | integer | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | RabattaktionPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `DELETE /rabattaktion/{rabattaktion_id}`

End a campaign by moving its `bis` date instead of deleting the row.

A running campaign gets `bis = now`, a future one gets `bis = von`. Raises
400 if the campaign already ended.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| rabattaktion_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /rabattaktion/{rabattaktion_id}`

Read one discount campaign; 404 if unknown.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| rabattaktion_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | RabattaktionPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PATCH /rabattaktion/{rabattaktion_id}`

Update a campaign; started campaigns allow only name and `bis`.

The merged state is validated, not just the supplied fields. Raises 400 for
ended campaigns or fields that are locked after the start.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| rabattaktion_id | path | integer | yes |  |

**Request body** (`application/json`) - `RabattaktionUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| produktgruppen_id | integer | no |  |
| artikel_id | integer | no |  |
| aktionsname | string | no |  |
| rabatt_relativ | number | no | min 0.0, max 1.0 |
| rabatt_absolut | number | no | min 0.0 |
| mengenrabatt_schwelle | integer | no | min 1.0 |
| mengenrabatt_anzahl_kostenlos | integer | no | min 1.0 |
| mengenrabatt_relativ | number | no | min 0.0, max 1.0 |
| von | string | no |  |
| bis | string | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | RabattaktionPublic |
| 404 | Not found |
| 422 | HTTPValidationError |


## training

### `POST /training/reset`

Clear the sandbox and seed the test catalog again (training mode only).

**Access:** admin

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |

### `GET /training/status`

Report whether this API instance runs in training mode.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |


## TSE (technical security device)

### `POST /tse/certificates`

Download the TSE certificates as a tar archive.

Falls back to a placeholder archive when the device returns nothing, so the
client always receives a file.

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |

### `POST /tse/export/delete`

Export TSE data and delete it from the device (admin-only, destructive).

**Access:** admin

**Request body** (`application/json`)

| Field | Type | Required | Constraints |
|---|---|---|---|
| last_excluded_signature_counter | integer | no |  |
| max_records | integer | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /tse/export/full`

Download the full TSE export as a tar archive (placeholder on empty result).

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |

### `POST /tse/export/partial`

Download a partial TSE export as a tar archive.

The selection is by `criterion` (tx number, date or signature counter) with
the matching start/end values, an optional
`last_excluded_signature_counter` and `max_records` limit.

**Access:** logged-in user

**Request body** (`application/json`)

| Field | Type | Required | Constraints |
|---|---|---|---|
| criterion | string | no | default sig_counter |
| start_tx_number | integer | no |  |
| end_tx_number | integer | no |  |
| start_date | string | no |  |
| end_date | string | no |  |
| last_excluded_signature_counter | integer | no |  |
| max_records | integer | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /tse/init`

Commission a brand-new TSE, or keep the time of a running one set.

With a body: sets both PINs and both PUKs while the TSE is still in transport
state, initializes it, sets its time and registers this client id
(`se_initializePuk` + `se_unblockUser`, `se_initialize`, `se_updateTime`,
`se_registerClient`; v3.1 replaces the deprecated `se_initializePinValues`).
Without a body: opens the device and keeps its time set; `force=true` skips
the sync-interval shortcut (used by the GUI's "set time now" button).

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| force | query | boolean | no | default False |

**Request body** (`application/json`)

| Field | Type | Required | Constraints |
|---|---|---|---|
| admin_pin | string | yes |  |
| admin_puk | string | yes |  |
| time_admin_pin | string | yes |  |
| time_admin_puk | string | yes |  |
| confirm_stored_puks | boolean | no | default False |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /tse/init/preflight`

Report what `POST /tse/init` would do, without writing to the TSE (gap G10).

With a body the four values are validated exactly as init validates them,
so a green preflight means init would pass the same checks.

**Access:** admin

**Request body** (`application/json`)

| Field | Type | Required | Constraints |
|---|---|---|---|
| admin_pin | string | yes |  |
| admin_puk | string | yes |  |
| time_admin_pin | string | yes |  |
| time_admin_puk | string | yes |  |
| confirm_stored_puks | boolean | no | default False |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /tse/register-client`

Map this API's client id on the TSE (idempotent, admin-only).

`ErrorERSalreadyMapped` is reported as `already_registered`, not as an error
(TSE_FAILURE_PATHWAYS.md W3).

**Access:** admin

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |

### `GET /tse/status`

Current device status from the TSE client (read-only).

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |

### `GET /tse/transaction`

List TSE transactions with pagination, optionally for one receipt.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| rechnungs_nr | query | integer | no |  |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of TSETransactionPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /tse/transaction`

Sign a transaction on the TSE and store it.

Values missing from the payload are taken from the signing client (numbers,
timestamps, signature counter, signature and error). A referenced
`rechnungs_nr` must exist, otherwise the request fails with 400.

**Access:** logged-in user

**Request body** (`application/json`) - `TSETransactionCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| transaction_number | integer | no |  |
| rechnungs_nr | integer | no |  |
| training | boolean | no | default False |
| transaction_start | string | no |  |
| transaction_end | string | no |  |
| process_type | string | no |  |
| signature_counter | integer | no |  |
| signature_base64 | string | no |  |
| tse_error | string | no |  |
| process_data | string | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | TSETransactionPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /tse/transaction/start`

Start the TSE transaction of a new basket (first article scanned).

**Access:** logged-in user

**Responses**

| Status | Body |
|---|---|
| 200 | TSETransactionPublic |
| 404 | Not found |

### `GET /tse/transaction/verkauf/{rechnungs_nr}`

All TSE transactions signed for one receipt.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| rechnungs_nr | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | array of TSETransactionPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /tse/transaction/{transaction_id}`

Read one TSE transaction by id; 404 when it does not exist.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| transaction_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | TSETransactionPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /tse/transaction/{transaction_id}/abbruch`

Abort a started transaction: the sale did not happen (`AVBelegabbruch`).

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| transaction_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | TSETransactionPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /tse/unblock`

Repair a blocked Admin/TimeAdmin PIN with its PUK (recovery matrix).

The PUK cannot be verified with a read call, so a wrong PUK may block it
permanently. TimeAdmin must keep `TSE_TIME_ADMIN_PIN` as its new PIN,
otherwise the next restart cannot set the time (gap G2).

**Access:** admin

**Request body** (`application/json`) - `TSEUnblockRequest`

| Field | Type | Required | Constraints |
|---|---|---|---|
| user | one of `Admin`, `TimeAdmin` | yes |  |
| puk | string | yes |  |
| new_pin | string | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |


## users

### `GET /users/`

List users with role, active and name filters.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| role | query | string | no | default |
| active | query | boolean | no |  |
| search_string | query | string | no | default |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of UserPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /users/`

Create a user with a hashed password (admin only); 400 if the name is taken.

**Access:** admin

**Request body** (`application/json`) - `UserCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| username | string | yes | max length 50 |
| password | string | yes | min length 1 |
| role | one of `admin`, `mitarbeiter` | no | default mitarbeiter |
| active | boolean | no | default True |
| full_name | string | no | max length 50 |
| pref_theme | one of `light`, `dark` | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | UserPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `DELETE /users/{user_id}`

Delete an account. Self-deletion and removing the last admin are refused.

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| user_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /users/{user_id}`

Read one user by id; 404 if unknown.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| user_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | UserPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PATCH /users/{user_id}`

Update user fields, hashing a new password if one is given (admin only).

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| user_id | path | integer | yes |  |

**Request body** (`application/json`) - `UserUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| username | string | no |  |
| role | one of `admin`, `mitarbeiter` | no |  |
| active | boolean | no |  |
| password | string | no |  |
| full_name | string | no | max length 50 |
| pref_theme | one of `light`, `dark` | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | UserPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /users/{user_id}/deactivate`

Deactivate a user account (admin only).

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| user_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | UserPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /users/{user_id}/reset-password`

Set a new password for a user without the old one (admin only).

**Access:** admin

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| user_id | path | integer | yes |  |
| new_password | query | string | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | UserPublic |
| 404 | Not found |
| 422 | HTTPValidationError |


## verkauf

### `GET /verkauf/`

List receipts, optionally filtered by date range or storno flag.

`include_details` adds the receipt positions and `include_mwst` the VAT rows.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| von | query | string | no |  |
| bis | query | string | no |  |
| only_storno | query | boolean | no | default False |
| include_details | query | boolean | no | default False |
| include_mwst | query | boolean | no | default False |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |
| desc | query | boolean | no | default False |

**Responses**

| Status | Body |
|---|---|
| 200 | array of object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /verkauf/`

Book a sale and return the stored receipt (requires a logged-in user).

`create_sale` expands Pfand/discount/voucher lines, writes positions, VAT,
voucher and Kassenstand rows in one transaction and signs the receipt on the
TSE. The response additionally carries `change` (cash change) and
`ec_warning` (card terminal warning); validation failures surface as domain
errors from `create_sale`.

**Access:** logged-in user

**Request body** (`application/json`) - `VerkaufCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| ec_zahlung | boolean | no | default False |
| kunde_gibt | number | no | min 0.0 |
| user_id | integer | no |  |
| storno_von | integer | no |  |
| rechnung_rabatt_relativ | number | no | min 0.0, < 1.0 |
| gutschein_einloesung_nr | integer | no |  |
| gutschein_einloesung_betrag | number | no | > 0.0 |
| anzahlung_betrag | number | no | > 0.0 |
| anzahlung_aufloesen_nr | integer | no |  |
| tse_transaction_id | integer | no |  |
| verkauf_details | array of object | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | VerkaufPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /verkauf/{rechnungs_nr}`

Read one receipt by number; 404 when it does not exist.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| rechnungs_nr | path | integer | yes |  |
| include_details | query | boolean | no | default True |
| include_mwst | query | boolean | no | default True |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /verkauf/{rechnungs_nr}/storno`

Storno a receipt that is not yet part of a completed Tagesabschluss.

The shop can only refund in cash, so `cash_refund` defaults to true (see
`business.storno_logic.storno_sale`).

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| rechnungs_nr | path | integer | yes |  |
| cash_refund | query | boolean | no | default True |

**Responses**

| Status | Body |
|---|---|
| 200 | object |
| 404 | Not found |
| 422 | HTTPValidationError |


## Warenkorb (stateless cart preview)

### `POST /warenkorb/anzahlung`

Preview an Anzahlung (new deposit or resolving an open one).

Returns the whole cart as it will be booked: the article rows (zeroed for a
new deposit), the ANZAHLUNG lines, or the re-added deposit positions and
the negative ANZAHLAUFLOES lines. Display-only; the sale is still created
with `anzahlung_betrag`/`anzahlung_aufloesen_nr`.

**Access:** logged-in user

**Request body** (`application/json`) - `WarenkorbAnzahlung`

| Field | Type | Required | Constraints |
|---|---|---|---|
| positionen | array of object | yes |  |
| betrag | number | no | > 0.0 |
| aufloesen_nr | integer | no |  |
| rechnung_rabatt_relativ | number | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | array of WarenkorbPosition |
| 422 | HTTPValidationError |

### `POST /warenkorb/hinzufuegen`

Add an article to the cart.

Returns the article row plus the rows it requires: its product-group Pfand
and any active Rabattaktion. A variable-price article keeps `preis` (the
line total); without it the line is 0 until a price is entered.

**Access:** logged-in user

**Request body** (`application/json`) - `WarenkorbHinzufuegen`

| Field | Type | Required | Constraints |
|---|---|---|---|
| artikel_id | integer | yes |  |
| stueckzahl | integer | no | > 0.0, default 1 |
| preis | number | no | min 0.0 |
| ref | string | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | array of WarenkorbPosition |
| 422 | HTTPValidationError |

### `POST /warenkorb/leergut`

Return the Pfand row of the given article with a negative price.

Used when a customer returns empty bottles: the article itself is not put
into the cart, only its deposit.

**Access:** logged-in user

**Request body** (`application/json`) - `WarenkorbLeergut`

| Field | Type | Required | Constraints |
|---|---|---|---|
| artikel_id | integer | yes |  |
| stueckzahl | integer | no | > 0.0, default 1 |
| ref | string | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | array of WarenkorbPosition |
| 422 | HTTPValidationError |

### `POST /warenkorb/rabatt`

Apply a discount and return the rows to display.

Per article: returns the echoed article row (with `rabatt_absolut` for the
sale payload) followed by its negative Rabatt rows. With `rechnung=true`
the discount applies to the whole receipt and returns one negative row per
VAT rate, skipping articles that already carry a discount.

**Access:** logged-in user

**Request body** (`application/json`) - `WarenkorbRabatt`

| Field | Type | Required | Constraints |
|---|---|---|---|
| positionen | array of object | yes |  |
| rabatt | object | yes |  |
| rechnung | boolean | no | default False |

**Responses**

| Status | Body |
|---|---|
| 200 | array of WarenkorbPosition |
| 422 | HTTPValidationError |

### `POST /warenkorb/summen`

Totals of the current cart rows (subtotal, VAT split, discounts, change).

**Access:** logged-in user

**Request body** (`application/json`) - `WarenkorbSummenAnfrage`

| Field | Type | Required | Constraints |
|---|---|---|---|
| positionen | array of object | yes |  |
| kunde_gibt | number | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | WarenkorbSummen |
| 422 | HTTPValidationError |


## zaehlprotokoll

### `GET /zaehlprotokoll/`

List count protocols, optionally filtered by Tagesabschluss id.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| abrechnung_tag_id | query | integer | no |  |
| offset | query | integer | no | default 0 |
| limit | query | integer | no | max 100, default 100 |

**Responses**

| Status | Body |
|---|---|
| 200 | array of ZaehlprotokollPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `POST /zaehlprotokoll/`

Insert a count protocol for a Tagesabschluss and deactivate its predecessor.

`abrechnung_tag_id` is required and must reference an existing settlement
(400 otherwise). The counting user comes from the bearer token.

**Access:** logged-in user

**Request body** (`application/json`) - `ZaehlprotokollCreate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| abrechnung_tag_id | integer | no |  |
| zeitpunkt | string | no |  |
| kommentar | string | yes |  |
| aktiv | boolean | no | default True |
| details | array of object | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | ZaehlprotokollPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /zaehlprotokoll/abrechnung/{abrechnung_tag_id}`

All count protocols of one Tagesabschluss, including inactive ones.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| abrechnung_tag_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | array of ZaehlprotokollPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `GET /zaehlprotokoll/{zp_id}`

Read one count protocol by id; 404 when it does not exist.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| zp_id | path | integer | yes |  |

**Responses**

| Status | Body |
|---|---|
| 200 | ZaehlprotokollPublic |
| 404 | Not found |
| 422 | HTTPValidationError |

### `PATCH /zaehlprotokoll/{zp_id}`

Patch an existing count protocol with the supplied fields only.

**Access:** logged-in user

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| zp_id | path | integer | yes |  |

**Request body** (`application/json`) - `ZaehlprotokollUpdate`

| Field | Type | Required | Constraints |
|---|---|---|---|
| zeitpunkt | string | no |  |
| kommentar | string | no |  |
| aktiv | boolean | no |  |

**Responses**

| Status | Body |
|---|---|
| 200 | ZaehlprotokollPublic |
| 404 | Not found |
| 422 | HTTPValidationError |
