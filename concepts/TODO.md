# Weltladenkasse API - Detailed TODO List

> **Sync note**: This document and `concepts/IMPLEMENTATION_PLAN.md` must be kept in sync. When implementation progress changes, update both files so new sessions without prior memory see a consistent status.

> **Last Updated**: 2026-10-23  
> **Status**: Phases 1-5 implemented at router level (TSE export adapter untested without hardware); main Phase 6/7 flows wired (see "Business Logic Wiring Gaps" for what remains); auth enforced on transaction endpoints; parity audit of the remaining low-priority endpoints done and resolved (see "Parity Audit"), Bestellung positions + date filter implemented; bar_brutto aggregation matches Java; sale/workflow validation and kassenstand balance validation wired; Bestellung CSV import supports positions; 6 missing test files added; test coverage 83%

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
- [ ] Advanced redemption calculation - Phase 6

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
- [x] POST /abrechnung/tag (basic Tagesabschluss aggregation)
- [x] GET /abrechnung/tag/offen
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
- [x] Date filter on `GET /bestellung` (`since`/`until` params) - done

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

[⏳] VAT Calculation Module (python/business/vat_calculator.py) - complete; used by sale creation and the abrechnung response (`get_all_current_mwst_values_by_id`)
- [x] `validate_detail` now called by the sale endpoint (rejects `stueckzahl == 0` before writing); `determine_mwst_satz` derives the rate via `artikel.produktgruppe.mwst` (was broken); `determine_ges_preis` covers explicit price, article price, variable price and discounts - covered by tests/test_sale_workflow.py
[⏳] Storno Logic Enhancements (python/business/storno_logic.py) - basic storno works; voucher/installment handlers and reversing kassenstand entry implemented; TSE handling best-effort
[⏳] Cash Register Operations (python/business/cash_register.py) - `update_kassenstand_for_sale`, `process_payment`, `ec_payment_threshold_check` and `validate_balance_change` wired; `end_of_day_procedure` basic; `is_training_mode` reads `TRAINING_MODE` env var (no real training mode)

---

## 🔴 HIGH PRIORITY - Business Logic Wiring Gaps (modules exist but not integrated)

### Cash Register (`python/business/cash_register.py`)
- [x] `update_kassenstand_for_sale` wired into `verkauf.py` create (cash only) and storno (cash refund) → per-sale kassenstand entries (manuell=False) now created
- [x] `ec_payment_threshold_check` invoked in sale creation → EC warning surfaced in response (`ec_warning` field on VerkaufPublic)
- [x] `process_payment` wired into sale creation (change + EC warning) - items 5-8 (helper available)
- [x] `end_of_day_procedure` implemented (basic summary) - step 5
- [x] `is_training_mode` reads TRAINING_MODE env var - items 5-8 (no training mode)

### Sale Workflow (`python/business/sale_workflow.py`)
- [x] `check_ec_payment_threshold` invoked in sale endpoint (EC warning surfaced)
- [x] Voucher creation integrated into sale creation (GUTSCHEIN article creates Gutschein) - items 1-4
- [x] Discount handling integrated in determine_ges_preis (rabatt_relativ/absolut/mengenrabatt) - items 1-4
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

[x] Import/Export Functionality - `import_bestellung_from_csv` imports positions (`artikel_id`/`stueckzahl`/`position`, rows grouped by order header) with validation; `import_artikel` maps all Artikel fields; abrechnung CSV export includes VAT totals; session dependency fixed (step 7)
[⏳] Search and Filter Enhancements - minimal (only verkauf since/until/only_storno, mwst search_string); most routers have no filtering/sorting/pagination improvements
[⏳] Validation Framework - model-level constraints added (MwstBase 0-1, Kassenstand, Gutschein, AnzahlungDetails, BestellungDetails); `ensure_*` helpers in `utils/validation.py` exist but are **never called** by any router and have 0% test coverage
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
- [ ] Setup and Deployment - dev/prod start, auth and HTTPS are in `python/README.md`; a complete deployment guide (TLS, service unit, backup) is missing
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

- [ ] Complete workflows
- [ ] Cross-entity relationships
- [ ] Concurrent operations

### Test Coverage Target

- [x] Achieve 80%+ coverage (measured 83% on 2026-10-23, 119 tests passing)

---

## 🔎 Parity Audit 2026-10-22 (completed)

The imported low-priority endpoint ideas were checked against the Java POS (`../git/src/org/weltladen_bonn/pos/`) and the open items were updated accordingly:

- **Removed as not needed** (no Java equivalent, so no parity value):
  - per-sale installments lookup (`GET /anzahlung/verkauf/{rechnungs_nr}`) - `AnzahlungAufloesDialog` starts from the open installments grouped by `anzahlung_in_rech_nr`; `/anzahlung/offen` + `/{id}/details` + `GET /verkauf/{rechnungs_nr}` already cover the flow.
  - per-date/per-period settlement lookups (`/abrechnung/tag/heute`, `/abrechnung/tag/{date}`, `/abrechnung/monat/{jahr}/{monat}`, `/abrechnung/jahr/{jahr}`) - `Abrechnungen.java` only shows paginated lists of all settlements; the list endpoints already return the date/month/year.
  - balanced-protocol validation for zaehlprotokoll - not a Java feature: `ZaehlprotokollDialog` shows the difference to the target balance and accepts any count after confirmation; the difference is explained via `kommentar`.
- **Fixed real gap**: Bestellung positions - no API path wrote `bestellung_details`, so orders had no positions. Positions are now embedded in POST/PATCH (`details`) and returned by `GET /bestellung/{bestell_nr}`; separate position endpoints are not needed because the Java POS always saves the whole order at once.

The remaining imported items are quality/production tasks, tracked below.

---

## 🏭 Production Readiness Findings (2026-10-22)

- [ ] **Integration against a real MariaDB** - tests use in-memory SQLite only, which does not enforce foreign keys and ignores `UNSIGNED`/`YEAR`/`TIMESTAMP` semantics. Needs a smoke run against `../git/mysql/generateDB.sql` with both the `mitarbeiter` and `kassenadmin` grants (especially: `bestellung` composite PK/`AUTO_INCREMENT`, delete order of parent/child rows, timezone round-trips, DECIMAL rounding).
- [ ] **Frontend readiness** - API surface and JWT auth are usable. Open: no CORS in `python/main.py` (use a SvelteKit dev proxy or add a restricted CORS config), and `GET /bestellung` has no date filter although the Java "Bestellungen" view filters by date. Keep the OpenAPI schema stable for the generated client.
- [ ] **Training mode** - Java POS supports a training mode writing to `training_*` tables; only the models exist, no endpoints. Either implement or explicitly descope for the frontend.
- [ ] **Deployment** - setup, HTTPS and auth are documented in `python/README.md`; a migration guide and a DB schema reference are still missing.

---

## 🎯 Final Success Criteria Checklist

### Core Functionality

- [x] Most database tables have corresponding models and endpoints (Phase 1-5)
- [x] All database tables have models (training tables are table-only, no endpoints yet)
- [ ] All business logic from Java POS ported (Phase 6) - main flows wired, see "Business Logic Wiring Gaps"
- [ ] Comprehensive validation and error handling (Phase 7) - validation module exists but rarely applied
- [x] Per-user accounts with login auditing (Phase 7.4) - models + endpoints + migration + enforcement complete
- [x] Transaction attribution via user_id (all 8 transaction tables have the column; populated from token where present) (step 4 follow-up)
- [ ] Proper separation of concerns

### Quality Assurance

- [x] 80%+ test coverage (82% achieved)
- [ ] All endpoints documented
- [ ] All code documented

### Documentation

- [ ] Complete API documentation
- [ ] Migration guide
- [ ] Setup instructions

### Production Readiness

- [ ] Working integration with existing database
- [ ] Ready for frontend client development
- [ ] Ready for production deployment

---

## 📊 Summary Statistics

### Models Status
- **Models Implemented**: 35+ table models (Phase 1-5 + User + Anmeldung + training tables)
- **Models Missing**: none (training tables are model-only, endpoints not implemented)

### Endpoints Status
- **Routers Implemented**: 19 routers (incl. auth, users, import_export)
- **Phase 1-5 endpoints**: implemented; the optional per-date/per-period lookup and balanced-protocol items were dropped as not needed for Java parity (see "Parity Audit")
- **Phase 6/7**: main sale/storno/settlement flows wired; per-user auth enforced on transaction create/mutate endpoints (admin endpoints still also accept the shared `ADMIN_TOKEN` stopgap)

### Business Logic Status
- **Business Logic Ported**: CRUD + settlement aggregation + VAT/sale-workflow/storno/cash-register modules wired into the endpoints
- **Business Logic NOT wired**: training mode (only `TRAINING_MODE` env flag), TSE hardware (adapter untested)
- **Remaining Java logic**: mainly validation/edge cases and training mode; no missing core workflow

### Testing Status
- **Test Files**: 24 (incl. dedicated tests for abrechnung_monat/jahr, tse, sale_workflow, storno_logic, import_export)
- **Test Coverage**: 83% measured with pytest-cov (target 80% achieved)

---

## 🚀 Recommended Next Steps

1. **Real database validation**: run a smoke test against MariaDB with `../git/mysql/generateDB.sql` and the real grants; fix anything SQLite hides (FK enforcement, `AUTO_INCREMENT`/composite PK, `YEAR`/`UNSIGNED`, timezone, DECIMAL)
2. **Frontend readiness**: decide CORS vs. SvelteKit dev proxy; add a date filter to `GET /bestellung`; keep the OpenAPI schema stable
3. **Integration tests**: complete sales/storno/settlement workflows, cross-entity relationships, concurrent operations
4. **Coverage**: 82% achieved (target 80%+ met); remaining gaps: utils/validation.py 0%, tse_client.py 44%, users 33%, rabattaktion 33%
5. **Validation**: apply the `ensure_*` helpers in the routers (0% coverage, never called)
6. **Training mode**: implement endpoints for the `training_*` tables or explicitly descope it
7. **Import/Export**: extend CSV export for Bestellungen (positions are imported, but there is no order export yet)
8. **Documentation**: migration guide (Java POS → API), database schema reference, consistent docstrings, deployment/HTTPS docs

---

*This TODO list reflects the current implementation state as of 2026-10-23 (completeness check against IMPLEMENTATION_PLAN.md).*