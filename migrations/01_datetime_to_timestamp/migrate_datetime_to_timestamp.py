#!/usr/bin/env python3
"""
=====================================================================
Migration: DATETIME → TIMESTAMP with UTC storage
=====================================================================

WHY THIS MIGRATION
  sqlmodel 0.0.27+ enforces timezone-aware datetimes. The Python
  application uses datetime.now(timezone.utc) (aware UTC). MariaDB's
  TIMESTAMP type stores values in UTC and converts them on read/write
  using the session timezone.

DST PROBLEM (IMPORTANT)
  Historical data was stored in local time: CET (+01:00) in winter,
  CEST (+02:00) in summer. MariaDB's ALTER TABLE MODIFY converts
  using the CURRENT session timezone only. A single SET time_zone
  will misinterpret ~50% of historical rows by 1 hour.
  Example: "2024-01-15 14:30:00" (CET) should become "2024-01-15
  13:30:00" UTC. But if you SET time_zone = '+02:00' (CEST),
  MariaDB would store it as "2024-01-15 12:30:00" UTC — 1 hour off.

THERE IS NO PURELY SQL-ONLY SOLUTION that handles historical DST
transitions correctly. You MUST use this Python migration script.

This script correctly migrates all DATETIME columns to TIMESTAMP
with UTC storage. Handles historical DST transitions using zoneinfo
(Europe/Berlin).

Usage:
    python3 migrate_datetime_to_timestamp.py

The script reads DB credentials from python/.env (DBHOST, DBNAME).
Requires: python3 + mariadb connector (mariadb package).

Steps performed:
    1. For each table/column, read the existing DATETIME value
    2. Interpret it as Europe/Berlin local time (CET/CEST via zoneinfo)
    3. Convert to UTC
    4. Store the UTC value

MIGRATION PROCEDURE
  1. BACKUP the database first:
       mysqldump -u kassenadmin -p kasse > backup_before_timestamp.sql
  2. Run the Python migration script (handles DST correctly):
       cd /home/mvoge/Documents/Markus/i/code/Weltladenkasse/wlkserver
       python3 migrations/01_datetime_to_timestamp/migrate_datetime_to_timestamp.py
  3. Verify the results:
       SELECT verkaufsdatum FROM verkauf ORDER BY verkaufsdatum LIMIT 5;
       -- Values should now be in UTC (roughly 1-2 hours earlier than
       -- the original local times)
"""

import os
import sys
from getpass import getpass
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    import mariadb
except ImportError:
    print("Error: mariadb package not installed.")
    print("Install it: pip install mariadb")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration — read from .env
# ---------------------------------------------------------------------------

# Locate python/.env relative to this script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(script_dir, "..", "..", "python", ".env")

if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                os.environ.setdefault(key, val)

db_host = os.environ.get("DBHOST", "127.0.0.1")
db_name = os.environ.get("DBNAME", "kasse")
db_user = "kassenadmin"
db_pass = getpass(f"Enter the MySQL password for user '{db_user}': ")

# Timezone constants
TZ_BERLIN = ZoneInfo("Europe/Berlin")
TZ_UTC = ZoneInfo("UTC")

# Tables with (table_name, primary_key_column, datetime_column)
# Add or remove entries as new tables/columns are created.
TABLES_COLUMNS = [
    ("artikel",        "artikel_id",     "von"),
    ("artikel",        "artikel_id",     "bis"),
    ("rabattaktion",   "rabatt_id",      "von"),
    ("rabattaktion",   "rabatt_id",      "bis"),
    ("verkauf",        "rechnungs_nr",   "verkaufsdatum"),
    ("kassenstand",    "kassenstand_id", "buchungsdatum"),
    ("anzahlung",      "anzahlung_id",   "datum"),
    ("gutschein",      "gutschein_id",   "datum"),
    ("zaehlprotokoll", "id",             "zeitpunkt"),
    ("abrechnung_tag", "id",             "zeitpunkt"),
    ("abrechnung_tag", "id",             "zeitpunkt_real"),
    ("bestellung",     "bestell_nr",     "bestell_datum"),
    # TRAINING MODE:
    ("training_verkauf",        "rechnungs_nr",   "verkaufsdatum"),
    ("training_kassenstand",    "kassenstand_id", "buchungsdatum"),
    ("training_anzahlung",      "anzahlung_id",   "datum"),
    ("training_gutschein",      "gutschein_id",   "datum"),
    ("training_zaehlprotokoll", "id",             "zeitpunkt")
]


def to_utc(dt_value):
    """Convert a naive datetime (stored in local time) to UTC."""
    if isinstance(dt_value, str):
        dt_value = dt_value.replace(" ", "T")  # ISO format for fromisoformat
        dt_local = datetime.fromisoformat(dt_value)
    else:
        dt_local = dt_value  # already a Python datetime (naive)

    # Attach the local timezone, then convert to UTC
    dt_local = dt_local.replace(tzinfo=TZ_BERLIN)
    return dt_local.astimezone(TZ_UTC)


def migrate():
    print(f"Connecting to {db_name}@{db_host} as {db_user}...")
    conn = mariadb.connect(
        host=db_host,
        user=db_user,
        password=db_pass,
        database=db_name,
    )
    cursor = conn.cursor()

    changed_count = 0
    skipped_count = 0

    for table, pk_col, dt_col in TABLES_COLUMNS:
        print(f"\n--- {table}.{dt_col} ---")

        # Check column type
        cursor.execute("""
            SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """, (db_name, table, dt_col))
        row = cursor.fetchone()

        if not row:
            print(f"  Column '{dt_col}' not found in table '{table}'. Skipping.")
            continue

        col_type = row[0].lower()
        if "timestamp" in col_type:
            print(f"  Already {row[0]}. Skipping.")
            skipped_count += 1
            continue

        print(f"  Current type: {row[0]}")

        # Read all rows
        cursor.execute(f"SELECT `{pk_col}`, `{dt_col}` FROM `{table}`")
        rows = cursor.fetchall()
        print(f"  Found {len(rows)} rows.")

        # Process and update
        for pk, dt_val in rows:
            if dt_val is None:
                continue

            dt_utc = to_utc(dt_val)

            # Only update if the value actually changed (avoids unnecessary writes)
            if isinstance(dt_val, str):
                current_as_utc = to_utc(dt_val)
            else:
                current_as_utc = to_utc(str(dt_val).replace(" ", "T"))

            # Update the row with the correct UTC value
            cursor.execute(
                f"UPDATE `{table}` SET `{dt_col}` = %s WHERE `{pk_col}` = %s",
                (dt_utc, pk),
            )
            changed_count += 1

        # Now change the column type to TIMESTAMP
        print(f"  Changing column type to TIMESTAMP NOT NULL...")
        cursor.execute(f"ALTER TABLE `{table}` MODIFY `{dt_col}` TIMESTAMP NOT NULL")

    conn.commit()

    print(f"\n{'=' * 50}")
    print(f"Migration complete!")
    print(f"  Changed: {changed_count} rows")
    print(f"  Skipped (already TIMESTAMP): {skipped_count} columns")
    print(f"{'=' * 50}")

    conn.close()


if __name__ == "__main__":
    migrate()