-- ============================================================
-- Migration: drop the legacy `training_*` tables
-- ============================================================
-- The Java POS kept a copy of the cashier tables for its training mode.
-- wlkserver does not use them: training mode runs the whole API against a
-- separate database (TRAINING_MODE + TRAINING_DB_URL), whose schema is created
-- from models/tables.py on startup. `tse_transaction.training` remains and
-- still marks training receipts.
--
-- Run as kassenadmin (full privileges). Back up first.

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS
    training_abrechnung_jahr_mwst,
    training_abrechnung_jahr,
    training_abrechnung_monat_mwst,
    training_abrechnung_monat,
    training_zaehlprotokoll_details,
    training_zaehlprotokoll,
    training_abrechnung_tag_tse,
    training_abrechnung_tag_mwst,
    training_abrechnung_tag,
    training_anzahlung_details,
    training_anzahlung,
    training_gutschein,
    training_kassenstand,
    training_verkauf_details,
    training_verkauf_mwst,
    training_verkauf;

SET FOREIGN_KEY_CHECKS = 1;
