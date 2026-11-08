#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "Backing up database..."
#echo "kassenadmin password:"
#mysqldump -u kassenadmin -p kasse > "$SCRIPT_DIR/backup_before_gutschein_counter.sql"
mysqldump --defaults-extra-file=~/.my.kassenadmin.cnf -u kassenadmin kasse > "$SCRIPT_DIR/backup_before_gutschein_counter.sql"

echo ""
echo "Creating and seeding the voucher counter..."
#echo "kassenadmin password:"
#mysql -u kassenadmin -p kasse < "$SCRIPT_DIR/gutschein_counter.sql"
mysql --defaults-extra-file=~/.my.kassenadmin.cnf -u kassenadmin kasse < "$SCRIPT_DIR/gutschein_counter.sql"

sudo mysql -e "GRANT SELECT, INSERT, UPDATE ON kasse.gutschein_counter TO 'mitarbeiter'@'localhost';"

echo ""
echo "Migration complete."
