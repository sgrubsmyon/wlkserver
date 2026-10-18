# Weltladenkasse API - Detailed TODO List

> **Sync note**: This document and `concepts/IMPLEMENTATION_PLAN.md` must be kept in sync. When implementation progress changes, update both files so new sessions without prior memory see a consistent status.

> **Last Updated**: 2026-10-18  
> **Status**: Phases 1-4 implemented and tested; Phase 5 implemented as stubs (TSE C library not yet ported); Phase 6/7 pending

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
- [ ] Advanced business logic (balance validation) - Phase 6

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
- [ ] Automatic incremental TSE export (Phase 5)
- [ ] Full Java aggregation (stornos, retouren, entnahmen) - Phase 6

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
- [ ] Port/wrap TSE C library (ctypes/cffi) in python/utils/tse_client.py (currently stub)
- [ ] Automatic incremental TSE export in daily settlement

---

## 🟡 MEDIUM PRIORITY - Business Logic Porting

### Phase 6: Core Business Logic from Java

[ ] VAT Calculation Module (python/business/vat_calculator.py)
[ ] Sale Workflow Enhancements (python/business/sale_workflow.py)
[ ] Storno Logic Enhancements (python/business/storno_logic.py)
[ ] Cash Register Operations (python/business/cash_register.py)

---

## 🟢 LOW PRIORITY - Utilities and Enhancements

### Phase 7: Data Import/Export, Validation, Auth

[ ] Import/Export Functionality
[ ] Search and Filter Enhancements
[ ] Validation Framework
[ ] Authentication and Authorization System (per-user accounts, login auditing, transaction attribution) - HIGH PRIORITY
[ ] Transport security (HTTPS on LAN)

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
- [ ] All business logic from Java POS ported (Phase 6)
- [ ] Comprehensive validation and error handling (Phase 7)
- [ ] Per-user accounts with login auditing (Phase 7.4)
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
- **Models Implemented**: 18 table models (Phase 1-5)
- **Models Missing**: 15+ (training tables, user/anmeldung, import/export)

### Endpoints Status
- **Routers Implemented**: 16 routers
- **Phase 1-5 endpoints**: implemented (with minor optional endpoints remaining)
- **Phase 6/7**: pending

### Business Logic Status
- **Business Logic Ported**: Basic CRUD + partial settlement aggregation
- **Business Logic to Port**: ~90% of Java business logic still needs porting (Phase 6)

### Testing Status
- **Test Files**: 9 (2 original + 7 smoke)
- **Test Coverage**: Low
- **Target Coverage**: 80%+

---

## 🚀 Recommended Next Steps

1. Port TSE C library (Phase 5 completion)
2. Implement Phase 6 business logic (VAT calculator, sale workflow, storno, cash register)
3. Implement Phase 7 (auth, import/export, validation)
4. Comprehensive testing to reach 80%+ coverage
5. Documentation

---

*This TODO list reflects the current implementation state as of 2026-10-18.*