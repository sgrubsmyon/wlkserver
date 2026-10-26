# Weltladenkasse API - Detailed TODO List

> **Sync note**: This document and `concepts/IMPLEMENTATION_PLAN.md` must be kept in sync. When implementation progress changes, update both files so new sessions without prior memory see a consistent status.

> **Last Updated**: 2026-10-27  
> **Status**: Phases 1-5 implemented at router level (TSE export adapter untested without hardware); main Phase 6/7 flows wired (see "Business Logic Wiring Gaps" for what remains); auth enforced on transaction endpoints; parity audit of the remaining low-priority endpoints done and resolved (see "Parity Audit"), Bestellung positions + date filter implemented; bar_brutto aggregation matches Java; sale workflow (validation, automatic discounts, all four modes), storno (payment-mode parity, cash payout, settlement lock, rollback, attribution), cash register (payment, balance validation, end-of-day preview) complete; voucher redemption uses the Java balance calculation; search/filter/pagination/sorting finished for all list endpoints; Bestellung CSV import supports positions; Bestellung/Inventur CSV export added (ODS deferred); CORS configured; core `/training` endpoints; integration tests incl. concurrency; same-origin nginx deployment and script automation documented as planned; VAT module Java-parity checked, 100% tested, rounding method configurable; test coverage 90%

---

## 📋 Legend
- `[x]` = Already implemented and working
- `[✅]` = Completed and tested
- `[⏳]` = In progress
- `[ ]` = Not yet started / Missing
- `🔴` = High Priority
- `🟡` = Medium Priority
- `🟢` = Low Priority

---

## 🏗️ Core Infrastructure & Existing Functionality

### Database Models (python/models.py)
[x] Lieferant models (Base, Table, Public, Update)
[x] MwSt models (Base, Table, Public, Create, Update)
[x] Pfand models (Table, Public, Create, Update)
[x] Produktgruppe models (Base, Table, Public, Create, Update)
[x] Artikel models (Base, Table, Public, Create, Update)
[x] Rabattaktion models (Base, Table, Public, Create, Update)
[x] Verkauf models (Base, Table, Public, Create)
[x] VerkaufMwst models (Base, Table, Public, Create)
[x] VerkaufDetails models (Base, Table, Public, Create)
[x] Kassenstand models (Table, Public, Create)
[x] Gutschein models (Table, Public, Create, Einloesen)
[x] Anzahlung models (Table, Public, Create, Details)
[x] AbrechnungTag models (Table, Public, Create, Mwst, Tse)
[x] AbrechnungMonat models (Table, Public, Create, Mwst)
[x] AbrechnungJahr models (Table, Public, Create, Mwst)
[x] Zaehlprotokoll models (Table, Public, Create, Update, Details)
[x] Bestellung models (Table, Public, Create, Update, Details)
[x] TSETransaction models (Table, Public, Create)
[x] Training table models added (Table-only) for all training_* tables (step 6)
[x] User model (Table, Public, Create, Update) - Phase 7.4
[x] Anmeldung model (Table) - Phase 7.4 (login auditing)
[x] `user_id` FK column added to gutschein, zaehlprotokoll, bestellung, tse_transaction models (step 4)
[x] SQL migration script created in `migrations/02_user_auth/` (user_auth.sql + migrate_user_auth.py + migrate.sh) (step 4)
[x] Auth utils switched to bcrypt + PyJWT (step 4)
[x] Auth router logout/me now read token from Authorization header (step 4)
[x] Per-user auth enforcement on transaction endpoints (require_user enforced) - done

### Existing Router Functionality
[x] Artikel router - Full CRUD with advanced versioning logic
[x] Lieferant router - Full CRUD with deactivation pattern
[x] Produktgruppe router - Full CRUD with deactivation pattern
[x] MwSt router - Admin-only CRUD (POST/PUT/PATCH/DELETE) + read
[x] Pfand router - Admin-only CRUD (POST/PUT/PATCH/DELETE) + read
[x] Rabattaktion router - Full CRUD with date validation and update restrictions
[x] Verkauf router - Create, Read, Storno functionality
[x] Kassenstand router - CR + /aktuell + rechnungen filter
[x] Gutschein router - CR + redemption + ausstehend/eingeloest
[x] Anzahlung router - CR + aufloesen + offen/aufgeloest + details
[x] AbrechnungTag router - CR + /offen (basic Tagesabschluss aggregation)
[x] AbrechnungMonat router - CRD (delete-and-recreate) + /offen
[x] AbrechnungJahr router - CRD (delete-and-recreate) + /offen
[x] Zaehlprotokoll router - CRU + /abrechnung/{id}
[x] Bestellung router - CRUD incl. positions (`details` on create/update, returned by GET single)
[x] TSE router - transaction CRUD + status/init + export endpoints (stub adapter)
[x] Main API setup with all routers included
[x] Database session management
[x] Test infrastructure (conftest.py, smoke tests Phase 2-5)

---

## 🔴 HIGH PRIORITY - Complete Existing CRUD Operations

### Phase 1: Missing CRUD for Existing Models

[x] **MwSt Admin-Only CRUD Completion** - `python/routers/mwst.py`
- [x] POST /mwst - Create new VAT rate with validation - **ADMIN ONLY**
- [x] PUT /mwst/{mwst_id} - Update VAT rate - **ADMIN ONLY**
- [x] PATCH /mwst/{mwst_id} - Update VAT rate - **ADMIN ONLY**
- [x] DELETE /mwst/{mwst_id} - Delete VAT rate (with constraints check) - **ADMIN ONLY**
- [x] Add authentication/authorization dependency (stopgap: shared ADMIN_TOKEN)
- [x] `MwstBase.mwst_satz` has `ge=0, le=1` constraint (models.py line 48) - done

[x] **Pfand Admin-Only CRUD Completion** - `python/routers/pfand.py`
- [x] POST /pfand - Create new deposit item - **ADMIN ONLY**
- [x] PUT /pfand/{pfand_id} - Update deposit item - **ADMIN ONLY**
- [x] PATCH /pfand/{pfand_id} - Update deposit item - **ADMIN ONLY**
- [x] DELETE /pfand/{pfand_id} - Delete deposit item (with constraints check) - **ADMIN ONLY**
- [x] Add authentication/authorization dependency (stopgap: shared ADMIN_TOKEN)

**Verkauf: No Update Functionality (By Design)** - `python/routers/verkauf.py`
- [x] No update endpoint for verkauf (bookkeeping integrity)
- [x] Create/Read/Storno complete; Storno logic enhanced later (Phase 6)

**Dedicated Related Table Endpoints (Not Planned)**
- [x] No separate endpoints for verkauf_mwst / verkauf_details

---

## 🔴 HIGH PRIORITY - Core Business Tables

### Phase 2: Missing Core Tables

[x] **Kassenstand** - models + router + smoke tests
- [x] GET /kassenstand (rechnungen filter)
- [x] GET /kassenstand/{id}
- [x] POST /kassenstand
- [x] GET /kassenstand/aktuell
(no /kassenstand/letzte endpoint needed; /kassenstand/aktuell covers it)
- [x] `update_kassenstand_for_sale` wired into sale creation + storno (cash only) - Phase 6 (step 1)
- [x] Advanced business logic (balance validation) - `validate_balance_change` rejects Entnahmen that increase the balance or exceed it; wired into POST /kassenstand
- [x] Non-negative validation on `neuer_kassenstand` enforced via `ge=0` model constraint (models.py line 472)

[x] **Gutschein** - models + router + smoke tests
- [x] GET /gutschein
- [x] GET /gutschein/{id}
- [x] POST /gutschein
- [x] POST /gutschein/{id}/einloesen
- [x] GET /gutschein/ausstehend
- [x] GET /gutschein/eingeloest
- [x] /gutschein/ausstehend now returns restbetrag_anfang (initial amount) for partial-redemption detection - done
- [x] GET /gutschein/verkauf/{rechnungs_nr} - not needed for Java parity (see Parity Audit)
- [x] Advanced redemption calculation - `python/business/voucher_logic.py` mirrors Java `GutscheinEinloesenDialog.queryForGutschein` + `Kassieren.maybeInsertEinloesungIntoGutschein`: balance = `MIN(restbetrag)` over all rows of the `gutschein_nr` (append-only family, not the passed row), start value = `MAX(restbetrag)`; amount is derived from the linked sale position (`abs(ges_preis)`), an explicit `betrag` or the requested new `restbetrag`; must be positive and may not exceed the balance; a sale position can redeem only once; `gutschein_in_vd_id` is copied from the creation row; the redeemed row is attributed to the user. `restbetrag_anfang` in `/ausstehend` now uses `MAX(restbetrag)` (Java semantics). Redemptions are serialized with a process lock + `SELECT ... FOR UPDATE`

[x] **Anzahlung** - models + router + smoke tests
- [x] GET /anzahlung
- [x] GET /anzahlung/{id}
- [x] POST /anzahlung
- [x] POST /anzahlung/{id}/aufloesen
- [x] GET /anzahlung/offen
- [x] GET /anzahlung/aufgeloest
- [x] POST /anzahlung/details

---

## 🟡 MEDIUM PRIORITY - Accounting System

### Phase 3: Settlement Tables

[x] **Abrechnung Tag** - models + router + smoke tests
- [x] GET /abrechnung/tag
- [x] GET /abrechnung/tag/{id}
- [x] POST /abrechnung/tag (Tagesabschluss: period since the last settlement, VAT/`bar_brutto` aggregation, storno/retouren reporting, links the current Kassenstand entry)
- [x] GET /abrechnung/tag/offen
- [x] GET /abrechnung/tag/vorschau (read-only preview of the open Tagesabschluss)
- [x] Automatic incremental TSE export (best-effort) wired into POST /abrechnung/tag - step 3
- [x] Stornos/retouren handled in mwst + bar aggregation; entnahmen subtracted from closing balance (step 5)
- [x] Full Java aggregation parity (storno/retouren reporting in abrechnung response) - items 5-8
- [x] kassenstand entry validation during Tagesabschluss (provided `kassenstand_id` must exist)

[x] **Abrechnung Monat** - models + router + smoke tests
- [x] GET /abrechnung/monat
- [x] GET /abrechnung/monat/{id}
- [x] POST /abrechnung/monat (delete-and-recreate)
- [x] GET /abrechnung/monat/offen

[x] **Abrechnung Jahr** - models + router + smoke tests
- [x] GET /abrechnung/jahr
- [x] GET /abrechnung/jahr/{id}
- [x] POST /abrechnung/jahr (delete-and-recreate)
- [x] GET /abrechnung/jahr/offen

---

## 🟡 MEDIUM PRIORITY - Supporting Features

### Phase 4: Supporting Tables

[x] **Zaehlprotokoll** - models + router + smoke tests
- [x] GET /zaehlprotokoll
- [x] GET /zaehlprotokoll/{id}
- [x] POST /zaehlprotokoll
- [x] PATCH /zaehlprotokoll/{id}
- [x] GET /zaehlprotokoll/abrechnung/{abrechnung_tag_id}

[x] **Bestellung** - models + router + smoke tests
- [x] GET /bestellung
- [x] GET /bestellung/{bestell_nr}
- [x] POST /bestellung
- [x] PATCH /bestellung/{bestell_nr}
- [x] DELETE /bestellung/{bestell_nr}
- [x] Positions saved/read together with the order (`details` in POST/PATCH, returned by GET /bestellung/{bestell_nr}) - matches Java "Bestellung abschließen"
- [x] No separate position endpoints needed (Java always saves the whole order, see parity audit)
- [x] Date filter on `GET /bestellung` (`von`/`bis` params) - done
- [x] `typ` restricted to the Java POS values `LM` (Lebensmittel), `KHW` (Kunsthandwerk) and `IVT` (Inventur); defaults to `LM` like the Java order form; invalid values are rejected by API (422) and CSV import (400)

---

## 🟡 MEDIUM PRIORITY - German Compliance (TSE)

### Phase 5: TSE Integration

[x] **TSE Transaction Support** - models + router + smoke tests (stub adapter)
- [x] GET /tse/transaction
- [x] GET /tse/transaction/{id}
- [x] POST /tse/transaction
- [x] GET /tse/status
- [x] POST /tse/init
- [x] POST /tse/export/full
- [x] POST /tse/export/partial
- [x] POST /tse/export/delete
- [x] POST /tse/certificates - items 12
- [x] GET /tse/transaction/verkauf/{rechnungs_nr} - items 12
- [⏳] TSE C library (libse-api-c.so) wraps open/init/start/finish/export/delete via ctypes; untested without hardware (Phase 5)
- [x] Automatic incremental TSE export in daily settlement - wired into POST /abrechnung/tag (step 3)
- [x] Export endpoints now call tse_client.export_full/partial/export_and_delete (fallback to placeholder when no data/device) - step 2
- [x] `export_and_delete` now calls se_deleteStoredDataUpTo (up to current signature counter) - items 9-11
- [x] Export endpoints now call tse_client (fallback to placeholder) - done
- [x] Partial export honors tx number range, date range (converted to epoch), sig counter, max_records - items 9-11
- [x] POST /tse/certificates, GET /tse/transaction/verkauf/{rechnungs_nr} implemented - items 12

---

## 🟡 MEDIUM PRIORITY - Business Logic Porting

### Phase 6: Core Business Logic from Java (main flows wired; gaps below)

[x] VAT Calculation Module (python/business/vat_calculator.py) - complete and Java-parity checked
- [x] `calculate_vat` mirrors `WindowContent.calculateVAT` (divide to 10 places HALF_UP, multiply, round to cents HALF_UP); handles negative storno amounts, 0 % rates and string/percent inputs
- [x] `calculate_netto` / `calculate_total` (dicts, tuples, objects; skips missing prices)
- [x] `calculate_mwst_values_in_rechnung` aggregates per rate and returns rates sorted ascending like the Java `TreeMap`; missing rates are booked at 0 %
- [x] `get_all_current_mwst_values_by_id` maps MwSt IDs to `[rate, netto, betrag, brutto]`; rates are matched numerically so DB values like `0.19000` match `0.19` (previous string comparison silently dropped them)
- [x] Used by sale creation (`calculate_mwst_summary`) and the Abrechnung Tag response (`mwst_nach_id`); `tests/test_vat_calculator.py` covers the module at 100 %
- [x] Rounding mode researched (2026-10-25): no German statutory rounding rule for VAT on invoices (§ 14 UStG / § 33 UStDV); EuGH C-484/06 leaves the method to the Member States; commercial rounding to cents (`ROUND_HALF_UP`) is the practice and matches the Java POS' explicit `RoundingMode.HALF_UP`. Details/sources: `docs/VAT_ROUNDING.md`
- [x] Rounding method configurable for receipts via `VAT_ROUNDING_METHOD` (`horizontal` = per position, Java POS default; `vertical` = per VAT rate, EN 16931 BR-CO-17). Read per request from the environment, invalid values abort startup; stored in `verkauf_mwst` for new sales. Invoices must always pass `method="vertical"` explicitly
[x] Sale Workflow Enhancements (python/business/sale_workflow.py) - complete
- [x] `validate_detail` runs before any write (rejects `stueckzahl == 0`, unknown `artikel_id`, unknown `rabatt_id`)
- [x] `determine_mwst_satz` derives the rate via `artikel.produktgruppe.mwst`; VAT for discounts always comes from the article
- [x] `determine_ges_preis` covers explicit price, article price and `variabler_preis` articles (no derived price)
- [x] Discount handling now mirrors Java `Kassieren.checkForRabatt`: currently active actions are selected **automatically** (article-specific or via matching product group with `NULL` as wildcard, within the `von..bis` window); an explicitly passed `rabatt_id` overrides automatic selection and is validated (exists, active, applies to the article); all four modes are supported in Java order: absolute, relative, buy-X-get-Y-free, quantity-relative; a discount exceeding the line price is rejected; negative quantities (storno) get no discount
- [x] Automatically applied discounts are recorded in `verkauf_details.rabatt_id` when exactly one action applies (bookkeeping attribution)
- [x] EC threshold helper delegates to `cash_register.ec_payment_threshold_check` (no duplicate implementation)
- [x] Dead duplicate sale-creation path (`create_verkauf`/`create_sale` in the module, unused by the API) removed - the router remains the single sale implementation
- [x] Covered by tests/test_sale_workflow.py (auto/explicit discounts, group wildcards, date windows, all four modes, rejections, router-level attribution)
[x] Storno Logic Enhancements (python/business/storno_logic.py) - complete
- [x] Inverted sale/mwst/details entries identical to Java `HeutigeRechnungen.insertStornoIntoVerkauf` (position, artikel, rabatt, mwst copied; stueckzahl/ges_preis/mwst negated)
- [x] Storno receipt mirrors the **original payment mode** (Java: `ec_zahlung = !zahlMod.equals("Bar")`)
- [x] Refund to the customer is always in cash (Java `insertStornoIntoTSE` sends "Bar" even for EC sales: "Weltladen can only pay back in bar"), so the reversing Kassenstand entry is written for cash **and** EC stornos by default; `cash_refund=false` remains only for the edge case that a card charge was not executed
- [x] Voucher cancellation (restbetrag 0, creation position kept) and open-installment resolution against the storno receipt (Java `maybeInsertStornoIntoGutschein` / `maybeInsertStornoIntoAnzahlung`)
- [x] TSE transaction for the storno (best-effort, still untested without hardware); `user_id` attribution on both the storno sale and the TSE row
- [x] Validation: original must exist, must not be a storno, must not already have a storno
- [x] **Storno is only allowed for receipts not yet part of a completed Tagesabschluss**: a receipt whose `rechnungs_nr` falls into any `abrechnung_tag` range is rejected with `400` and a clear message naming the settlement; a finished settlement is immutable
- [x] Single transaction with rollback - a failed inversion no longer leaves a half-written storno
- [x] Covered by tests/test_verkauf_storno.py and tests/test_storno_logic.py (payment modes, cash payout, settlement guard, rollback, attribution, voucher/installment handling); storno_logic.py at 94 %
[x] Cash Register Operations (python/business/cash_register.py) - complete
- [x] Payment processing: `calculate_change`, `process_payment` (change + EC warning) and `ec_payment_threshold_check` (10 EUR threshold, Java `ecSchwelle`) wired into sale creation
- [x] Kassenstand integration: every cash sale/storno appends an entry; manual entries and Entnahmen are validated (`validate_balance_change`); balance updates are serialized (process lock + `SELECT ... FOR UPDATE`)
- [x] End-of-day: `end_of_day_procedure` is now a real read-only preview of the open period and exposed as `GET /abrechnung/tag/vorschau` (period range since the last settlement, sales/cash/EC/storno counts, VAT per rate, `bar_brutto`, storno/retouren sums, withdrawctions, current and expected balance). `POST /abrechnung/tag` reuses the same aggregation (`aggregate_period`/`open_period_range`), so preview and settlement cannot drift apart
- [x] Java parity for the closing balance: the settlement now **links the current Kassenstand entry** (highest id) instead of inventing a new one. The old auto-entry double-counted cash sales and Entnahmen (the ledger already contains them); the counted cash is recorded as a manual Kassenstand entry before closing, like the Java POS
- [x] Fixed while extracting: explicit `rechnungs_nr_von/bis` settlements crashed on an unset `last` variable; `storno_summe` now reports the cancelled original amounts positively (Java `prepareStmtStornos`) instead of summing the negative storno rows
- [x] `is_training_mode` reads `TRAINING_MODE`; the training flow itself lives in `/training`
- [x] Covered by tests/test_abrechnung_tag.py (preview before/after settlement, stornos/retouren, Entnahmen, explicit range), tests/test_kassenstand.py and tests/test_integration.py; cash_register.py at 90 %

---

## 🔴 HIGH PRIORITY - Business Logic Wiring Gaps (modules exist but not integrated)

### Cash Register (`python/business/cash_register.py`)
- [x] `update_kassenstand_for_sale` wired into `verkauf.py` create (cash only) and storno (cash refund) → per-sale kassenstand entries (manuell=False) now created
- [x] `ec_payment_threshold_check` invoked in sale creation → EC warning surfaced in response (`ec_warning` field on VerkaufPublic)
- [x] `process_payment` wired into sale creation (change + EC warning) - items 5-8 (helper available)
- [x] `end_of_day_procedure` implemented (basic summary) - step 5
- [x] `is_training_mode` reads TRAINING_MODE env var - items 5-8
- [x] Training sale endpoints under `/training` write to the `training_*` tables (see Production Readiness)

### Sale Workflow (`python/business/sale_workflow.py`)
- [x] `check_ec_payment_threshold` invoked in sale endpoint (EC warning surfaced)
- [x] Voucher creation integrated into sale creation (GUTSCHEIN article creates Gutschein) - items 1-4
- [x] Discount handling integrated in determine_ges_preis: all four Java modes (absolute, relative, buy-X-get-Y-free, quantity-relative), automatic selection of active actions incl. product-group wildcards, explicit `rabatt_id` override with date/match validation, negative-result rejection - items 1-4
- [x] `require_user` enforced on all transaction create/mutate endpoints (step 4 enforcement follow-up)

### Storno (`python/business/storno_logic.py`)
- [x] `handle_storno_voucher` implemented (cancels linked vouchers) - items 1-4
- [x] `handle_storno_installment` implemented (resolves open installments against storno) - items 1-4
- [x] TSE transaction handling for storno (best-effort) - items 1-4
- [x] Reversing kassenstand entry for storno (step 1)
- [x] `get_all_current_mwst_values_by_id` used in abrechnung_tag response (mwst_nach_id) - items 5-8

### Abrechnung Tag (`python/routers/abrechnung_tag.py`)
- [x] Stornos/retouren handled via negative entries; entnahmen subtracted (step 5)
- [x] Automatic incremental TSE export performed (best-effort) - step 3
- [x] `bar_brutto` aggregation matches Java: SUM(ges_preis) over non-EC sales per VAT rate, storno/retour included via negative values - done

### Auth / Transaction Attribution
- [x] Per-user auth enforced on transaction create/mutate endpoints
- [x] `user_id` auto-populated from JWT on all transaction tables
- [x] logout/me read token from Authorization header
- [x] SQL migration script created in migrations/02_user_auth/

## 🟢 LOW PRIORITY - Utilities and Enhancements

### Phase 7: Data Import/Export, Validation, Auth

[x] Import/Export Functionality - `import_bestellung_from_csv` imports positions (`artikel_id`/`stueckzahl`/`position`, rows grouped by order header) with validation; `import_artikel` maps all Artikel fields; CSV exports for artikel, abrechnung, bestellung (VK order list) and inventur (EK valuation, mirrors Java `writeInventur`); session dependency fixed (step 7)
[ ] ODS/Spreadsheet export (later phase) - Java POS writes `Bestellvorlage_<typ>.ods` / `Inventur.ods` and fills cells (date/KW for orders, "Inventur 31.12.<jahr>" headline for inventory); needs an ODS library and the `../git/vorlagen/` templates. Also relevant for `abrechnung_tag`/`abrechnung_monat`/`abrechnung_jahr` (Tages-/Monats-/Jahresabrechnung.ods)
[x] Search and Filter Enhancements - complete for all list endpoints
- Catalog: `artikel` (aktiv_only, search_string over name/shortname/number/origin/barcode, barcode, artikel_nr, artikel_name, lieferant_id, produktgruppen_id), `lieferant` and `produktgruppe` (aktiv_only, search_string, name/parent filters), `mwst` (search_string) - already present, now documented as the pattern
- `rabattaktion`: search_string (Aktionsname), `artikel_id`/`produktgruppen_id`, `current_only` (running now), typed `von`/`bis`, `exclude_deleted`. Fixed a bug where open-ended actions (`bis IS NULL`) vanished from the default list (Java keeps them: `bis != von OR bis IS NULL`)
- `bestellung`: `typ` filter (validated against LM/KHW/IVT) on top of the existing `von`/`bis`
- `kassenstand`: `von`/`bis` on `buchungsdatum` (plus the existing `rechnungen` filter)
- `anzahlung`: `anzahlung_in_rech_nr` / `aufloesung_in_rech_nr`
- `zaehlprotokoll`: `abrechnung_tag_id` on the list endpoint
- `tse/transaction`: `rechnungs_nr` filter and bounded `limit`
- `users`: `role`, `active`, `search_string`, sorted by username
- Sorting: `verkauf` already had `desc`; settlement lists (`abrechnung/tag|monat|jahr`) can now be sorted newest-first with `desc=true`
- Pagination: every list endpoint now uses `offset` + `limit` with `limit <= 100` (TSE list was unbounded before)
- Covered by tests/test_filters.py (all new filters, the open-ended Rabattaktion regression, settlement ordering, invalid type rejection)
[⏳] Validation Framework - model-level constraints added (MwstBase 0-1, Kassenstand, Gutschein, AnzahlungDetails, BestellungDetails); `ensure_*` helpers in `utils/validation.py` are fully unit-tested (100% coverage) but still not called by any router
[⏳] Authentication and Authorization System (per-user accounts, login auditing, transaction attribution) - HIGH PRIORITY
  - Models + login/logout/me + user CRUD exist
  - `require_user` enforced on all transaction create/mutate endpoints (step 4 enforcement follow-up)
  - `user_id` now populated from auth token in all transaction create endpoints (step 4 follow-up)
  - logout/me now read token from Authorization header (step 4)
  - Password hashing switched to bcrypt; JWT switched to PyJWT (step 4)
  - SQL migration script created in migrations/02_user_auth/ (step 4)
  - user_id columns added to all 8 transaction table models (step 4)
[x] Transport security (HTTPS on LAN) - documented in python/README.md (step 7)

---

## 📚 Documentation Tasks

- [ ] API Documentation Enhancement - `docs/API.md` and auto-generated `/docs` exist; endpoint reference still incomplete
- [ ] Code Documentation - docstrings are inconsistent across routers/business modules
- [ ] Migration Documentation - guide for switching from the Java POS to the API is missing
- [ ] Setup and Deployment - dev/prod start, auth and HTTPS are in `python/README.md`; a complete deployment guide (TLS, service unit, backup) is missing. The planned same-origin nginx topology and the script-automation rules are documented in `concepts/IMPLEMENTATION_PLAN.md` (Phase 7.4) and in the Production Readiness section here; the nginx/systemd artifacts are not written yet.
- [ ] Database Schema Documentation - schema reference is missing (`../git/mysql/generateDB.sql` is the only source)

---

## 🧪 Testing Tasks

### Unit Tests

- [x] tests/test_mwst.py
- [x] tests/test_pfand.py
- [x] tests/test_phase2_smoke.py
- [x] tests/test_phase3_smoke.py
- [x] tests/test_phase4_smoke.py
- [x] tests/test_phase5_smoke.py
- [x] tests/test_kassenstand.py
- [x] tests/test_gutschein.py
- [x] tests/test_anzahlung.py
- [x] tests/test_abrechnung_tag.py
- [x] tests/test_abrechnung_monat.py
- [x] tests/test_abrechnung_jahr.py
- [x] tests/test_zaehlprotokoll.py
- [x] tests/test_bestellung.py (incl. positions/details)
- [x] tests/test_tse.py
- [x] tests/test_auth.py
- [x] tests/test_vat_calculator.py
- [x] tests/test_verkauf_storno.py (storno flow)
- [x] tests/test_sale_workflow.py
- [x] tests/test_storno_logic.py
- [x] tests/test_import_export.py

### Integration Tests

- [x] Complete workflows (`test_integration.py`: sale → kassenstand → Tagesabschluss → Monat → Jahr; EC sale without cash)
- [x] Cross-entity relationships (Gutschein sale + Anzahlung reversed by storno; Bestellung positions reference Artikel)
- [x] Concurrent operations (4 parallel sales produce distinct receipts and a consistent running Kassenstand)

### Test Coverage Target

- [x] Achieve 80%+ coverage (measured 90% on 2026-10-27, 238 tests passing)

---

## 🔎 Parity Audit 2026-10-22 (completed)

The imported low-priority endpoint ideas were checked against the Java POS (`../git/src/org/weltladen_bonn/pos/`) and the open items were updated accordingly:

- **Removed as not needed** (no Java equivalent, so no parity value):
  - per-sale installments lookup (`GET /anzahlung/verkauf/{rechnungs_nr}`) - `AnzahlungAufloesDialog` starts from the open installments grouped by `anzahlung_in_rech_nr`; `/anzahlung/offen` + `/{id}/details` + `GET /verkauf/{rechnungs_nr}` already cover the flow.
  - per-date/per-period settlement lookups (`/abrechnung/tag/heute`, `/abrechnung/tag/{date}`, `/abrechnung/monat/{jahr}/{monat}`, `/abrechnung/jahr/{jahr}`) - `Abrechnungen.java` only shows paginated lists of all settlements; the list endpoints already return the date/month/year.
  - balanced-protocol validation for zaehlprotokoll - not a Java feature: `ZaehlprotokollDialog` shows the difference to the target balance and accepts any count after confirmation; the difference is explained via `kommentar`.
- **Fixed real gap**: Bestellung positions - no API path wrote `bestellung_details`, so orders had no positions. Positions are now embedded in POST/PATCH (`details`) and returned by `GET /bestellung/{bestell_nr}`; separate position endpoints are not needed because the Java POS always saves the whole order at once.
- **Fixed by integration tests (2026-10-24)**: `GET /anzahlung/offen` kept resolved installments because the table is append-only (now matches Java `HAVING COUNT(*) = 1`); concurrent sales could overwrite each other's Kassenstand balance (now serialized with a process lock + `SELECT ... FOR UPDATE`).

The remaining imported items are quality/production tasks, tracked below.

---

## 🏭 Production Readiness Findings (2026-10-22)

- [ ] **Integration against a real MariaDB** - tests use in-memory SQLite only, which does not enforce foreign keys and ignores `UNSIGNED`/`YEAR`/`TIMESTAMP` semantics. Needs a smoke run against `../git/mysql/generateDB.sql` with both the `mitarbeiter` and `kassenadmin` grants (especially: `bestellung` composite PK/`AUTO_INCREMENT`, delete order of parent/child rows, timezone round-trips, DECIMAL rounding).
- [x] **Frontend readiness** - CORS is configured in `python/main.py` (`CORS_ORIGINS` env var, defaults to the SvelteKit dev server on port 5173); `GET /bestellung` has a date filter. Keep the OpenAPI schema stable for the generated client.
- [ ] **Training mode** - Java POS supports a training mode writing to `training_*` tables; core training sale flow implemented (`GET /training/status`, `GET/POST /training/verkauf`, `GET /training/verkauf/{rechnungs_nr}` writing `training_verkauf*` + `training_kassenstand`). Still missing: training storno, training Tagesabschluss/Monat/Jahr, training gutschein/anzahlung/zaehlprotokoll and clearing training data.
- [ ] **Deployment** - setup, HTTPS and auth are documented in `python/README.md`; a migration guide and a DB schema reference are still missing.
- [ ] **Same-origin deployment behind nginx (planned, deferred)** - frontend and API served from one origin: nginx serves the SvelteKit build at `/`, proxies `/api/` to FastAPI on `127.0.0.1:8000` (Uvicorn `--root-path /api`), terminates TLS with the internal CA and blocks plain HTTP. CORS then only matters for the Vite dev server via `CORS_ORIGINS`. Still to be written: nginx site config, systemd units, backup procedure.
- [ ] **Script automation (planned)** - future cron/scripts (price changes, supplier article imports, settlement creation) call the API over the same-origin nginx URL; CORS is irrelevant for them. They authenticate via `POST /auth/login` with a dedicated service account (visible in the `anmeldung` audit), verify the internal CA, re-login on `401`, and check state (`GET /abrechnung/monat/offen`, `GET /abrechnung/jahr/offen`) before creating because `POST`s are not idempotent. Kassenstand writes require a single API worker (process lock) or rely on `SELECT ... FOR UPDATE` in MariaDB.

---

## 🎯 Final Success Criteria Checklist

### Core Functionality

- [x] Most database tables have corresponding models and endpoints (Phase 1-5)
- [x] All database tables have models (training tables now have core sale endpoints)
- [ ] All business logic from Java POS ported (Phase 6) - main flows wired, see "Business Logic Wiring Gaps"
- [ ] Comprehensive validation and error handling (Phase 7) - validation module exists but rarely applied
- [x] Per-user accounts with login auditing (Phase 7.4) - models + endpoints + migration + enforcement complete
- [x] Transaction attribution via user_id (all 8 transaction tables have the column; populated from token where present) (step 4 follow-up)
- [ ] Proper separation of concerns

### Quality Assurance

- [x] 80%+ test coverage (90% achieved)
- [ ] All endpoints documented
- [ ] All code documented

### Documentation

- [ ] Complete API documentation
- [ ] Migration guide
- [ ] Setup instructions

### Production Readiness

- [ ] Working integration with existing database
- [ ] Ready for frontend client development
- [ ] Ready for production deployment (concurrent Kassenstand updates are serialized per process; multi-worker setups rely on `SELECT ... FOR UPDATE`)

---

## 📊 Summary Statistics

### Models Status
- **Models Implemented**: 35+ table models (Phase 1-5 + User + Anmeldung + training tables)
- **Models Missing**: none (training tables have core sale endpoints, see `/training`)

### Endpoints Status
- **Routers Implemented**: 19 routers (incl. auth, users, import_export)
- **Phase 1-5 endpoints**: implemented; the optional per-date/per-period lookup and balanced-protocol items were dropped as not needed for Java parity (see "Parity Audit")
- **Phase 6/7**: main sale/storno/settlement flows wired; per-user auth enforced on transaction create/mutate endpoints (admin endpoints still also accept the shared `ADMIN_TOKEN` stopgap)

### Business Logic Status
- **Business Logic Ported**: CRUD + settlement aggregation + VAT/sale-workflow/storno/cash-register modules wired into the endpoints; VAT module is Java-parity checked and fully tested
- **Business Logic NOT wired**: TSE hardware (adapter untested); training mode covers sales only
- **Remaining Java logic**: mainly validation/edge cases and training mode; no missing core workflow

### Testing Status
- **Test Files**: 24 (incl. dedicated tests for abrechnung_monat/jahr, tse, sale_workflow, storno_logic, import_export)
- **Test Coverage**: 90% measured with pytest-cov (target 80% achieved)

---

## 🚀 Recommended Next Steps

1. **Real database validation**: run a smoke test against MariaDB with `../git/mysql/generateDB.sql` and the real grants; fix anything SQLite hides (FK enforcement, `AUTO_INCREMENT`/composite PK, `YEAR`/`UNSIGNED`, timezone, DECIMAL)
2. **Frontend readiness**: CORS is configured via `CORS_ORIGINS` (defaults to the SvelteKit dev server); keep the OpenAPI schema stable
3. **Integration tests**: done in `test_integration.py` (workflows, cross-entity effects, concurrent sales)
4. **Coverage**: target 80%+ reached; remaining gaps: tse_client.py 44%, users 33%, rabattaktion 33%
5. **Validation**: apply the `ensure_*` helpers in the routers (helpers are tested, but still unused)
6. **Training mode**: extend the `/training` endpoints (storno, settlements, gutschein/anzahlung) if the frontend needs them
7. **Import/Export**: CSV exports for Bestellung and Inventur exist; ODS export is deferred to a later phase (see "Phase 7" above)
8. **Documentation**: migration guide (Java POS → API), database schema reference, consistent docstrings, deployment/HTTPS docs

---

*This TODO list reflects the current implementation state as of 2026-10-23 (completeness check against IMPLEMENTATION_PLAN.md).*