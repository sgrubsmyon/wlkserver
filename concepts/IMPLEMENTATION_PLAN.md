# Weltladenkasse API - Implementation Plan

## Overview

This document outlines the comprehensive implementation plan to complete the FastAPI backend for the Weltladenkasse POS system. The goal is to port all business logic from the existing Java Swing POS application (`../git/src/org/weltladen_bonn/pos/`) to the new Python FastAPI backend.

## Current Status Summary

### ✅ Already Implemented
- **Database Models**: All core tables have SQLModel definitions in `python/models.py`
- **CRUD Operations**: Most major entities have basic CRUD functionality
- **Business Logic**: Some core logic like article versioning and storno operations
- **API Structure**: Clean FastAPI structure with proper routing

### 🎯 What Needs to be Done
- Complete missing CRUD operations for existing models
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

### 1.3 Verkauf (Sale) - Add Update Functionality
**Current**: Create, Read, Storno in `python/routers/verkauf.py`  
**Target**: Full CRUD with update restrictions

**Files to modify:**
- `python/routers/verkauf.py` - Add PATCH endpoint
- Add validation: prevent updates to completed/storniert sales
- Add business logic for sale modification constraints

### 1.4 Dedicated Endpoints for Related Tables
**Current**: Handled within main entity endpoints  
**Target**: Separate endpoints for better API design

**Files to create:**
- `python/routers/verkauf_mwst.py` - CRUD for sale VAT entries
- `python/routers/verkauf_details.py` - CRUD for sale details

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

**Required endpoints:**
- GET /kassenstand - List cash register balances with filtering
- GET /kassenstand/{id} - Get single entry
- POST /kassenstand - Create new cash register entry
- PATCH /kassenstand/{id} - Update entry (with restrictions)
- GET /kassenstand/aktuell - Get current cash register balance

**Business logic from Java:**
- Cash register balance tracking in `../git/src/org/weltladen_bonn/pos/kasse/Kasse.java`
- Balance validation and change calculation in `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java`
- Integration with sales and storno operations

**Files to create:**
- `python/models.py` - Add Kassenstand models
- `python/routers/kassenstand.py` - All CRUD endpoints
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

**Required endpoints:**
- GET /gutschein - List vouchers with filtering
- GET /gutschein/{id} - Get single voucher
- POST /gutschein - Create new voucher
- POST /gutschein/{id}/einloesen - Redeem voucher (link to sale detail)
- GET /gutschein/ausstehend - List outstanding vouchers
- GET /gutschein/eingeloest - List redeemed vouchers

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/kasse/GutscheinEinloesenDialog.java` - Voucher redemption logic
- Voucher creation in `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java` (articles 6 and 7 are voucher-related)
- Balance tracking and validation

**Files to create:**
- `python/models.py` - Add Gutschein models
- `python/routers/gutschein.py` - All CRUD endpoints + redemption logic

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

**Required endpoints:**
- GET /anzahlung - List installments
- GET /anzahlung/{id} - Get single installment
- POST /anzahlung - Create new installment
- POST /anzahlung/{id}/aufloesen - Resolve installment
- GET /anzahlung/offen - List open installments
- GET /anzahlung/aufgeloest - List resolved installments

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/kasse/AnzahlungAufloesDialog.java` - Installment resolution
- `../git/src/org/weltladen_bonn/pos/kasse/AnzahlungNeuDialog.java` - Installment creation
- Integration with sales workflow in `../git/src/org/weltladen_bonn/pos/kasse/Kassieren.java`

**Files to create:**
- `python/models.py` - Add Anzahlung and AnzahlungDetails models
- `python/routers/anzahlung.py` - All CRUD endpoints + resolution logic

---

## Phase 3: Add Accounting/Settlement Tables (Medium Priority)

### 3.1 Abrechnung Tag (Daily Settlement)
**Priority**: 🟡 MEDIUM - Essential for accounting

**Database tables**:
- `abrechnung_tag` (lines 180-193 in `../git/mysql/generateDB.sql`)
- `abrechnung_tag_mwst` (lines 194-201 in `../git/mysql/generateDB.sql`)
- `abrechnung_tag_tse` (lines 202-214 in `../git/mysql/generateDB.sql`)

**Required endpoints:**
- GET /abrechnung/tag - List daily settlements
- GET /abrechnung/tag/{id} - Get single daily settlement
- POST /abrechnung/tag - Create daily settlement
- GET /abrechnung/tag/offen - Check for incomplete daily settlements
- POST /abrechnung/tag/{id}/abschliessen - Finalize daily settlement

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/kasse/AbrechnungenTag.java` - Daily settlement logic
- `../git/src/org/weltladen_bonn/pos/kasse/Abrechnungen.java` - Base settlement functionality
- VAT aggregation and reporting
- TSE integration

**Files to create:**
- `python/models.py` - Add AbrechnungTag, AbrechnungTagMwst, AbrechnungTagTse models
- `python/routers/abrechnung_tag.py` - All CRUD endpoints

### 3.2 Abrechnung Monat (Monthly Settlement)
**Priority**: 🟡 MEDIUM - For monthly accounting

**Database tables**:
- `abrechnung_monat` (lines 242-250 in `../git/mysql/generateDB.sql`)
- `abrechnung_monat_mwst` (lines 251-258 in `../git/mysql/generateDB.sql`)

**Required endpoints:**
- GET /abrechnung/monat - List monthly settlements
- GET /abrechnung/monat/{id} - Get single monthly settlement
- POST /abrechnung/monat - Create monthly settlement (from daily settlements)

**Files to create:**
- `python/models.py` - Add AbrechnungMonat, AbrechnungMonatMwst models
- `python/routers/abrechnung_monat.py` - All CRUD endpoints

### 3.3 Abrechnung Jahr (Yearly Settlement)
**Priority**: 🟡 LOW - For yearly accounting

**Database tables**:
- `abrechnung_jahr` (lines 269-277 in `../git/mysql/generateDB.sql`)
- `abrechnung_jahr_mwst` (lines 278-285 in `../git/mysql/generateDB.sql`)

**Required endpoints:**
- GET /abrechnung/jahr - List yearly settlements
- GET /abrechnung/jahr/{id} - Get single yearly settlement
- POST /abrechnung/jahr - Create yearly settlement (from monthly settlements)

**Files to create:**
- `python/models.py` - Add AbrechnungJahr, AbrechnungJahrMwst models
- `python/routers/abrechnung_jahr.py` - All CRUD endpoints

---

## Phase 4: Add Supporting Tables (Medium-Low Priority)

### 4.1 Zaehlprotokoll (Counting Protocol)
**Priority**: 🟡 MEDIUM - For cash counting and reconciliation

**Database tables**:
- `zaehlprotokoll` (lines 215-223 in `../git/mysql/generateDB.sql`)
- `zaehlprotokoll_details` (lines 224-231 in `../git/mysql/generateDB.sql`)

**Required endpoints:**
- GET /zaehlprotokoll - List counting protocols
- GET /zaehlprotokoll/{id} - Get single protocol
- POST /zaehlprotokoll - Create new counting protocol
- GET /zaehlprotokoll/abrechnung/{abrechnung_tag_id} - Get protocols for settlement

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/kasse/ZaehlprotokollDialog.java` - Counting protocol creation

**Files to create:**
- `python/models.py` - Add Zaehlprotokoll, ZaehlprotokollDetails models
- `python/routers/zaehlprotokoll.py` - All CRUD endpoints

### 4.2 Bestellung (Order/Purchase Order)
**Priority**: 🟢 LOW - For supplier ordering

**Database tables**:
- `bestellung` (lines 287-294 in `../git/mysql/generateDB.sql`)
- `bestellung_details` (lines 295-304 in `../git/mysql/generateDB.sql`)

**Required endpoints:**
- GET /bestellung - List orders
- GET /bestellung/{bestell_nr}/{typ} - Get single order
- POST /bestellung - Create new order
- PATCH /bestellung/{bestell_nr}/{typ} - Update order
- DELETE /bestellung/{bestell_nr}/{typ} - Cancel order

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/besteller/Bestellen.java` - Order creation
- `../git/src/org/weltladen_bonn/pos/besteller/Bestellung.java` - Order management
- `../git/src/org/weltladen_bonn/pos/besteller/BestellAnzeige.java` - Order display

**Files to create:**
- `python/models.py` - Add Bestellung, BestellungDetails models
- `python/routers/bestellung.py` - All CRUD endpoints

---

## Phase 5: Add TSE Integration (Medium Priority for German Compliance)

### 5.1 TSE Transaction Support
**Priority**: 🟡 MEDIUM - Legal requirement for German cash registers

**Database table**: `tse_transaction` (lines 306-321 in `../git/mysql/generateDB.sql`)

**Required endpoints:**
- GET /tse/transaction - List TSE transactions
- GET /tse/transaction/{id} - Get single transaction
- POST /tse/transaction - Create TSE-signed transaction
- GET /tse/status - Get TSE status
- POST /tse/init - Initialize TSE

**Business logic from Java:**
- `../git/src/org/weltladen_bonn/pos/kasse/WeltladenTSE.java` - Complete TSE integration
- `../git/src/org/weltladen_bonn/pos/kasse/TSEInitDialog.java` - TSE initialization
- `../git/src/org/weltladen_bonn/pos/kasse/TSETarFile.java` - TSE file handling

**Files to create:**
- `python/models.py` - Add TSETransaction model
- `python/routers/tse.py` - TSE transaction endpoints

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
- Cash drawer management
- Payment processing (cash, EC card)
- Change calculation (see line 44 in `Kasse.java`: `private final BigDecimal ecSchwelle = new BigDecimal("10.00");`)
- End-of-day procedures
- Integration with kassenstand
- Training mode support

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

---

## Implementation Priority Matrix

| Priority | Category | Items | Estimated Effort | Status |
|----------|----------|-------|------------------|--------|
| 🔴 HIGH | Core CRUD | Complete MwSt, Pfand CRUD; Add Verkauf update | 2-3 days | ⏳ TODO |
| 🔴 HIGH | Core Tables | Kassenstand, Gutschein, Anzahlung | 3-4 days | ⏳ TODO |
| 🔴 HIGH | Validation | Comprehensive input validation | 1-2 days | ⏳ TODO |
| 🟡 MEDIUM | Accounting | Abrechnung Tag/Monat/Jahr | 3-5 days | ⏳ TODO |
| 🟡 MEDIUM | Business Logic | VAT calculation, sale creation | 2-3 days | ⏳ TODO |
| 🟡 MEDIUM | TSE | TSE transaction support | 2-3 days | ⏳ TODO |
| 🟡 MEDIUM | Supporting | Zaehlprotokoll, Bestellung | 2-3 days | ⏳ TODO |
| 🟢 LOW | Utilities | Import/Export, Search | 1-2 days | ⏳ TODO |

---

## Recommended Implementation Order

### Week 1: Foundation Completion
1. **Complete existing CRUD** (Phase 1)
   - Add missing operations for MwSt and Pfand
   - Add Verkauf update functionality
   - Add dedicated endpoints for related tables
2. **Add core validation** across all existing endpoints

### Week 2: Core Business Tables
1. **Kassenstand** - Cash register balance management
2. **Gutschein** - Voucher management
3. **Anzahlung** - Installment payment management

### Week 3: Accounting System
1. **Abrechnung Tag** - Daily settlement
2. **Abrechnung Monat** - Monthly settlement
3. **Abrechnung Jahr** - Yearly settlement

### Week 4: Supporting Features
1. **Zaehlprotokoll** - Counting protocols
2. **Bestellung** - Order management
3. **TSE Integration** - Technical Security Equipment

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
- `tests/test_bestellung.py` - Order management tests
- `tests/test_tse.py` - TSE integration tests
- `tests/test_vat_calculator.py` - Business logic tests

---

## Documentation Requirements

1. **API Documentation**: Auto-generated from FastAPI (already working via `/docs` and `/redoc`)
2. **Code Documentation**: Docstrings for all functions and classes
3. **Business Logic Documentation**: Explain complex calculations and workflows
4. **Migration Guide**: For transitioning from Java POS to new API
5. **Setup Instructions**: Clear instructions for deployment and configuration
6. **Database Schema Documentation**: Complete schema reference

---

## Success Criteria

- [ ] All database tables have corresponding models and endpoints
- [ ] All business logic from Java POS is ported to API
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
├── models.py                  # All SQLModel definitions
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
│   ├── verkauf_mwst.py        # NEW: Dedicated endpoints
│   ├── verkauf_details.py     # NEW: Dedicated endpoints
│   ├── kassenstand.py         # NEW: Cash register
│   ├── gutschein.py           # NEW: Vouchers
│   ├── anzahlung.py           # NEW: Installments
│   ├── abrechnung_tag.py      # NEW: Daily settlements
│   ├── abrechnung_monat.py    # NEW: Monthly settlements
│   ├── abrechnung_jahr.py     # NEW: Yearly settlements
│   ├── zaehlprotokoll.py      # NEW: Counting protocols
│   ├── bestellung.py          # NEW: Orders
│   ├── tse.py                  # NEW: TSE integration
│   └── import_export.py        # NEW: Data import/export
├── utils/                     # Utility functions
│   ├── __init__.py
│   ├── csv_import.py          # CSV import utilities
│   ├── csv_export.py          # CSV export utilities
│   └── validation.py          # Input validation utilities
└── tests/                     # Test files
    ├── conftest.py
    ├── test_*.py              # Existing tests
    └── test_*.py              # NEW: Tests for all new functionality
```

---

## Dependencies and Prerequisites

### Python Dependencies (already in requirements.txt or need to add)
- `fastapi` - Web framework
- `sqlmodel` - SQLAlchemy + Pydantic models
- `pymysql` or `mariadb` - MySQL/MariaDB connector
- `python-decimal` - Enhanced decimal support (if needed)
- `pytest` - Testing framework
- `httpx` - Async HTTP client for testing

### Database Requirements
- MySQL 5.7+ or MariaDB 10.2+
- Database schema from `../git/mysql/generateDB.sql`
- Appropriate user permissions

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
- Add migration scripts if schema changes are needed

---

## Next Steps

1. **Review this plan** and provide feedback
2. **Prioritize implementation** based on business needs
3. **Start with Phase 1** - Complete existing CRUD operations
4. **Proceed to Phase 2** - Add core business tables (Kassenstand first)
5. **Continue through phases** in recommended order
6. **Test thoroughly** at each phase
7. **Document progress** and update this plan as needed