#!/usr/bin/env bash
# Create the disposable kasse_test database from the canonical schema.
# Reuses deployment/create_db.sql (generateDB.sql + migrations 01-05) with the
# database name rewritten and the training-database section stripped, so the
# production `kasse` and the training sandbox are never touched.
set -euo pipefail

cd "$(dirname "$0")/.."

sed -e 's/\bkasse\b/kasse_test/g' -e '/Separate training database/,$d' \
    deployment/create_db.sql | sudo mariadb
