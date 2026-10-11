# Weltladenkasse API - Implementation Plan

## Overview

This document outlines the comprehensive implementation plan to complete the FastAPI backend for the Weltladenkasse POS system. The goal is to port all business logic from the existing Java Swing POS application (`../git/src/org/weltladen_bonn/pos/`) to the new Python FastAPI backend.

**Design principle**: The API must respect bookkeeping integrity and the SQL grants in `../git/mysql/grants.sql`. Where the SQL user (`mitarbeiter`) has no UPDATE or DELETE grant on a table, the API does not expose update or delete endpoints for it. Corrections are done by adding new entries (e.g. Storno), not by modifying existing ones.

## Current Status Summary

### ✅ Already Implemented
- **Database Models**: All core tables have SQLModel definitions in `python/models.py`
- **CRUD Operations**: Most major entities have basic CRUD functionality
- **Business Logic**: Some core logic like article versioning and storno operations
- **API Structure**: Clean FastAPI structure with proper routing

### 🎯 What Needs to be Done
- Complete missing endpoints for existing models (CR, CRU or CRD per table, see Phases 1-4)
- Add missing database table models and endpoints
- Port business logic from Java POS classes
- Add validation, security, and error handling
- Comprehensive test coverage

---

## Phase 1: Complete Existing CRUD Operations (High Priority)

### 1.1 MwSt (VAT/Tax) - Add Admin-Only Operations
**Current**: Read-only endpoints in `python/routers/mwst.py`  
**Target**: Read-only for regular users + Admin-only CRUD with authorization

**Rationale**: VAT rates change very rarely and should not be modifiable by regular users. Only authorized administrators should be able to create, update, or delete VAT rates.

**Files to modify:**
- `python/routers/mwst.py` - Add POST, PUT/PATCH, DELETE endpoints with admin authorization
- Add validation for mwst_satz (must be between 0 and 1)
- Add business logic for VAT rate constraints
- **Add authentication/authorization layer** (see Phase 7.4 below)

**Java reference**: VAT-related logic in `../git/src/org/weltladen_bonn/pos/kasse/RechnungsGrundlage.java`

### 1.2 Pfand (Deposit) - Add Admin-Only Operations  
**Current**: Read-only endpoints in `python/routers/pfand.py`  
**Target**: Read-only for regular users + Admin-only CRUD with authorization

**Rationale**: Deposit rates/items change very rarely and should not be modifiable by regular users. Only authorized administrators should be able to create, update, or delete deposit items.

**Files to modify:**
- `python/routers/pfand.py` - Add POST, PUT/PATCH, DELETE endpoints with admin authorization
- Add validation for artikel_id (must reference existing article)
- Add business logic for deposit value calculation
- **Add authentication/authorization layer** (see Phase 7.4 below)

**Java reference**: Deposit logic in various files in `../git/src/org/weltladen_bonn/pos/`

### 1.3 Verkauf (Sale) - No Update Functionality (By Design)
**Current**: Create, Read, Storno in `python/routers/verkauf.py`  
**Target**: Keep as-is. **No update endpoint for the `verkauf` table will ever be added.**

**Rationale**: Bookkeeping integrity requires that entries in the `verkauf` table are immutable once created. Corrections are made by performing a Storno (reversing entry via `POST /verkauf/{rechnungs_nr}/storno`, which creates a new sale referencing the original via `storno_von`) and, if needed, by creating a new corrected sale afterwards. This CR + Storno pattern is complete; a full CRUD would make no sense here and would endanger the consistency of the books.

**Files to modify:** None. (The Storno logic itself is enhanced in Phase 6.3 without changing the endpoint surface.)

### 1.4 Related Tables: No Dedicated Endpoints
**Decision**: There will be **no separate endpoints** for `verkauf_mwst` and `verkauf_details`. Entries in these tables must always exist together with an entry in `verkauf`, so they are modified exclusively as "side-effects" of the `python/routers/verkauf.py` endpoints (sale creation, storno). No changes needed - keep things as they are.

---

## Phase 2: Add Missing Core Business Tables (High Priority)

### 2.1 Kassenstand (Cash Register Balance)
**Priority**: 🔴 HIGH - Essential for POS operations

**Database table**: `kassenstand` (lines 125-135 in `../git/mysql/generateDB.sql`)

**Model fields:**
- kassenstand_id (PK)
- buchungsdatum (DATETIME, not null)
- neuer_kassenstand (DECIMAL(13,2), not null)
- manuell (BOOLEAN, default FALSE)
- entnahme (BOOLEAN, default FALSE)
- rechnungs_nr (FK to verkauf, nullable)
- kommentar (VARCHAR(70))

**Required endpoints (CR only - no update, no delete; the SQL user has only INSERT grant on `kassenstand`):**
- GET /kassenstand - List cash register balances with filtering, we need a filter "rechnungen=true|false" that shows rechnungen (default false, rechnungen not shown, which means there is a "WHERE manuell = TRUE" filter on the query)
- GET /kassenstand/{id} - Get single entry
- POST /kassenstand - Create new cash register entry
- GET /kassenstand/aktuell - Get current cash register balance

**Business logic from Java:**
- Cash register balance tracking in `../git/src/org/weltladen_bonn/pos/kasse/Kasse.java`
- Balance validation and change calculation in `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java`
- Integration with sales and storno operations
- Kassenstand setting and view in `../git/src/org/weltladen_bonn/pos/kasse/Kassenstand.java`
- Kassenstand table must be updated as part of the AbrechnungTag process (see below)

**Files to create:**
- `python/models.py` - Add Kassenstand models
- `python/routers/kassenstand.py` - Create + Read endpoints (CR, no U and no D)
- `tests/test_kassenstand.py` - Tests for kassenstand functionality

### 2.2 Gutschein (Voucher/Gift Certificate)
**Priority**: 🟡 MEDIUM - Important for customer loyalty

**Database table**: `gutschein` (lines 156-166 in `../git/mysql/generateDB.sql`)

**Model fields:**
- gutschein_id (PK)
- gutschein_nr (UNIQUE, not null)
- datum (DATETIME, not null)
- gutschein_in_vd_id (FK to verkauf_details, nullable)
- einloesung_in_vd_id (FK to verkauf_details, nullable)
- restbetrag (DECIMAL(13,2), not null)

**Required endpoints (CR only - no update, no delete; the SQL user has only INSERT grant on `gutschein`):**
- GET /gutschein - List vouchers with filtering
- GET /gutschein/{id} - Get single voucher
- POST /gutschein - Create new voucher
- POST /gutschein/{id}/einloesen - Redeem voucher (link to sale detail; technically an INSERT in SQL, not a delete)
- GET /gutschein/ausstehend - List outstanding vouchers
- GET /gutschein/eingeloest - List redeemed vouchers

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/kasse/GutscheinEinloesenDialog.java` - Voucher redemption logic
- Voucher creation in `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java` (articles 6 and 7 are voucher-related)
- Balance tracking and validation

**Files to create:**
- `python/models.py` - Add Gutschein models
- `python/routers/gutschein.py` - Create + Read endpoints + redemption logic (no update, no delete)

### 2.3 Anzahlung (Deposit/Installment Payment)
**Priority**: 🟡 MEDIUM - Important for installment sales

**Database tables**: 
- `anzahlung` (lines 137-145 in `../git/mysql/generateDB.sql`)
- `anzahlung_details` (lines 146-154 in `../git/mysql/generateDB.sql`)

**Model fields (Anzahlung):**
- anzahlung_id (PK)
- datum (DATETIME, not null)
- anzahlung_in_rech_nr (FK to verkauf, not null)
- aufloesung_in_rech_nr (FK to verkauf, nullable)

**Model fields (AnzahlungDetails):**
- ad_id (PK)
- rechnungs_nr (FK to verkauf, not null)
- vd_id (FK to verkauf_details, not null)
- ges_preis (DECIMAL(13,2), not null)

**Required endpoints (CR only - no update, no delete; the SQL user has only INSERT grants on `anzahlung*`):**
- GET /anzahlung - List installments
- GET /anzahlung/{id} - Get single installment
- POST /anzahlung - Create new installment
- POST /anzahlung/{id}/aufloesen - Resolve installment (technically an INSERT in SQL, not a delete)
- GET /anzahlung/offen - List open installments
- GET /anzahlung/aufgeloest - List resolved installments

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/kasse/AnzahlungAufloesDialog.java` - Installment resolution
- `../git/src/org/weltladen_bonn/pos/kasse/AnzahlungNeuDialog.java` - Installment creation
- Integration with sales workflow in `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java`

**Files to create:**
- `python/models.py` - Add Anzahlung and AnzahlungDetails models
- `python/routers/anzahlung.py` - Create + Read endpoints + resolution logic (no update, no delete)

---

## Phase 3: Add Accounting/Settlement Tables (Medium Priority)

### 3.1 Abrechnung Tag (Daily Settlement)
**Priority**: 🔴 HIGH - Essential for accounting

**Database tables**:
- `abrechnung_tag` (lines 180-193 in `../git/mysql/generateDB.sql`)
- `abrechnung_tag_mwst` (lines 194-201 in `../git/mysql/generateDB.sql`)
- `abrechnung_tag_tse` (lines 202-214 in `../git/mysql/generateDB.sql`)

**Required endpoints (CR only - no update, no delete; the SQL user has only INSERT grants on `abrechnung_tag*`):**
- GET /abrechnung/tag - List daily settlements
- GET /abrechnung/tag/{id} - Get single daily settlement
- POST /abrechnung/tag - Create daily settlement. This single endpoint performs the complete Tagesabschluss (aggregating the day's sales, VAT aggregation, updating kassenstand, running the automatic incremental TSE export, linking counting protocols) - there is no separate "finalize" step.
- GET /abrechnung/tag/offen - Check for incomplete daily settlements

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/kasse/AbrechnungenTag.java` - Daily settlement logic (incl. `exportTSELog()` for the automatic TSE export)
- `../git/src/org/weltladen_bonn/pos/kasse/Abrechnungen.java` - Base settlement functionality
- VAT aggregation and reporting
- TSE integration (see Phase 5.1: the Tagesabschluss triggers a partial TSE export by signature counter, with fallback by TX number)

**Files to create:**
- `python/models.py` - Add AbrechnungTag, AbrechnungTagMwst, AbrechnungTagTse models
- `python/routers/abrechnung_tag.py` - Create + Read endpoints

### 3.2 Abrechnung Monat (Monthly Settlement)
**Priority**: 🟡 MEDIUM - For monthly accounting

**Database tables**:
- `abrechnung_monat` (lines 242-250 in `../git/mysql/generateDB.sql`)
- `abrechnung_monat_mwst` (lines 251-258 in `../git/mysql/generateDB.sql`)

**Required endpoints (at most CRD - no updates, since the SQL user has no UPDATE grant; see note on the DELETE grant below):**
- GET /abrechnung/monat - List monthly settlements
- GET /abrechnung/monat/{id} - Get single monthly settlement
- POST /abrechnung/monat - Create monthly settlement (from daily settlements). If a settlement for the month already exists, it is deleted first and recreated (mirrors the Java behavior, see note below).
- GET /abrechnung/monat/offen - Check for incomplete monthly settlements: returns the months that have already passed but do not yet have an AbrechnungMonat

**Note - not user-initiated**: In the Java POS, AbrechnungMonat is not created from user initiative but automatically: when the user opens the POS software, it checks whether new months have started/passed that do not yet have a monthly settlement and creates them automatically. The API itself does not act on its own, so this endpoint is meant to be called by:
- a cron job on the server, or
- the POS GUI in the background at startup (like the old Java POS), which can use `GET /abrechnung/monat/offen` to determine whether anything is due.

**Note - DELETE grant**: The SQL user has DELETE grant on `kasse.abrechnung_monat` (and `abrechnung_monat_mwst`). Checked in the Java code: `AbrechnungenTag.deleteAbrechnungIfNeedBe()` (lines 1004-1006, 1322 in `AbrechnungenTag.java`) deletes an existing monthly/yearly settlement for a period before recreating it (i.e. redoing a settlement, e.g. after a correction). This is why the DELETE grant exists. The API therefore only needs DELETE as an internal step of re-running `POST /abrechnung/monat` (delete existing + recreate, in one transaction), not as a standalone endpoint.

**Files to create:**
- `python/models.py` - Add AbrechnungMonat, AbrechnungMonatMwst models
- `python/routers/abrechnung_monat.py` - Create + Read endpoints (+ internal delete-and-recreate)

### 3.3 Abrechnung Jahr (Yearly Settlement)
**Priority**: 🟡 LOW - For yearly accounting

**Database tables**:
- `abrechnung_jahr` (lines 269-277 in `../git/mysql/generateDB.sql`)
- `abrechnung_jahr_mwst` (lines 278-285 in `../git/mysql/generateDB.sql`)

**Required endpoints (at most CRD - no updates, since the SQL user has no UPDATE grant; see note on the DELETE grant below):**
- GET /abrechnung/jahr - List yearly settlements
- GET /abrechnung/jahr/{id} - Get single yearly settlement
- POST /abrechnung/jahr - Create yearly settlement (from monthly settlements). If a settlement for the year already exists, it is deleted first and recreated (mirrors the Java behavior).
- GET /abrechnung/jahr/offen - Check for incomplete yearly settlements: returns the past years that do not yet have an AbrechnungJahr

**Note - not user-initiated**: Like the monthly settlement, this is not created from user initiative in the Java POS; it happens automatically. The endpoint is meant to be called by a cron job or by the POS GUI in the background at startup (which can use `GET /abrechnung/jahr/offen` to determine whether anything is due).

**Note - DELETE grant**: Same as for the monthly settlement: the SQL user has DELETE grant on `kasse.abrechnung_jahr` (and `abrechnung_jahr_mwst`), used by `AbrechnungenTag.deleteAbrechnungIfNeedBe()` to delete an existing yearly settlement before recreating it. DELETE is only needed as an internal step of re-running `POST /abrechnung/jahr`, not as a standalone endpoint.

**Files to create:**
- `python/models.py` - Add AbrechnungJahr, AbrechnungJahrMwst models
- `python/routers/abrechnung_jahr.py` - Create + Read endpoints (+ internal delete-and-recreate)

---

## Phase 4: Add Supporting Tables (Medium-Low Priority)

### 4.1 Zaehlprotokoll (Counting Protocol)
**Priority**: 🟡 MEDIUM - For cash counting and reconciliation

**Database tables**:
- `zaehlprotokoll` (lines 215-223 in `../git/mysql/generateDB.sql`)
- `zaehlprotokoll_details` (lines 224-231 in `../git/mysql/generateDB.sql`)

**Required endpoints (CRU - no delete, since the SQL user has no DELETE grant):**
- GET /zaehlprotokoll - List counting protocols
- GET /zaehlprotokoll/{id} - Get single protocol
- POST /zaehlprotokoll - Create new counting protocol
- PATCH /zaehlprotokoll/{id} - Update an existing counting protocol (the SQL user has UPDATE grant)
- GET /zaehlprotokoll/abrechnung/{abrechnung_tag_id} - Get protocols for settlement

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/kasse/ZaehlprotokollDialog.java` - Counting protocol creation

**Files to create:**
- `python/models.py` - Add Zaehlprotokoll, ZaehlprotokollDetails models
- `python/routers/zaehlprotokoll.py` - Create, Read, Update endpoints (CRU, no D)

### 4.2 Bestellung (Order/Purchase Order)
**Priority**: 🟢 LOW - For supplier ordering

**Database tables**:
- `bestellung` (lines 287-294 in `../git/mysql/generateDB.sql`)
- `bestellung_details` (lines 295-304 in `../git/mysql/generateDB.sql`)

**Required endpoints (full CRUD - the SQL user has INSERT, UPDATE, DELETE grants on `bestellung*`):**
- GET /bestellung - List orders
- GET /bestellung/{bestell_nr} - Get single order (`bestell_nr` is unique; there cannot be multiple orders with different `typ` under the same bestell_nr, so no `typ` in the endpoint path)
- POST /bestellung - Create new order
- PATCH /bestellung/{bestell_nr} - Update order
- DELETE /bestellung/{bestell_nr} - Delete order

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/besteller/Bestellen.java` - Order creation
- `../git/src/org/weltladen_bonn/pos/besteller/Bestellung.java` - Order management
- `../git/src/org/weltladen_bonn/pos/besteller/BestellAnzeige.java` - Order display

**Files to create:**
- `python/models.py` - Add Bestellung, BestellungDetails models
- `python/routers/bestellung.py` - CRUD endpoints

---

## Phase 5: Add TSE Integration (Medium Priority for German Compliance)

### 5.1 TSE Transaction Support
**Priority**: 🔴 HIGH - Legal requirement for German cash registers

**Database table**: `tse_transaction` (lines 306-321 in `../git/mysql/generateDB.sql`) - local log of TSE operations (transaction number, signature counter, signature in base64, process data)

**Required endpoints:**
- GET /tse/transaction - List TSE transactions
- GET /tse/transaction/{id} - Get single transaction
- POST /tse/transaction - Create TSE-signed transaction
- GET /tse/status - Get TSE status
- POST /tse/init - Initialize TSE
- POST /tse/export/full - Full export of all TSE transaction data (mirrors `exportFullTransactionData()` in Java)
- POST /tse/export/partial - Partial export, with a request body selecting the criterion:
  - by TX number range (mirrors `exportPartialTransactionDataByTXNumber(filename, startTXNumber, endTXNumber, maxRecords)`)
  - by date range (mirrors `exportPartialTransactionDataByDate(filename, startDate, endDate, maxRecords)`)
  - by signature counter (mirrors `exportPartialTransactionDataBySigCounter(filename, lastExcludedSignatureCounter, maxRecords)`)
- POST /tse/export/delete - Partial export (up to a given signature counter) followed by deletion of the stored TSE data up to the highest exported signature counter (mirrors the "TSE-Log exportieren und löschen" flow in `TSEStatus.java`, which calls `deletePartialTransactionDataBySigCounter()`)

The export endpoints return the generated `.tar` file as a file download (in Java the file is written to a local export directory, e.g. `tse_export_<date>_Sig_from_X_to_Y.tar`).

**Automatic export during daily settlement**: The Tagesabschluss (Phase 3.1) automatically performs an incremental partial TSE export by signature counter (since the previous settlement), with a fallback by TX number - see `AbrechnungenTag.exportTSELog()` (lines 1097-1145 in `AbrechnungenTag.java`). This integration must be part of the `POST /abrechnung/tag` process.

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/kasse/WeltladenTSE.java` - Complete TSE integration (incl. all export/delete methods)
- `../git/src/org/weltladen_bonn/pos/kasse/TSEStatus.java` - Manual export dialogs ("TSE-Log exportieren", "TSE-Log exportieren und löschen")
- `../git/src/org/weltladen_bonn/pos/kasse/TSEInitDialog.java` - TSE initialization
- `../git/src/org/weltladen_bonn/pos/kasse/TSETarFile.java` - TSE file handling

**Open question to check**: The Java export methods talk to the TSE hardware via the Java TSE library. The API needs a Python TSE library (or equivalent mechanism) that can perform the same operations (export, delete stored data). Availability of such a library for the TSE in use must be verified.

**Files to create:**
- `python/models.py` - Add TSETransaction model
- `python/routers/tse.py` - TSE transaction + export endpoints

---

## Phase 6: Port Core Business Logic from Java POS

### 6.1 VAT Calculation and Aggregation
**Source**: `../git/src/org/weltladen_bonn/pos/kasse/RechnungsGrundlage.java`  
**Target**: Business logic module in Python

**Key methods to port:**
- `calculateVAT(BigDecimal brutto, BigDecimal steuersatz)` - Calculate VAT amount
- `calculateMwStValuesInRechnung()` - Aggregate VAT per tax rate
- `getAllCurrentMwstValuesByID()` - Get current VAT values by ID

**Implementation:**
- Create `python/business/vat_calculator.py`
- Use Python's `Decimal` for precise financial calculations
- Handle rounding according to German tax laws
- Add comprehensive unit tests

### 6.2 Sale Creation with Proper VAT Handling
**Source**: `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java`, `../git/src/org/weltladen_bonn/pos/kasse/RechnungsGrundlage.java`  
**Target**: Enhance existing sale creation

**Key functionality:**
- Automatic VAT rate determination from articles
- Proper VAT calculation for mixed tax rate sales
- Validation of financial values
- Integration with voucher and discount handling
- Customer display integration logic

**Implementation:**
- Enhance `python/routers/verkauf.py` with VAT calculation
- Add validation for financial calculations
- Add business logic module for sale workflow

### 6.3 Advanced Storno Logic
**Source**: Various Java files in `../git/src/org/weltladen_bonn/pos/kasse/`  
**Target**: Enhance existing storno functionality

**Current implementation**: Basic storno with inverted entries  
**Missing functionality:**
- TSE transaction handling for storno
- Voucher handling in storno
- Installment handling in storno
- Comprehensive validation for storno operations
- Prevent storno of already storniert sales

### 6.4 Cash Register Operations
**Source**: `../git/src/org/weltladen_bonn/pos/kasse/Kasse.java`, `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java`  
**Target**: Business logic for cash register operations

**Key functionality:**
- Payment processing (cash, EC card)
- EC payment threshold check (`Kassieren.java` line 44: `private final BigDecimal ecSchwelle = new BigDecimal("10.00");` - warning that the total is below 10.00 when paying by EC card, see `Kassieren.java` line 2512)
- End-of-day procedures
- Integration with kassenstand
- Training mode support

(No cash drawer management: there is no automatic cash drawer opened via the POS software.)

---

## Phase 7: Add Utility and Helper Functionality

### 7.1 Import/Export Functionality
**Priority**: 🟢 LOW - For data migration and backup

**Required endpoints:**
- POST /import/artikel - Import articles from CSV/Excel
- GET /export/artikel - Export articles to CSV/Excel
- POST /import/bestellung - Import orders
- GET /export/abrechnung - Export accounting data

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/ArtikelImport.java` - Article import functionality
- `../git/src/org/weltladen_bonn/pos/ArtikelExport.java` - Article export functionality
- `../git/src/org/weltladen_bonn/pos/kasse/CSVExport.java` - CSV export for various data

**Files to create:**
- `python/routers/import_export.py` - Import/export endpoints
- `python/utils/csv_import.py` - CSV import utilities
- `python/utils/csv_export.py` - CSV export utilities

### 7.2 Search and Filter Enhancements
**Priority**: 🟢 LOW - Improve usability

**Enhancements:**
- Advanced filtering for all list endpoints
- Full-text search capabilities
- Pagination improvements
- Sorting options

### 7.3 Validation and Error Handling
**Priority**: 🔴 HIGH - Essential for data integrity

**Enhancements:**
- Comprehensive input validation for all endpoints
- Proper error messages and HTTP status codes
- Business rule validation (e.g., prevent future dates)
- Foreign key constraint validation
- Add validation for all Decimal fields to prevent negative values where inappropriate

### 7.4 Authentication and Authorization
**Priority**: 🔴 HIGH - Essential for security

**Current state:**
- Authentication is very basic and done entirely with MySQL users: there are only two - `kassenadmin` (full privileges) and `mitarbeiter` (restricted privileges, see `../git/mysql/grants.sql`).
- The Java POS asks for the DB password (`../git/src/org/weltladen_bonn/pos/DBConnection.java`, password dialog).
- There are no per-user accounts, no record of who logged in when, and no way to look up which transaction was done by which person.

**Target: proper user account management**
- **Per-user accounts**: Every user has their own account and password. This requires a new `user` table (does not exist in the current schema): `user_id`, `username` (unique), `password_hash` (bcrypt), `role` (`admin` or `mitarbeiter`), `active`.
- **Roles**: admin vs. regular user (mitarbeiter). Sensitive operations (MwSt/Pfand CRUD, user management) are admin-only.
- **Login auditing**: A new `anmeldung` table (`user_id` FK, `login_time`, `logout_time`) registers who logged in when, so logins can be looked up later.
- **Transaction attribution**: Add a nullable `user_id` FK column to the transaction tables (`verkauf`, and as appropriate `kassenstand`, `anzahlung`, `gutschein`, `zaehlprotokoll`, `abrechnung_tag`, `bestellung`, `tse_transaction` - exact list to be decided) so it can later be looked up which transaction was done by which user. Existing rows stay NULL (they cannot be attributed retroactively). This requires a one-time `ALTER TABLE` migration (SQL script in `../git/mysql/`).
- **Session management**: The login endpoint issues a JWT/session token carrying the user's identity and role; proper token expiration; logout records the logout time.
- **MySQL side**: The API process connects with the service account(s) (e.g. `kassenadmin`); per-user authorization is enforced at the API level, not by switching MySQL users.

**Required Implementation:**
- Add authentication middleware/dependencies for FastAPI
- Add authorization system with user roles (admin vs. regular user)
- Protect sensitive endpoints (MwSt POST/PUT/PATCH/DELETE, Pfand POST/PUT/PATCH/DELETE, user management)
- Add admin-only user management endpoints (create, update, deactivate users, reset passwords)
- Implement JWT or session-based authentication

**Files to create:**
- `python/routers/auth.py` - Authentication endpoints (login, logout, token refresh)
- `python/routers/users.py` - Admin-only user management endpoints
- `python/dependencies.py` - Dependency for authorization checks
- `python/models.py` - Add User and Anmeldung models (new tables) + `user_id` columns on transaction tables
- `python/utils/auth.py` - Authentication utilities (password hashing, token generation)
- SQL migration script (new `user`/`anmeldung` tables + `user_id` columns) in `../git/mysql/`

**Security considerations:**
- Use secure password hashing (bcrypt or similar)
- Implement proper token expiration
- Add rate limiting for authentication endpoints
- Transport security on the LAN: see below

**Transport security: HTTPS on the local network**

The API and Web App (GUI) will only be accessible on the local network. Two viable options:

*Option 1 (recommended): HTTPS with an internal (self-signed) certificate*
- Generate a small internal CA plus a server certificate for the server's LAN hostname. Easiest with `mkcert` (creates a local CA, signs the certificate, and provides the CA cert for client trust), or manually with `openssl`.
- Terminate TLS in a small reverse proxy (Caddy or nginx) in front of the FastAPI app, or configure uvicorn directly with the certificate.
- Install the internal CA certificate on the client devices (POS PCs, possibly mobile devices), which then trust the server.
- Note: public CAs (Let's Encrypt) do not work on a private LAN because the domain cannot be publicly verified - but a self-signed internal CA works perfectly fine within the LAN.

*Option 2: plain HTTP on a trusted, isolated LAN*

Security pitfalls of using unencrypted HTTP within a local network:
- All traffic is in clear text: any device that can sniff the network segment (any device on the same flat network, ARP spoofing / man-in-the-middle, switch port mirroring) can read passwords, session tokens and all sales data.
- An active attacker on the LAN can forge or tamper with API requests (no integrity protection of the channel).
- The risk is significantly higher if customer/guest WiFi shares the network segment with the POS, if the POS runs over WiFi (wireless eavesdropping reaches beyond the shop), or if an infected/compromised device is connected to the network.
- If staying on plain HTTP, mitigations: dedicated VLAN/segment for the POS devices (no access from guest/customer networks), wired POS connections, firewall rules restricting API access to the POS devices, and still keep strong application-level authentication with auditing.

**Recommendation**: Use HTTPS with an internal CA certificate (Option 1) - the setup cost is small (one-time) and it removes the clear-text pitfalls entirely. Plain HTTP (Option 2) is only acceptable if the LAN is a managed, isolated segment without guest access.

**Java reference**: The existing (basic) authentication in the Java POS is in `../git/src/org/weltladen_bonn/pos/DBConnection.java` (password dialog) - to be replaced by the API-level user accounts described above.

---

## Implementation Priority Matrix

| Priority | Category | Items | Estimated Effort | Status |
|----------|----------|-------|------------------|--------|
| 🔴 HIGH | Core CRUD | MwSt, Pfand admin CRUD with auth (Verkauf stays update-free by design) | 2-3 days | ⏳ TODO |
| 🔴 HIGH | Core Tables | Kassenstand (CR), Gutschein (CR), Anzahlung (CR) | 3-4 days | ⏳ TODO |
| 🔴 HIGH | Validation | Comprehensive input validation | 1-2 days | ⏳ TODO |
| 🔴 HIGH | Security | User accounts, authentication and authorization | 2-3 days | ⏳ TODO |
| 🟡 MEDIUM | Accounting | Abrechnung Tag (CR), Monat (CRD), Jahr (CRD) | 3-5 days | ⏳ TODO |
| 🟡 MEDIUM | Business Logic | VAT calculation, sale creation | 2-3 days | ⏳ TODO |
| 🟡 MEDIUM | TSE | TSE transaction support + export endpoints | 2-3 days | ⏳ TODO |
| 🟡 MEDIUM | Supporting | Zaehlprotokoll (CRU), Bestellung (CRUD) | 2-3 days | ⏳ TODO |
| 🟢 LOW | Utilities | Import/Export, Search | 1-2 days | ⏳ TODO |

---

## Recommended Implementation Order

### Week 1: Foundation Completion
1. **Complete existing endpoints** (Phase 1)
   - Add admin-only operations for MwSt and Pfand with authorization
   - (Verkauf: no update functionality - keep Create/Read/Storno as-is)
2. **Add core validation** across all existing endpoints
3. **Implement authentication/authorization** (Phase 7.4)
   - Add user accounts (new `user` table) with per-user passwords
   - Add login auditing and transaction attribution
   - Add authentication middleware
   - Add authorization system with user roles
   - Protect sensitive endpoints

### Week 2: Core Business Tables
1. **Kassenstand** - Cash register balance management (CR)
2. **Gutschein** - Voucher management (CR)
3. **Anzahlung** - Installment payment management (CR)

### Week 3: Accounting System
1. **Abrechnung Tag** - Daily settlement (CR, incl. automatic TSE export)
2. **Abrechnung Monat** - Monthly settlement (CRD, + `/offen` endpoint)
3. **Abrechnung Jahr** - Yearly settlement (CRD, + `/offen` endpoint)

### Week 4: Supporting Features
1. **Zaehlprotokoll** - Counting protocols (CRU)
2. **Bestellung** - Order management (CRUD)
3. **TSE Integration** - Technical Security Equipment (incl. export endpoints)

### Week 5: Business Logic Porting
1. **VAT Calculator** - Core financial calculations
2. **Sale Workflow** - Enhanced sale creation with business logic
3. **Storno Enhancements** - Advanced refund functionality

### Week 6: Utilities and Finalization
1. **Import/Export** - Data migration tools
2. **Search Enhancements** - Improved search functionality
3. **Comprehensive Testing** - Full test coverage
4. **Documentation** - Complete API documentation

---

## Testing Strategy

### Unit Tests
- Each endpoint should have unit tests
- Test edge cases and error conditions
- Test business logic calculations
- Test data validation

### Integration Tests
- Test complete workflows (e.g., sale creation with VAT calculation)
- Test cross-entity relationships
- Test database constraints

### Test Coverage Target
- Minimum 80% code coverage
- All critical paths tested
- All business logic validated

### Test Files to Create
- `tests/test_mwst.py` - MwSt CRUD tests
- `tests/test_pfand.py` - Pfand CRUD tests
- `tests/test_kassenstand.py` - Cash register tests
- `tests/test_gutschein.py` - Voucher management tests
- `tests/test_anzahlung.py` - Installment payment tests
- `tests/test_abrechnung*.py` - Accounting tests
- `tests/test_zaehlprotokoll.py` - Counting protocol tests
- `tests/test_bestellung.py` - Order management tests
- `tests/test_tse.py` - TSE integration tests
- `tests/test_auth.py` - Authentication/authorization tests
- `tests/test_vat_calculator.py` - Business logic tests

---

## Documentation Requirements

1. **API Documentation**: Auto-generated from FastAPI (already working via `/docs` and `/redoc`)
2. **Code Documentation**: Docstrings for all functions and classes
3. **Business Logic Documentation**: Explain complex calculations and workflows
4. **Migration Guide**: For transitioning from Java POS to new API
5. **Setup Instructions**: Clear instructions for deployment and configuration (incl. TLS setup on the LAN)
6. **Database Schema Documentation**: Complete schema reference

---

## Success Criteria

- [ ] All database tables have corresponding models and endpoints
- [ ] Bookkeeping integrity: no update/delete endpoints for immutable tables (verkauf, kassenstand, gutschein, anzahlung, abrechnung_tag)
- [ ] All business logic from Java POS is ported to API
- [ ] Per-user accounts with login auditing and transaction attribution
- [ ] Comprehensive validation and error handling
- [ ] 80%+ test coverage
- [ ] Complete API documentation
- [ ] Working integration with existing database
- [ ] Ready for frontend client development
- [ ] All existing functionality preserved and enhanced

---

## File Structure Target

```
python/
├── __init__.py
├── main.py                    # FastAPI app setup
├── session.py                 # Database session management
├── models.py                  # All SQLModel definitions (incl. new User, Anmeldung models)
├── business/                  # Business logic modules
│   ├── __init__.py
│   ├── vat_calculator.py      # VAT calculation logic
│   ├── sale_workflow.py      # Sale creation workflow
│   ├── storno_logic.py        # Storno/refund logic
│   └── cash_register.py       # Cash register operations
├── routers/                   # FastAPI route definitions
│   ├── __init__.py
│   ├── artikel.py
│   ├── lieferant.py
│   ├── produktgruppe.py
│   ├── mwst.py
│   ├── pfand.py
│   ├── rabattaktion.py
│   ├── verkauf.py
│   ├── auth.py                # NEW: Authentication endpoints
│   ├── users.py               # NEW: Admin user management endpoints
│   ├── kassenstand.py         # NEW: Cash register (CR)
│   ├── gutschein.py           # NEW: Vouchers (CR)
│   ├── anzahlung.py           # NEW: Installments (CR)
│   ├── abrechnung_tag.py      # NEW: Daily settlements (CR)
│   ├── abrechnung_monat.py    # NEW: Monthly settlements (CRD)
│   ├── abrechnung_jahr.py     # NEW: Yearly settlements (CRD)
│   ├── zaehlprotokoll.py      # NEW: Counting protocols (CRU)
│   ├── bestellung.py          # NEW: Orders (CRUD)
│   ├── tse.py                 # NEW: TSE integration (incl. export)
│   └── import_export.py       # NEW: Data import/export
├── utils/                     # Utility functions
│   ├── __init__.py
│   ├── auth.py                # NEW: Authentication utilities
│   ├── csv_import.py          # CSV import utilities
│   ├── csv_export.py          # CSV export utilities
│   └── validation.py          # Input validation utilities
└── tests/                     # Test files
    ├── conftest.py
    ├── test_*.py              # Existing tests
    └── test_*.py              # NEW: Tests for all new functionality
```

Note: There are deliberately **no** `routers/verkauf_mwst.py` and `routers/verkauf_details.py` - these tables are only modified as side-effects of the `verkauf.py` endpoints.

---

## Dependencies and Prerequisites

### Python Dependencies (already in requirements.txt or need to add)
- `fastapi` - Web framework
- `sqlmodel` - SQLAlchemy + Pydantic models
- `pymysql` or `mariadb` - MySQL/MariaDB connector
- `bcrypt` - Password hashing
- `python-jose` or `pyjwt` - JWT tokens (or session-based alternative)
- `pytest` - Testing framework
- `httpx` - Async HTTP client for testing
- Python TSE library (to be determined - the Java POS uses the Java TSE API for export/delete operations; a Python equivalent must be verified)

### Database Requirements
- MySQL 5.7+ or MariaDB 10.2+
- Database schema from `../git/mysql/generateDB.sql`
- Appropriate user permissions (see `../git/mysql/grants.sql`)
- One-time migration: new `user`/`anmeldung` tables + `user_id` columns on transaction tables

---

## Migration Considerations

### From Java POS to API
1. **Data Migration**: Existing data can be used as-is (same database schema)
2. **Functionality Migration**: Port business logic incrementally
3. **UI Migration**: Frontend can be developed separately using the API
4. **Training Mode**: Support training mode like in Java POS (separate training_* tables)

### Backward Compatibility
- Maintain compatibility with existing database
- Ensure all existing data relationships are preserved
- Add migration scripts if schema changes are needed (new user tables and `user_id` columns are the planned schema changes)

---

## Next Steps

1. **Review this plan** and provide feedback
2. **Prioritize implementation** based on business needs
3. **Start with Phase 1** - Complete existing endpoints
4. **Proceed to Phase 2** - Add core business tables (Kassenstand first)
5. **Continue through phases** in recommended order
6. **Test thoroughly** at each phase
7. **Document progress** and update this plan as needed
