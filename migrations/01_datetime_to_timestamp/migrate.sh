#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "Enter the MySQL kassenadmin password (for creating a backup):"
mysqldump -u kassenadmin -p kasse > $SCRIPT_DIR/backup_before_timestamp.sql

echo ""
echo "Before migration:"
# Look at bookings around the daylight saving time change in 2026 (29th March 2026, 2:00 AM)
echo "Enter the MySQL mitarbeiter password:"
mysql -u mitarbeiter -p kasse -e "SELECT verkaufsdatum FROM verkauf WHERE verkaufsdatum >= '2026-03-28' AND verkaufsdatum <= '2026-03-31';"

echo ""
echo "Running Python migration script..."
python3 $SCRIPT_DIR/migrate_datetime_to_timestamp.py

echo ""
echo "After migration: (times should be 1 or 2 hours earlier than before, because converted to UTC)"
# Now, bookings from 2026-03-28 should be 1 hour earlier, and bookings from 2026-03-29 should be 2 hours earlier, because they are now in UTC instead of local time.
echo "Enter the MySQL mitarbeiter password:"
mysql -u mitarbeiter -p kasse -e "SELECT verkaufsdatum FROM verkauf WHERE verkaufsdatum >= '2026-03-28' AND verkaufsdatum <= '2026-03-31';"

echo ""
echo "Running SQL schema migration..."
echo "Enter the MySQL kassenadmin password:"
mysql -u kassenadmin -p kasse < $SCRIPT_DIR/datetime_to_timestamp.sql