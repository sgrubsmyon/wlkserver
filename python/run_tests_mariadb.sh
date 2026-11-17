#!/usr/bin/env bash
# Run the pytest suite against MariaDB instead of in-memory SQLite.
# Prerequisite: deployment/create_test_db.sh has created `kasse_test`.
set -euo pipefail

cd "$(dirname "$0")"

read -r -s -p "MariaDB password for kassenadmin: " dbpass
echo

# Percent-encode, so passwords with @ : / # etc. survive the URL.
dbpass=$(./venv/bin/python -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$dbpass")

TEST_DATABASE_URL="mariadb+mariadbconnector://kassenadmin:${dbpass}@localhost/kasse_test" \
    ./venv/bin/python -m pytest -q "$@"
