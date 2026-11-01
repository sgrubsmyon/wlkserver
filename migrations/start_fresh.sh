#!/bin/bash

mysql --local-infile -hlocalhost -ukassenadmin -p -e "source ../DB_Dump_kasse_mit_kompliziertester_Rechnung_Nr._57874.sql" kasse
01_datetime_to_timestamp/migrate.sh
02_user_auth/migrate.sh
03_gutschein_counter/migrate.sh
