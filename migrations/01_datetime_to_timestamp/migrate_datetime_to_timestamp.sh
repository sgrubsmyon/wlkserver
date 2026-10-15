#!/bin/bash

set -euo pipefail

echo "Enter the MySQL kassenadmin password (for creating a backup):"
mysqldump -u kassenadmin -p kasse > backup_before_timestamp.sql

echo "Before migration:"
mysql "SELECT verkaufsdatum FROM verkauf ORDER BY verkaufsdatum LIMIT 5;"

echo "Running Python migration script..."
python3 migrate_datetime_to_timestamp.py

echo "After migration: (times should be 1 or 2 hours earlier than before, because converted to UTC)"
mysql "SELECT verkaufsdatum FROM verkauf ORDER BY verkaufsdatum LIMIT 5;"

echo "Running SQL schema migration..."
mysql -u kassenadmin -p kasse < datetime_to_timestamp.sql