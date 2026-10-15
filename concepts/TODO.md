# Weltladenkasse API - Detailed TODO List

> **Last Updated**: 2026-10-14  
> **Status**: Phase 1 (MwSt + Pfand admin CRUD with admin-token auth stopgap) implemented and tested

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
[x] MwSt models (Base, Table, Public)
[x] Pfand models (Table, Public)
[x] Produktgruppe models (Base, Table, Public, Create, Update)
[x] Artikel models (Base, Table, Public, Create, Update)
[x] Rabattaktion models (Base, Table, Public, Create, Update)
[x] Verkauf models (Base, Table, Public, Create)
[x] VerkaufMwst models (Base, Table, Public, Create)
[x] VerkaufDetails models (Base, Table, Public, Create)

### Existing Router Functionality
[x] Artikel router - Full CRUD with advanced versioning logic
[x] Lieferant router - Full CRUD with deactivation pattern
[x] Produktgruppe router - Full CRUD with deactivation pattern
[x] MwSt router - Read-only (GET /, GET /{id})
[x] Pfand router - Read-only (GET /, GET /{id})
[x] Rabattaktion router - Full CRUD with date validation and update restrictions
[x] Verkauf router - Create, Read, Storno functionality
[x] Main API setup with all routers included
[x] Database session management
[x] Test infrastructure (conftest.py, test_verkauf_storno.py)

---

## 🔴 HIGH PRIORITY - Complete Existing CRUD Operations

### Phase 1: Missing CRUD for Existing Models

[x] **MwSt Admin-Only CRUD Completion** - `python/routers/mwst.py`
- [x] POST /mwst - Create new VAT rate with validation (mwst_satz between 0 and 1, no duplicate rates) - **ADMIN ONLY**
- [x] PATCH /mwst/{mwst_id} - Update VAT rate - **ADMIN ONLY**
- [x] DELETE /mwst/{mwst_id} - Delete VAT rate (with constraints check) - **ADMIN ONLY**
- [x] Add business validation: prevent deletion (409) if used by produktgruppe
- [x] Add authentication/authorization dependency to protect admin endpoints (stopgap: shared `ADMIN_TOKEN` from env via `python/dependencies.py::require_admin`; to be replaced by per-user accounts in Phase 7.4)
- [x] See reference: `../git/src/org/weltladen_bonn/pos/kasse/RechnungsGrundlage.java` lines 74-94 (retrieveVATs method)

[x] **Pfand Admin-Only CRUD Completion** - `python/routers/pfand.py`
- [x] POST /pfand - Create new deposit item with artikel_id validation - **ADMIN ONLY**
- [x] PATCH /pfand/{pfand_id} - Update deposit item - **ADMIN ONLY**
- [x] DELETE /pfand/{pfand_id} - Delete deposit item (with constraints check) - **ADMIN ONLY**
- [x] Add business validation: ensure artikel_id references existing article, no duplicate pfand per article
- [x] Add wert (value) calculation from article.vk_preis
- [x] Add authentication/authorization dependency to protect admin endpoints (stopgap: shared `ADMIN_TOKEN`, see above)

Note (Phase 1): the API currently connects to the DB as `mitarbeiter`, which has no DELETE grant on `mwst`/`pfand`. Per Phase 7.4, the API process should connect as the `kassenadmin` service account (set `DBUSER`/`DBPASS` in `python/.env`); admin endpoints then work fully, and API-level roles restrict access. Until then, DELETE returns 503 with a clear message.

**Verkauf: No Update Functionality (Decision: By Design)** - `python/routers/verkauf.py`
- [x] No update endpoint for the `verkauf` table will ever be added (bookkeeping integrity)
- [x] Corrections happen via Storno (`POST /verkauf/{rechnungs_nr}/storno` creates a reversing entry referencing the original via `storno_von`), then optionally a new corrected sale
- [x] The existing Create/Read/Storno endpoint surface is complete; only the Storno logic itself will be enhanced (see Phase 6)

**Dedicated Related Table Endpoints (Decision: Not Planned)**
- [x] No separate endpoints for `verkauf_mwst` and `verkauf_details` (no `python/routers/verkauf_mwst.py`, no `python/routers/verkauf_details.py`)
- [x] Entries in these tables always exist together with a `verkauf` entry and are modified exclusively as side-effects of the `python/routers/verkauf.py` endpoints (sale creation, storno)

---

## 🔴 HIGH PRIORITY - Core Business Tables

### Phase 2: Missing Core Tables

[ ] **Kassenstand (Cash Register Balance)** - `../git/mysql/generateDB.sql` lines 125-135 (CR only - no update, no delete; SQL user has only INSERT grant)
- [ ] Add Kassenstand, KassenstandPublic, KassenstandCreate models to `python/models.py` (no Update model)
- [ ] Create `python/routers/kassenstand.py` (CR endpoints only)
- [ ] GET /kassenstand - List cash register balances with filtering (by date range, manuell, entnahme; plus `rechnungen=true|false` filter: default false → only manual entries via `WHERE manuell = TRUE`)
- [ ] GET /kassenstand/{kassenstand_id} - Get single cash register entry
- [ ] POST /kassenstand - Create new cash register entry
- [ ] GET /kassenstand/aktuell - Get current cash register balance
- [ ] GET /kassenstand/letzte - Get most recent cash register entry
- [ ] Add business logic: balance validation, change calculation
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/Kasse.java` (lines 48, 81-82, 95-96)
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java` for cash register operations
- [ ] Create `tests/test_kassenstand.py`

[ ] **Gutschein (Voucher/Gift Certificate)** - `../git/mysql/generateDB.sql` lines 156-166 (CR only - no update, no delete; SQL user has only INSERT grant)
- [ ] Add Gutschein, GutscheinPublic, GutscheinCreate models to `python/models.py` (no Update model)
- [ ] Create `python/routers/gutschein.py` (CR endpoints + redemption logic)
- [ ] GET /gutschein - List vouchers with filtering (by status, date range, restbetrag)
- [ ] GET /gutschein/{gutschein_id} - Get single voucher with full details
- [ ] POST /gutschein - Create new voucher (with unique gutschein_nr generation)
- [ ] POST /gutschein/{gutschein_id}/einloesen - Redeem voucher, link to verkauf_details (an INSERT in SQL, not a delete)
- [ ] GET /gutschein/ausstehend - List outstanding vouchers (restbetrag > 0)
- [ ] GET /gutschein/eingeloest - List fully redeemed vouchers
- [ ] GET /gutschein/teilingeloest - List partially redeemed vouchers
- [ ] Add business validation: restbetrag >= 0, proper voucher number generation
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/GutscheinEinloesenDialog.java`
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java` (articles 6 and 7 for voucher handling)
- [ ] Create `tests/test_gutschein.py`

[ ] **Anzahlung (Deposit/Installment Payment)** - `../git/mysql/generateDB.sql` lines 137-154 (CR only - no update, no delete; SQL user has only INSERT grants)
- [ ] Add Anzahlung, AnzahlungPublic, AnzahlungCreate models to `python/models.py` (no Update model)
- [ ] Add AnzahlungDetails, AnzahlungDetailsPublic models to `python/models.py`
- [ ] Create `python/routers/anzahlung.py` (CR endpoints + resolution logic)
- [ ] GET /anzahlung - List installments with filtering (by date range, status)
- [ ] GET /anzahlung/{anzahlung_id} - Get single installment with details
- [ ] POST /anzahlung - Create new installment payment
- [ ] POST /anzahlung/{anzahlung_id}/aufloesen - Resolve installment, link to sale (an INSERT in SQL, not a delete)
- [ ] GET /anzahlung/offen - List open installments (aufloesung_in_rech_nr IS NULL)
- [ ] GET /anzahlung/aufgeloest - List resolved installments
- [ ] GET /anzahlung/verkauf/{rechnungs_nr} - Get installments for a sale
- [ ] Add business validation: anzahlung_in_rech_nr must exist, prevent duplicate resolutions
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/AnzahlungAufloesDialog.java`
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/AnzahlungNeuDialog.java`
- [ ] Create `tests/test_anzahlung.py`

---

## 🟡 MEDIUM PRIORITY - Accounting System

### Phase 3: Settlement Tables

[ ] **Abrechnung Tag (Daily Settlement)** - `../git/mysql/generateDB.sql` lines 180-214 (CR only - no update, no delete; SQL user has only INSERT grants)
- [ ] Add AbrechnungTag, AbrechnungTagPublic, AbrechnungTagCreate models to `python/models.py`
- [ ] Add AbrechnungTagMwst, AbrechnungTagMwstPublic models to `python/models.py`
- [ ] Add AbrechnungTagTse, AbrechnungTagTsePublic models to `python/models.py`
- [ ] Create `python/routers/abrechnung_tag.py`
- [ ] GET /abrechnung/tag - List daily settlements with filtering
- [ ] GET /abrechnung/tag/{id} - Get single daily settlement with VAT details and TSE info
- [ ] POST /abrechnung/tag - Create daily settlement from sales in date range. This single endpoint performs the complete Tagesabschluss (VAT aggregation, updating kassenstand, automatic incremental TSE export, linking counting protocols) - no separate "finalize" step
- [ ] GET /abrechnung/tag/offen - Check for incomplete daily settlements
- [ ] GET /abrechnung/tag/heute - Get today's settlement (if exists)
- [ ] GET /abrechnung/tag/{date} - Get settlement for specific date
- [ ] Add business logic: VAT aggregation, cash register reconciliation
- [ ] Add automatic incremental TSE export as part of the settlement (mirrors `AbrechnungenTag.exportTSELog()`: by signature counter, fallback by TX number)
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/AbrechnungenTag.java`
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/Abrechnungen.java`
- [ ] Create `tests/test_abrechnung_tag.py`

[ ] **Abrechnung Monat (Monthly Settlement)** - `../git/mysql/generateDB.sql` lines 242-258 (at most CRD - no updates; SQL user has INSERT + DELETE, no UPDATE)
- [ ] Add AbrechnungMonat, AbrechnungMonatPublic, AbrechnungMonatCreate models to `python/models.py`
- [ ] Add AbrechnungMonatMwst, AbrechnungMonatMwstPublic models to `python/models.py`
- [ ] Create `python/routers/abrechnung_monat.py` (CR endpoints + internal delete-and-recreate)
- [ ] GET /abrechnung/monat - List monthly settlements
- [ ] GET /abrechnung/monat/{id} - Get single monthly settlement with VAT details
- [ ] POST /abrechnung/monat - Create monthly settlement from daily settlements; if one for the month already exists, delete it first and recreate (mirrors `AbrechnungenTag.deleteAbrechnungIfNeedBe()`)
- [ ] GET /abrechnung/monat/offen - Check for incomplete monthly settlements (past months without an AbrechnungMonat)
- [ ] GET /abrechnung/monat/{jahr}/{monat} - Get settlement for specific month
- [ ] Add business logic: aggregate daily settlements, calculate monthly totals
- [ ] Note: not user-initiated - endpoint is called by a cron job or the POS GUI in the background at startup (like the old Java POS)
- [ ] See reference: Various files in `../git/src/org/weltladen_bonn/pos/kasse/`
- [ ] Create `tests/test_abrechnung_monat.py`

[ ] **Abrechnung Jahr (Yearly Settlement)** - `../git/mysql/generateDB.sql` lines 269-285 (at most CRD - no updates; SQL user has INSERT + DELETE, no UPDATE)
- [ ] Add AbrechnungJahr, AbrechnungJahrPublic, AbrechnungJahrCreate models to `python/models.py`
- [ ] Add AbrechnungJahrMwst, AbrechnungJahrMwstPublic models to `python/models.py`
- [ ] Create `python/routers/abrechnung_jahr.py` (CR endpoints + internal delete-and-recreate)
- [ ] GET /abrechnung/jahr - List yearly settlements
- [ ] GET /abrechnung/jahr/{id} - Get single yearly settlement with VAT details
- [ ] POST /abrechnung/jahr - Create yearly settlement from monthly settlements; if one for the year already exists, delete it first and recreate (mirrors `AbrechnungenTag.deleteAbrechnungIfNeedBe()`)
- [ ] GET /abrechnung/jahr/offen - Check for incomplete yearly settlements (past years without an AbrechnungJahr)
- [ ] GET /abrechnung/jahr/{jahr} - Get settlement for specific year
- [ ] Add business logic: aggregate monthly settlements, calculate yearly totals
- [ ] Note: not user-initiated - endpoint is called by a cron job or the POS GUI in the background at startup
- [ ] Create `tests/test_abrechnung_jahr.py`

---

## 🟡 MEDIUM PRIORITY - Supporting Features

### Phase 4: Supporting Tables

[ ] **Zaehlprotokoll (Counting Protocol)** - `../git/mysql/generateDB.sql` lines 215-231 (CRU - no delete; SQL user has INSERT + UPDATE, no DELETE)
- [ ] Add Zaehlprotokoll, ZaehlprotokollPublic, ZaehlprotokollCreate models to `python/models.py`
- [ ] Add ZaehlprotokollDetails, ZaehlprotokollDetailsPublic models to `python/models.py`
- [ ] Create `python/routers/zaehlprotokoll.py`
- [ ] GET /zaehlprotokoll - List counting protocols
- [ ] GET /zaehlprotokoll/{id} - Get single counting protocol with details
- [ ] POST /zaehlprotokoll - Create new counting protocol
- [ ] PATCH /zaehlprotokoll/{id} - Update counting protocol (SQL user has UPDATE grant)
- [ ] GET /zaehlprotokoll/abrechnung/{abrechnung_tag_id} - Get protocols for settlement
- [ ] Add business validation: ensure protocol is balanced, aktiv flag handling
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/ZaehlprotokollDialog.java`
- [ ] Create `tests/test_zaehlprotokoll.py`

[ ] **Bestellung (Order/Purchase Order)** - `../git/mysql/generateDB.sql` lines 287-304
- [ ] Add Bestellung, BestellungPublic, BestellungCreate, BestellungUpdate models to `python/models.py`
- [ ] Add BestellungDetails, BestellungDetailsPublic, BestellungDetailsCreate models to `python/models.py`
- [ ] Create `python/routers/bestellung.py`
- [ ] GET /bestellung - List orders with filtering (by typ, date range, status)
- [ ] GET /bestellung/{bestell_nr} - Get single order with details (bestell_nr is unique; no typ in the path)
- [ ] POST /bestellung - Create new order
- [ ] PATCH /bestellung/{bestell_nr} - Update order
- [ ] DELETE /bestellung/{bestell_nr} - Cancel order
- [ ] POST /bestellung/{bestell_nr}/Position - Add position to order
- [ ] DELETE /bestellung/{bestell_nr}/Position/{position} - Remove position from order
- [ ] Add business validation: typ validation, position numbering, artikel_id validation
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/besteller/Bestellen.java`
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/besteller/Bestellung.java`
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/besteller/BestellAnzeige.java`
- [ ] Create `tests/test_bestellung.py`

---

## 🟡 MEDIUM PRIORITY - German Compliance (TSE)

### Phase 5: TSE Integration

[ ] **TSE Transaction Support** - `../git/mysql/generateDB.sql` lines 306-321
- [ ] Add TSETransaction, TSETransactionPublic, TSETransactionCreate models to `python/models.py`
- [ ] Create `python/routers/tse.py`
- [ ] GET /tse/transaction - List TSE transactions with filtering
- [ ] GET /tse/transaction/{transaction_id} - Get single TSE transaction
- [ ] POST /tse/transaction - Create TSE-signed transaction for sale
- [ ] GET /tse/status - Get TSE status and health
- [ ] POST /tse/init - Initialize TSE device
- [ ] POST /tse/certificates - Update TSE certificates
- [ ] GET /tse/transaction/verkauf/{rechnungs_nr} - Get TSE transaction for sale
- [ ] POST /tse/export/full - Full export of all TSE transaction data (mirrors `exportFullTransactionData()`), returns `.tar` file download
- [ ] POST /tse/export/partial - Partial export by TX number range / date range / signature counter (mirrors `exportPartialTransactionDataByTXNumber/ByDate/BySigCounter()`), returns `.tar` file download
- [ ] POST /tse/export/delete - Partial export up to a given signature counter, then delete stored TSE data up to the highest exported signature counter (mirrors the "TSE-Log exportieren und löschen" flow in `TSEStatus.java`, `deletePartialTransactionDataBySigCounter()`)
- [ ] Add automatic incremental TSE export as part of the daily settlement (see Abrechnung Tag)
- [ ] Wrap the TSE C API (cryptovision/D-Trust SEAPI - no Python library exists, only Java and C) via `ctypes` (first choice; `cffi` or Cython if needed) in a single adapter module `python/utils/tse_client.py`; fallback: small Java helper service running the SEAPI
- [ ] Add business validation: transaction signing, error handling
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/WeltladenTSE.java` (complete TSE implementation)
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/TSEInitDialog.java`
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/TSETarFile.java`
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/TSEStatus.java`
- [ ] Create `tests/test_tse.py`

---

## 🟡 MEDIUM PRIORITY - Business Logic Porting

### Phase 6: Core Business Logic from Java

[ ] **VAT Calculation Module** - Port from `../git/src/org/weltladen_bonn/pos/kasse/RechnungsGrundlage.java`
- [ ] Create `python/business/__init__.py`
- [ ] Create `python/business/vat_calculator.py`
- [ ] Implement `calculate_vat(brutto: Decimal, steuersatz: Decimal) -> Decimal` method
- [ ] Implement `calculate_mwst_values_in_rechnung(kassier_artikel: list) -> dict` method
- [ ] Implement `get_all_current_mwst_values_by_id() -> dict` method
- [ ] Add comprehensive unit tests in `tests/test_vat_calculator.py`
- [ ] Use Python's `decimal.Decimal` for precise financial calculations
- [ ] Handle rounding according to German tax laws (Round HALF_UP)

[ ] **Sale Workflow Enhancements** - Port from `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java` and `RechnungsGrundlage.java`
- [ ] Create `python/business/sale_workflow.py`
- [ ] Implement automatic VAT rate determination from articles
- [ ] Implement proper VAT calculation for mixed tax rate sales
- [ ] Implement financial value validation (no negative prices, valid decimals)
- [ ] Implement customer display integration logic
- [ ] Implement change calculation logic (see ecSchwelle = 10.00 in Kassieren.java line 44)
- [ ] Enhance existing `python/routers/verkauf.py` to use business logic
- [ ] Add comprehensive tests for sale workflow

[ ] **Storno Logic Enhancements** - Port from various Java files in `kasse/` package
- [ ] Create `python/business/storno_logic.py`
- [ ] Implement TSE transaction handling for storno operations
- [ ] Implement voucher handling in storno (partial refund to voucher)
- [ ] Implement installment handling in storno
- [ ] Add comprehensive validation for storno operations
- [ ] Implement prevention of storno for already storniert sales
- [ ] Enhance existing storno functionality in `python/routers/verkauf.py`
- [ ] Add tests for advanced storno scenarios

[ ] **Cash Register Operations** - Port from `../git/src/org/weltladen_bonn/pos/kasse/Kasse.java` and `Kassieren.java`
- [ ] Create `python/business/cash_register.py`
- [ ] Implement payment processing (cash, EC card)
- [ ] Implement change calculation (incl. EC payment threshold check: `ecSchwelle = 10.00` in `Kassieren.java` line 44)
- [ ] Implement end-of-day procedures
- [ ] Implement integration with kassenstand
- [ ] Implement training mode support (separate training_* tables)
- [ ] Add tests for cash register operations

---

## 🟢 LOW PRIORITY - Utilities and Enhancements

### Phase 7: Data Import/Export

[ ] **Import/Export Functionality**
- [ ] Create `python/routers/import_export.py`
- [ ] POST /import/artikel - Import articles from CSV/Excel
- [ ] GET /export/artikel - Export articles to CSV/Excel
- [ ] POST /import/bestellung - Import orders from CSV
- [ ] GET /export/abrechnung - Export accounting data to CSV/ODS
- [ ] Create `python/utils/csv_import.py` - CSV import utilities
- [ ] Create `python/utils/csv_export.py` - CSV export utilities
- [ ] Add support for OpenDocument Spreadsheet (ODS) format
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/ArtikelImport.java`
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/ArtikelExport.java`
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/kasse/CSVExport.java`
- [ ] Create `tests/test_import_export.py`

[ ] **Search and Filter Enhancements**
- [ ] Enhance all GET / endpoints with consistent filtering parameters
- [ ] Add full-text search capabilities where appropriate
- [ ] Add advanced pagination with cursor-based pagination
- [ ] Add consistent sorting options for all list endpoints
- [ ] Add filtering by date ranges, status, and other common criteria
- [ ] Implement search across multiple fields with AND/OR logic

[ ] **Validation Framework**
- [ ] Create `python/utils/validation.py`
- [ ] Implement comprehensive input validation for all endpoints
- [ ] Add proper error messages and HTTP status codes
- [ ] Add business rule validation (e.g., prevent future dates)
- [ ] Add foreign key constraint validation
- [ ] Add validation for all Decimal fields to prevent negative values where inappropriate

[ ] **Authentication and Authorization System** - **🔴 HIGH PRIORITY**
(replaces the current basic auth via only two MySQL users: kassenadmin/mitarbeiter)
- [ ] Add User model to `python/models.py` (new `user` table: user_id, username unique, password_hash, role admin/mitarbeiter, active)
- [ ] Add Anmeldung model to `python/models.py` (new `anmeldung` table: user_id, login_time, logout_time) - login auditing: register who logged in when
- [ ] Add nullable `user_id` FK column to transaction tables (verkauf, and as appropriate kassenstand, anzahlung, gutschein, zaehlprotokoll, abrechnung_tag, bestellung, tse_transaction) + one-time ALTER TABLE migration script in `../git/mysql/` - transaction attribution (existing rows stay NULL)
- [ ] Create `python/routers/auth.py` - Authentication endpoints (login, logout, token refresh)
- [ ] Create `python/routers/users.py` - Admin-only user management endpoints (create, update, deactivate users, reset passwords)
- [ ] Create `python/dependencies.py` - Authorization dependencies
- [ ] Create `python/utils/auth.py` - Authentication utilities (password hashing, token generation)
- [ ] Implement JWT or session-based authentication with proper token expiration
- [ ] Add role-based authorization (admin vs. regular user)
- [ ] Protect sensitive endpoints: MwSt POST/PUT/PATCH/DELETE, Pfand POST/PUT/PATCH/DELETE, user management
- [ ] Add secure password hashing (bcrypt or similar)
- [ ] Add rate limiting for authentication endpoints
- [ ] Transport security on the LAN: HTTPS with an internal (self-signed) CA certificate (e.g. mkcert; TLS via Caddy/nginx or uvicorn) - recommended; plain HTTP only acceptable on a managed, isolated LAN segment (see IMPLEMENTATION_PLAN.md Phase 7.4 for pitfalls)
- [ ] See reference: `../git/src/org/weltladen_bonn/pos/DBConnection.java` (password dialog) - to be replaced by API-level user accounts
- [ ] Add custom validators for business-specific constraints

---

## 📚 Documentation Tasks

[ ] **API Documentation Enhancement**
- [ ] Ensure all endpoints have proper docstrings for auto-generated docs
- [ ] Add examples for all endpoints
- [ ] Add response schemas for all endpoints
- [ ] Add error response schemas
- [ ] Create usage examples and tutorials

[ ] **Code Documentation**
- [ ] Add comprehensive docstrings for all functions and classes
- [ ] Add module-level docstrings for all new modules
- [ ] Add inline comments for complex business logic
- [ ] Create architecture overview documentation

[ ] **Migration Documentation**
- [ ] Create migration guide from Java POS to API
- [ ] Document API endpoints and their Java POS equivalents
- [ ] Create data migration instructions
- [ ] Document breaking changes and compatibility notes

[ ] **Setup and Deployment**
- [ ] Create comprehensive setup instructions
- [ ] Document database configuration
- [ ] Document environment variables and configuration options
- [ ] Create deployment guide for production

[ ] **Database Schema Documentation**
- [ ] Create complete schema reference documentation
- [ ] Document all tables, fields, relationships, and constraints
- [ ] Create ER diagram for the database

---

## 🧪 Testing Tasks

### Unit Tests

- [x] Create `tests/test_mwst.py` - MwSt CRUD and validation tests
- [x] Create `tests/test_pfand.py` - Pfand CRUD and validation tests
- [ ] Create `tests/test_kassenstand.py` - Cash register balance tests
- [ ] Create `tests/test_gutschein.py` - Voucher management tests
- [ ] Create `tests/test_anzahlung.py` - Installment payment tests
- [ ] Create `tests/test_abrechnung_tag.py` - Daily settlement tests
- [ ] Create `tests/test_abrechnung_monat.py` - Monthly settlement tests
- [ ] Create `tests/test_abrechnung_jahr.py` - Yearly settlement tests
- [ ] Create `tests/test_zaehlprotokoll.py` - Counting protocol tests
- [ ] Create `tests/test_bestellung.py` - Order management tests
- [ ] Create `tests/test_tse.py` - TSE integration tests
- [ ] Create `tests/test_auth.py` - Authentication/authorization tests
- [ ] Create `tests/test_vat_calculator.py` - Business logic tests
- [ ] Create `tests/test_sale_workflow.py` - Sale workflow tests
- [ ] Create `tests/test_storno_logic.py` - Storno logic tests
- [ ] Create `tests/test_import_export.py` - Import/export functionality tests

### Integration Tests

- [ ] Test complete workflow: Article creation → Sale creation → Storno
- [ ] Test complete workflow: Cash register balance → Sale → Settlement
- [ ] Test complete workflow: Voucher creation → Sale with voucher → Voucher redemption
- [ ] Test complete workflow: Installment creation → Sale → Installment resolution
- [ ] Test cross-entity relationships and constraints
- [ ] Test database constraint violations
- [ ] Test concurrent operations and race conditions

### Test Coverage Target

- [ ] Achieve minimum 80% code coverage
- [ ] All critical paths tested
- [ ] All business logic validated
- [ ] All edge cases covered
- [ ] All error conditions tested

---

## 🎯 Final Success Criteria Checklist

### Core Functionality

- [ ] All database tables have corresponding models and endpoints
- [ ] Bookkeeping integrity: no update/delete endpoints for immutable tables (verkauf, kassenstand, gutschein, anzahlung, abrechnung_tag)
- [ ] All business logic from Java POS is ported to API
- [ ] Comprehensive validation and error handling implemented
- [ ] Per-user accounts with login auditing and transaction attribution
- [ ] All existing Java POS functionality available through API
- [ ] Proper separation of concerns (business logic vs. API routes)

### Quality Assurance

- [ ] 80%+ test coverage achieved
- [ ] All endpoints properly documented
- [ ] All code properly documented with docstrings
- [ ] All error conditions handled gracefully
- [ ] Performance optimized for production use

### Documentation

- [ ] Complete API documentation available via /docs and /redoc
- [ ] Migration guide created
- [ ] Setup instructions created
- [ ] Database schema documented
- [ ] Architecture documented

### Production Readiness
- [ ] Working integration with existing database
- [ ] Ready for frontend client development
- [ ] Ready for production deployment
- [ ] All existing functionality preserved and enhanced
- [ ] All security considerations addressed

---

## 📊 Summary Statistics

### Models Status
- **Total Database Tables**: 21 main tables + 12 training tables = 33 tables
- **Models Implemented**: 9 table models
- **Models Missing**: 24 table models (need to add to python/models.py)

### Endpoints Status  
- **Existing Routers**: 6 routers with partial CRUD
- **Routers Needing Completion**: 2 routers (mwst, pfand) need admin-only CRUD with authentication
- **Routers to Create**: 10 new routers for missing tables (kassenstand, gutschein, anzahlung, abrechnung_tag, abrechnung_monat, abrechnung_jahr, zaehlprotokoll, bestellung, tse, import_export) + auth + users router; deliberately no dedicated routers for verkauf_mwst/verkauf_details
- **Security**: Authentication and authorization system with per-user accounts, login auditing and transaction attribution needed

### Business Logic Status
- **Java POS Classes**: 107 Java files in `../git/src/org/weltladen_bonn/pos/`
- **Business Logic Ported**: Minimal (basic CRUD, article versioning, storno)
- **Business Logic to Port**: ~95% of Java business logic still needs porting

### Testing Status
- **Test Files**: 2 test files exist
- **Test Coverage**: Low (only basic storno functionality tested)
- **Target Coverage**: 80%+

---

## 🚀 Recommended Next Steps

1. **Start with Phase 1** - Complete existing endpoints for MwSt and Pfand with admin authorization; Verkauf stays update-free by design (2-3 days)
2. **Implement Authentication** - User accounts (new `user` table), login auditing (`anmeldung` table), transaction attribution (`user_id` columns), authorization (2-3 days)
3. **Proceed to Phase 2** - Add core business tables, starting with Kassenstand (3-4 days)
4. **Continue with Phase 3** - Add accounting system (3-5 days)
5. **Add supporting features** - Zaehlprotokoll, Bestellung, TSE (2-3 days)
6. **Port business logic** - VAT calculator, sale workflow, storno logic (2-3 days)
7. **Add utilities** - Import/export, validation, search (1-2 days)
8. **Comprehensive testing** - Achieve 80%+ coverage (ongoing)
9. **Documentation** - Complete all documentation (ongoing)

---

## 📝 Notes and Assumptions

- Database schema is available in `../git/mysql/generateDB.sql`
- Existing data can be used as-is, except for one planned schema migration: new `user`/`anmeldung` tables + nullable `user_id` columns on transaction tables (for login auditing and transaction attribution)
- Java POS business logic should be ported faithfully but adapted for API context
- Training mode tables (training_*) can be implemented later if needed
- TSE integration may require external TSE device or service for full functionality
- The TSE in use (cryptovision/D-Trust SEAPI) has no Python library, only Java and C APIs; the API wraps the C library via `ctypes`/`cffi` in an adapter module (see Phase 5)
- Some Java UI-specific logic may not need to be ported (only business logic)

---

*This TODO list will be updated as implementation progresses. Check the IMPLEMENTATION_PLAN.md for detailed implementation guidance for each item.*