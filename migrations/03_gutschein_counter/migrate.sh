#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "Backing up database..."
mysqldump -u kassenadmin -p kasse > "$SCRIPT_DIR/backup_before_gutschein_counter.sql"

echo ""
echo "Creating and seeding the voucher counter..."
mysql -u kassenadmin -p kasse < "$SCRIPT_DIR/gutschein_counter.sql"

echo ""
echo "Migration complete."
