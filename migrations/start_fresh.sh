#!/bin/bash

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "***"
echo "*** LOAD OLD DB ***"
echo "***"
#echo "kassenadmin password:"
#mysql --local-infile -hlocalhost -ukassenadmin -p -e "source ../DB_Dump_kasse_mit_kompliziertester_Rechnung_Nr._57874.sql" kasse
mysql --defaults-extra-file=~/.my.kassenadmin.cnf --local-infile -hlocalhost -ukassenadmin -e "source $SCRIPT_DIR/../DB_Dump_kasse_mit_kompliziertester_Rechnung_Nr._57874.sql" kasse
echo ""
echo "***"
echo "*** MIGRATION 01: DATETIME TO TIMESTAMP ***"
echo "***"
$SCRIPT_DIR/01_datetime_to_timestamp/migrate.sh
echo ""
echo "***"
echo "*** MIGRATION 02: USER AUTH ***"
echo "***"
$SCRIPT_DIR/02_user_auth/migrate.sh
echo ""
echo "***"
echo "*** MIGRATION 03: VOUCHER COUNTER ***"
echo "***"
$SCRIPT_DIR/03_gutschein_counter/migrate.sh
