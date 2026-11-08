#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "Backing up database..."
echo "kassenadmin password:"
#mysqldump -u kassenadmin -p kasse > "$SCRIPT_DIR/backup_before_user_auth.sql"
mysqldump --defaults-extra-file=~/.my.kassenadmin.cnf -u kassenadmin kasse > "$SCRIPT_DIR/backup_before_user_auth.sql"

echo ""
echo "Running SQL migration script..."
echo "kassenadmin password:"
#mysql -u kassenadmin -p kasse < "$SCRIPT_DIR/user_auth.sql"
mysql --defaults-extra-file=~/.my.kassenadmin.cnf -u kassenadmin kasse < "$SCRIPT_DIR/user_auth.sql"

echo ""
echo "Migration complete. Remember to change the default admin password ('changeme')!"
