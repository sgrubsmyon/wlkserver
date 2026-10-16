#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "Enter the MySQL kassenadmin password (for creating a backup):"
mysqldump -u kassenadmin -p kasse > $SCRIPT_DIR/backup_before_timestamp.sql

echo "Before migration:"
# Look at bookings around the daylight saving time change in 2026 (29th March 2026, 2:00 AM)
mysql "SELECT verkaufsdatum FROM verkauf ORDER BY verkaufsdatum WHERE verkaufsdatum >= '2026-03-28' AND verlaufsdatum <= '2026-03-30';"

echo "Running Python migration script..."
python3 $SCRIPT_DIR/migrate_datetime_to_timestamp.py

echo "After migration: (times should be 1 or 2 hours earlier than before, because converted to UTC)"
# Now, bookings from 2026-03-28 should be 1 hour earlier, and bookings from 2026-03-29 should be 2 hours earlier, because they are now in UTC instead of local time.
mysql "SELECT verkaufsdatum FROM verkauf ORDER BY verkaufsdatum WHERE verkaufsdatum >= '2026-03-28' AND verlaufsdatum <= '2026-03-30';"

echo "Running SQL schema migration..."
mysql -u kassenadmin -p kasse < $SCRIPT_DIR/datetime_to_timestamp.sql