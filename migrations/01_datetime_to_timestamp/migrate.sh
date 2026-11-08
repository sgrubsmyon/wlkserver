#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "Backup"
echo "kassenadmin password:"
#mysqldump -u kassenadmin -p kasse > $SCRIPT_DIR/backup_before_timestamp.sql
mysqldump --defaults-extra-file=~/.my.kassenadmin.cnf -u kassenadmin kasse > $SCRIPT_DIR/backup_before_timestamp.sql

echo ""
echo "Before migration"
# Look at bookings around the daylight saving time change in 2025 (30th March 2025, 2:00 AM)
echo "mitarbeiter password:"
#mysql -u mitarbeiter -p kasse -e "SELECT verkaufsdatum FROM verkauf WHERE verkaufsdatum >= '2025-03-29' AND verkaufsdatum <= '2025-04-01';"
mysql --defaults-extra-file=~/.my.mitarbeiter.cnf -u mitarbeiter kasse -e "SELECT verkaufsdatum FROM verkauf WHERE verkaufsdatum >= '2025-03-29' AND verkaufsdatum <= '2025-04-01';"

echo ""
echo "Running Python migration script..."
python3 $SCRIPT_DIR/migrate_datetime_to_timestamp.py

echo ""
echo "After migration: (times on 2025-03-29 should be 1 hour and on 2025-03-30 and 2025-03-31 2 hours earlier than before, because converted to UTC)"
# Now, bookings from 2026-03-28 should be 1 hour earlier, and bookings from 2026-03-29 should be 2 hours earlier, because they are now in UTC instead of local time.
echo "mitarbeiter password:"
#mysql -u mitarbeiter -p kasse -e "SELECT verkaufsdatum FROM verkauf WHERE verkaufsdatum >= '2025-03-29' AND verkaufsdatum <= '2025-04-01';"
mysql --defaults-extra-file=~/.my.mitarbeiter.cnf -u mitarbeiter kasse -e "SELECT verkaufsdatum FROM verkauf WHERE verkaufsdatum >= '2025-03-29' AND verkaufsdatum <= '2025-04-01';"

echo ""
echo "Running SQL schema migration..."
echo "kassenadmin password:"
#mysql -u kassenadmin -p kasse < $SCRIPT_DIR/datetime_to_timestamp.sql
mysql --defaults-extra-file=~/.my.kassenadmin.cnf -u kassenadmin kasse < $SCRIPT_DIR/datetime_to_timestamp.sql
