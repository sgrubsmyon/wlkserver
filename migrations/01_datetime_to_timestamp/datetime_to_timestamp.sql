-- =====================================================================
-- Migration: DATETIME → TIMESTAMP with UTC storage
-- =====================================================================
--
-- WHY THIS MIGRATION
--   sqlmodel 0.0.27+ enforces timezone-aware datetimes. The Python
--   application uses datetime.now(timezone.utc) (aware UTC). MariaDB's
--   TIMESTAMP type stores values in UTC and converts them on read/write
--   using the session timezone.
--
-- DST PROBLEM (IMPORTANT)
--   Historical data was stored in local time: CET (+01:00) in winter,
--   CEST (+02:00) in summer. MariaDB's ALTER TABLE MODIFY converts
--   using the CURRENT session timezone only. A single SET time_zone
--   will misinterpret ~50% of historical rows by 1 hour.
--
--   Example: "2024-01-15 14:30:00" (CET) should become "2024-01-15
--   13:30:00" UTC. But if you SET time_zone = '+02:00' (CEST),
--   MariaDB would store it as "2024-01-15 12:30:00" UTC — 1 hour off.
--
-- THERE IS NO PURELY SQL-ONLY SOLUTION that handles historical DST
-- transitions correctly. You MUST use the Python migration script.
--
-- MIGRATION PROCEDURE
--   1. BACKUP the database first:
--        mysqldump -u kassenadmin -p kasse > backup_before_timestamp.sql
--
--   2. Run the Python migration script (handles DST correctly):
--        cd /home/mvoge/Documents/Markus/i/code/Weltladenkasse/wlkserver
--        python3 migrations/migrate_datetime_to_timestamp.py
--
--   3. Verify the results:
--        SELECT verkaufsdatum FROM verkauf ORDER BY verkaufsdatum LIMIT 5;
--        -- Values should now be in UTC (roughly 1-2 hours earlier than
--        -- the original local times)
--
--   4. Run the SQL schema migration (changes DATETIME → TIMESTAMP):
--        mysql -u kassenadmin -p kasse < datetime_to_timestamp.sql
--
--   5. Update the Python application:
--        - Change all datetime.now() → datetime.now(timezone.utc)
--        - For display (receipts): dt.astimezone(ZoneInfo("Europe/Berlin"))
--        - Remove sqlmodel==0.0.26 pin from requirements.txt
--
-- ALTERNATIVE (simpler, no schema change needed)
--   If you prefer to keep DATETIME columns in MariaDB:
--   1. Keep sqlmodel==0.0.26 (or upgrade and use NaiveDatetime)
--   2. Use datetime.now(ZoneInfo("Europe/Berlin")) in Python
--   3. The mariadb connector stores aware datetimes in DATETIME columns
--      correctly (converts to local time, stores as-is)
--   4. No schema migration needed
--   This keeps the Java POS working unchanged (reads raw local time).
-- =====================================================================


-- =====================================================================
-- SCHEMA CHANGES (RUN AFTER python migration script)
-- =====================================================================
-- The ALTER TABLE statements below change column types. They should be
-- run AFTER the Python migration script has written correct UTC values.
-- If run BEFORE the Python script, MariaDB will convert using the
-- current session timezone, causing 1-hour errors for ~50% of rows.
-- =====================================================================

ALTER TABLE verkauf MODIFY verkaufsdatum TIMESTAMP NOT NULL;
ALTER TABLE kassenstand MODIFY buchungsdatum TIMESTAMP NOT NULL;
ALTER TABLE anzahlung MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE gutschein MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE zaehlprotokoll MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE abrechnung_tag MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE abrechnung_monat MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE abrechnung_jahr MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE bestellung MODIFY bestelldatum TIMESTAMP NOT NULL;
ALTER TABLE tse_transaction MODIFY transaction_timestamp TIMESTAMP NOT NULL;

-- =====================================================================
-- TRAINING MODE TABLES (if training mode is used)
-- =====================================================================

ALTER TABLE training_verkauf MODIFY verkaufsdatum TIMESTAMP NOT NULL;
ALTER TABLE training_kassenstand MODIFY buchungsdatum TIMESTAMP NOT NULL;
ALTER TABLE training_anzahlung MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE training_gutschein MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE training_zaehlprotokoll MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE training_abrechnung_tag MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE training_abrechnung_monat MODIFY datum TIMESTAMP NOT NULL;
ALTER TABLE training_abrechnung_jahr MODIFY datum TIMESTAMP NOT NULL;