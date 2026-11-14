#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "Backing up database..."
#echo "kassenadmin password:"
#mysqldump -u kassenadmin -p kasse > "$SCRIPT_DIR/backup_before_artikel_bio_vegan.sql"
mysqldump --defaults-extra-file=~/.my.kassenadmin.cnf -u kassenadmin kasse > "$SCRIPT_DIR/backup_before_artikel_bio_vegan.sql"

echo ""
echo "Adding bio/vegan columns to artikel..."
#echo "kassenadmin password:"
#mysql -u kassenadmin -p kasse < "$SCRIPT_DIR/artikel_bio_vegan.sql"
mysql --defaults-extra-file=~/.my.kassenadmin.cnf -u kassenadmin kasse < "$SCRIPT_DIR/artikel_bio_vegan.sql"

echo ""
echo "Migration complete."
