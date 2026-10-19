#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "Backing up database..."
mysqldump -u kassenadmin -p kasse > "$SCRIPT_DIR/backup_before_user_auth.sql"

echo ""
echo "Running Python migration script..."
python3 "$SCRIPT_DIR/migrate_user_auth.py"

echo ""
echo "Migration complete. Remember to change the default admin password ('changeme')!"