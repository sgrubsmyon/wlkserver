#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "Backing up database..."
#echo "kassenadmin password:"
#mysqldump -u kassenadmin -p kasse > "$SCRIPT_DIR/backup_before_drop_training_tables.sql"
mysqldump --defaults-extra-file=~/.my.kassenadmin.cnf -u kassenadmin kasse > "$SCRIPT_DIR/backup_before_drop_training_tables.sql"

echo ""
echo "Dropping the legacy training_* tables..."
#echo "kassenadmin password:"
#mysql -u kassenadmin -p kasse < "$SCRIPT_DIR/drop_training_tables.sql"
mysql --defaults-extra-file=~/.my.kassenadmin.cnf -u kassenadmin kasse < "$SCRIPT_DIR/drop_training_tables.sql"

# Dropping a table leaves its table-level grants behind.
echo ""
echo "Removing leftover grants on the dropped tables..."
sudo mysql -e "DELETE FROM mysql.tables_priv WHERE Db = 'kasse' AND Table_name LIKE 'training\\_%'; FLUSH PRIVILEGES;"

echo ""
echo "Migration complete."
