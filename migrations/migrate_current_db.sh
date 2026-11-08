#!/bin/bash

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo "***"
echo "*** LOAD CURRENT DB ***"
echo "***"
$SCRIPT_DIR/../../git/preisaenderung_00_import_recent_db_dump_with_credentials.sh
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
