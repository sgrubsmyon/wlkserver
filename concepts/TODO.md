# Weltladenkasse API - Detailed TODO List

> **Sync note**: This document and `concepts/IMPLEMENTATION_PLAN.md` must be kept in sync. When implementation progress changes, update both files so new sessions without prior memory see a consistent status.

> **Last Updated**: 2026-10-19  
> **Status**: Phases 1-5 implemented at router level (TSE export still stubs); Phase 6/7 modules exist but much business logic is NOT wired into endpoints (see "Business Logic Wiring Gaps"); auth not enforced anywhere; test coverage low

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
[ ] Training table models (training_verkauf*, training_kassenstand, training_anzahlung*, training_gutschein, training_abrechnung_*, training_zaehlprotokoll*) - MISSING (not in models.py)
[x] User model (Table, Public, Create, Update) - Phase 7.4
[x] Anmeldung model (Table) - Phase 7.4 (login auditing)
[x] `user_id` FK column added to gutschein, zaehlprotokoll, bestellung, tse_transaction models (step 4)
[x] SQL migration script created in `migrations/02_user_auth/` (user_auth.sql + migrate_user_auth.py + migrate.sh) (step 4)
[x] Auth utils switched to bcrypt + PyJWT (step 4)
[x] Auth router logout/me now read token from Authorization header (step 4)
[ ] Per-user auth enforcement on transaction endpoints still pending (require_user available but not enforced, to keep tests green)

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
[x] Bestellung router - CRUD
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
- [ ] `MwstBase.mwst_satz` has no `ge=0, le=1` constraint (only `MwstCreate`/`MwstUpdate` enforce it) - validation gap

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
- [ ] GET /kassenstand/letzte (not implemented; /aktuell covers latest)
- [x] `update_kassenstand_for_sale` wired into sale creation + storno (cash only) - Phase 6 (step 1)
- [ ] Advanced business logic (balance validation) - Phase 6
- [ ] Non-negative validation on `neuer_kassenstand` not enforced

[x] **Gutschein** - models + router + smoke tests
- [x] GET /gutschein
- [x] GET /gutschein/{id}
- [x] POST /gutschein
- [x] POST /gutschein/{id}/einloesen
- [x] GET /gutschein/ausstehend
- [x] GET /gutschein/eingeloest
- [ ] GET /gutschein/teilingeloest (not implemented)
- [ ] GET /gutschein/verkauf/{rechnungs_nr} (not implemented)
- [ ] Advanced redemption calculation - Phase 6

[x] **Anzahlung** - models + router + smoke tests
- [x] GET /anzahlung
- [x] GET /anzahlung/{id}
- [x] POST /anzahlung
- [x] POST /anzahlung/{id}/aufloesen
- [x] GET /anzahlung/offen
- [x] GET /anzahlung/aufgeloest
- [x] POST /anzahlung/details
- [ ] GET /anzahlung/verkauf/{rechnungs_nr} (not implemented)

---

## 🟡 MEDIUM PRIORITY - Accounting System

### Phase 3: Settlement Tables

[x] **Abrechnung Tag** - models + router + smoke tests
- [x] GET /abrechnung/tag
- [x] GET /abrechnung/tag/{id}
- [x] POST /abrechnung/tag (basic Tagesabschluss aggregation)
- [x] GET /abrechnung/tag/offen
- [ ] GET /abrechnung/tag/heute
- [ ] GET /abrechnung/tag/{date}
- [x] Automatic incremental TSE export (best-effort) wired into POST /abrechnung/tag - step 3
- [x] Stornos/retouren handled in mwst + bar aggregation; entnahmen subtracted from closing balance (step 5)
- [ ] Full Java aggregation parity (separate storno/retouren reporting) - Phase 6
- [ ] kassenstand entry validation during Tagesabschluss

[x] **Abrechnung Monat** - models + router + smoke tests
- [x] GET /abrechnung/monat
- [x] GET /abrechnung/monat/{id}
- [x] POST /abrechnung/monat (delete-and-recreate)
- [x] GET /abrechnung/monat/offen
- [ ] GET /abrechnung/monat/{jahr}/{monat}

[x] **Abrechnung Jahr** - models + router + smoke tests
- [x] GET /abrechnung/jahr
- [x] GET /abrechnung/jahr/{id}
- [x] POST /abrechnung/jahr (delete-and-recreate)
- [x] GET /abrechnung/jahr/offen
- [ ] GET /abrechnung/jahr/{jahr}

---

## 🟡 MEDIUM PRIORITY - Supporting Features

### Phase 4: Supporting Tables

[x] **Zaehlprotokoll** - models + router + smoke tests
- [x] GET /zaehlprotokoll
- [x] GET /zaehlprotokoll/{id}
- [x] POST /zaehlprotokoll
- [x] PATCH /zaehlprotokoll/{id}
- [x] GET /zaehlprotokoll/abrechnung/{abrechnung_tag_id}
- [ ] Balanced protocol validation

[x] **Bestellung** - models + router + smoke tests
- [x] GET /bestellung
- [x] GET /bestellung/{bestell_nr}
- [x] POST /bestellung
- [x] PATCH /bestellung/{bestell_nr}
- [x] DELETE /bestellung/{bestell_nr}
- [ ] POST /bestellung/{bestell_nr}/Position
- [ ] DELETE /bestellung/{bestell_nr}/Position/{position}

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
- [ ] POST /tse/certificates
- [ ] GET /tse/transaction/verkauf/{rechnungs_nr}
- [⏳] TSE C library (libse-api-c.so) wraps open/init/start/finish/export/delete via ctypes; untested without hardware (Phase 5)
- [x] Automatic incremental TSE export in daily settlement - wired into POST /abrechnung/tag (step 3)
- [x] Export endpoints now call tse_client.export_full/partial/export_and_delete (fallback to placeholder when no data/device) - step 2
- [ ] `export_and_delete` does not call se_deleteStoredDataUpTo (deletion still missing; needs highest exported sig counter parsing)
- [ ] `export_and_delete` does not call se_deleteStoredDataUpTo (deletion missing)
- [ ] Partial export ignores request body criterion (tx number range / date range / sig counter) in response
- [ ] POST /tse/certificates, GET /tse/transaction/verkauf/{rechnungs_nr} missing

---

## 🟡 MEDIUM PRIORITY - Business Logic Porting

### Phase 6: Core Business Logic from Java (modules exist; wiring incomplete)

[⏳] VAT Calculation Module (python/business/vat_calculator.py) - module complete, but `get_all_current_mwst_values_by_id` unused
[⏳] Sale Workflow Enhancements (python/business/sale_workflow.py) - `prepare_detail`/`calculate_mwst_summary` used in router; `validate_detail`, `determine_mwst_satz`, `determine_ges_preis` not fully exercised; voucher/discount handling (Java Kassieren articles 6/7) NOT integrated; `check_ec_payment_threshold` NOT invoked; `user_id` not populated from auth token
[⏳] Storno Logic Enhancements (python/business/storno_logic.py) - basic storno works; `handle_storno_voucher` and `handle_storno_installment` are PLACEHOLDERS; no TSE handling for storno; no reversing kassenstand entry
[⏳] Cash Register Operations (python/business/cash_register.py) - `update_kassenstand_for_sale` NOT wired into sale creation or storno; `process_payment`/`ec_payment_threshold_check` unused; `end_of_day_procedure` is a STUB; `is_training_mode` always returns False

---

## 🔴 HIGH PRIORITY - Business Logic Wiring Gaps (modules exist but not integrated)

### Cash Register (`python/business/cash_register.py`)
- [x] `update_kassenstand_for_sale` wired into `verkauf.py` create (cash only) and storno (cash refund) → per-sale kassenstand entries (manuell=False) now created
- [x] `ec_payment_threshold_check` invoked in sale creation → EC warning surfaced in response (`ec_warning` field on VerkaufPublic)
- [ ] `process_payment` still unused (helper available)
- [x] `end_of_day_procedure` implemented (basic summary) - step 5
- [ ] `is_training_mode` always returns False (no training mode)

### Sale Workflow (`python/business/sale_workflow.py`)
- [x] `check_ec_payment_threshold` invoked in sale endpoint (EC warning surfaced)
- [ ] Voucher creation/redemption handling (Java Kassieren articles 6/7) not integrated into sale creation
- [ ] Discount handling not integrated
- [x] `require_user` enforced on all transaction create/mutate endpoints (step 4 enforcement follow-up)

### Storno (`python/business/storno_logic.py`)
- [ ] `handle_storno_voucher` is a PLACEHOLDER (no voucher reversal)
- [ ] `handle_storno_installment` is a PLACEHOLDER (no installment reversal)
- [ ] No TSE transaction handling for storno
- [ ] No reversing kassenstand entry for storno
- [ ] `get_all_current_mwst_values_by_id` unused

### Abrechnung Tag (`python/routers/abrechnung_tag.py`)
- [ ] Aggregation does not handle stornos, retouren, entnahmen
- [x] Automatic incremental TSE export performed (best-effort) - step 3
- [ ] `bar_brutto` aggregation is rough (sum of detail ges_preis for non-EC sales)

### Auth / Transaction Attribution
- [ ] Per-user auth not enforced on any endpoint (`require_user` unused)
- [ ] `user_id` not auto-populated from JWT on any transaction table
- [ ] logout/me use query param token instead of Authorization header
- [ ] No SQL migration for user/anmeldung tables or user_id columns

## 🟢 LOW PRIORITY - Utilities and Enhancements

### Phase 7: Data Import/Export, Validation, Auth

[⏳] Import/Export Functionality - endpoints exist; `import_bestellung_from_csv` is a PLACEHOLDER; `import_artikel` only maps 3 fields; CSV export of abrechnung minimal; `/import/artikel` session dependency questionable
[⏳] Search and Filter Enhancements - minimal (only verkauf since/until/only_storno, mwst search_string); most routers have no filtering/sorting/pagination improvements
[⏳] Validation Framework - `python/utils/validation.py` exists but rarely applied; non-negative checks not enforced on kassenstand/gutschein/anzahlung/bestellung/zaehlprotokoll; `MwstBase.mwst_satz` lacks 0-1 constraint
[⏳] Authentication and Authorization System (per-user accounts, login auditing, transaction attribution) - HIGH PRIORITY
  - Models + login/logout/me + user CRUD exist
  - `require_user` enforced on all transaction create/mutate endpoints (step 4 enforcement follow-up)
  - `user_id` now populated from auth token in all transaction create endpoints (step 4 follow-up)
  - logout/me now read token from Authorization header (step 4)
  - Password hashing switched to bcrypt; JWT switched to PyJWT (step 4)
  - SQL migration script created in migrations/02_user_auth/ (step 4)
  - user_id columns added to all 8 transaction table models (step 4)
[ ] Transport security (HTTPS on LAN) - not configured

---

## 📚 Documentation Tasks

[ ] API Documentation Enhancement
[ ] Code Documentation
[ ] Migration Documentation
[ ] Setup and Deployment
[ ] Database Schema Documentation

---

## 🧪 Testing Tasks

### Unit Tests

- [x] tests/test_mwst.py
- [x] tests/test_pfand.py
- [x] tests/test_phase2_smoke.py
- [x] tests/test_phase3_smoke.py
- [x] tests/test_phase4_smoke.py
- [x] tests/test_phase5_smoke.py
- [ ] tests/test_kassenstand.py
- [ ] tests/test_gutschein.py
- [ ] tests/test_anzahlung.py
- [ ] tests/test_abrechnung_tag.py
- [ ] tests/test_abrechnung_monat.py
- [ ] tests/test_abrechnung_jahr.py
- [ ] tests/test_zaehlprotokoll.py
- [ ] tests/test_bestellung.py
- [ ] tests/test_tse.py
- [ ] tests/test_auth.py
- [ ] tests/test_vat_calculator.py
- [ ] tests/test_sale_workflow.py
- [ ] tests/test_storno_logic.py
- [ ] tests/test_import_export.py

### Integration Tests

- [ ] Complete workflows
- [ ] Cross-entity relationships
- [ ] Concurrent operations

### Test Coverage Target

- [ ] Achieve 80%+ coverage

---

## 🎯 Final Success Criteria Checklist

### Core Functionality

- [x] Most database tables have corresponding models and endpoints (Phase 1-5)
- [ ] All database tables have models (training tables missing)
- [ ] All business logic from Java POS ported (Phase 6) - modules exist but wiring incomplete
- [ ] Comprehensive validation and error handling (Phase 7) - validation module exists but rarely applied
- [x] Per-user accounts with login auditing (Phase 7.4) - models + endpoints + migration + enforcement complete
- [x] Transaction attribution via user_id (all 8 transaction tables have the column; populated from token where present) (step 4 follow-up)
- [ ] Proper separation of concerns

### Quality Assurance

- [ ] 80%+ test coverage
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
- **Models Implemented**: 20 table models (Phase 1-5 + User + Anmeldung)
- **Models Missing**: training tables (15+), user_id columns on gutschein/zaehlprotokoll/bestellung/tse_transaction

### Endpoints Status
- **Routers Implemented**: 19 routers (incl. auth, users, import_export)
- **Phase 1-5 endpoints**: implemented (with minor optional endpoints remaining)
- **Phase 6/7**: modules exist but wiring incomplete; auth not enforced

### Business Logic Status
- **Business Logic Ported**: Basic CRUD + partial settlement aggregation + VAT/storno/sale-workflow/cash-register modules
- **Business Logic NOT wired**: cash-register side-effects, TSE export, voucher/installment storno, training mode, full Abrechnung aggregation, EC threshold warning
- **Business Logic to Port**: ~90% of Java business logic still needs porting/integration (Phase 6)

### Testing Status
- **Test Files**: 9 (2 original + 7 smoke) - no dedicated tests for kassenstand/gutschein/anzahlung/abrechnung/zaehlprotokoll/bestellung/tse/auth/business modules
- **Test Coverage**: Low (unmeasured; no pytest-cov installed)
- **Target Coverage**: 80%+

---

## 🚀 Recommended Next Steps

1. Wire cash-register side-effects into sale creation + storno; surface EC threshold warning
2. Wire TSE export endpoints to tse_client and perform automatic incremental export in daily settlement
3. Implement voucher/installment reversal in storno
4. Add SQL migration for user/anmeldung tables + user_id columns; enforce per-user auth on endpoints; populate user_id from token
5. Port full Abrechnung aggregation (stornos, retouren, entnahmen) and end-of-day procedure
6. Add training-table models (or explicitly descope)
7. Apply validation utilities across all endpoints; add ge=0,le=1 to MwstBase.mwst_satz
8. Implement import_bestellung_from_csv and full CSV import/export
9. Write dedicated test files for each router + business module; add pytest-cov; reach 80%+
10. Documentation + HTTPS setup on LAN

---

*This TODO list reflects the current implementation state as of 2026-10-19 (completeness check against IMPLEMENTATION_PLAN.md).*