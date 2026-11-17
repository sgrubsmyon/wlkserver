#!/usr/bin/env bash
# Daily MariaDB backup, keeping KEEP_DAYS days. Credentials come from the
# server's .env, so there is no second place that stores the DB password.
#
#   sudo deployment/backup_db.sh
#
# Run by wlkserver-backup.timer, or from cron. Back up python/.env and the TSE
# commissioning log separately and securely: they hold AUTH_SECRET and the
# TimeAdmin PIN, and nothing here can recreate them.
set -euo pipefail

ENV_FILE=${ENV_FILE:-/opt/wlkserver/python/.env}
BACKUP_DIR=${BACKUP_DIR:-/var/backups/wlkserver}
KEEP_DAYS=${KEEP_DAYS:-30}

set -a
. "$ENV_FILE"
set +a

: "${DBNAME:?DBNAME missing in $ENV_FILE}"
: "${DBUSER:?DBUSER missing in $ENV_FILE}"
: "${DBPASS:?DBPASS missing in $ENV_FILE}"

umask 077
install -d "$BACKUP_DIR"
target="$BACKUP_DIR/${DBNAME}_$(date +%Y-%m-%d_%H%M%S).sql.gz"

# MYSQL_PWD keeps the password out of the process list.
MYSQL_PWD=$DBPASS mariadb-dump --host="${DBHOST:-localhost}" --user="$DBUSER" \
    --single-transaction --quick --routines --triggers \
    "$DBNAME" | gzip > "$target"

find "$BACKUP_DIR" -name "${DBNAME}_*.sql.gz" -mtime +"$KEEP_DAYS" -delete
echo "backup written: $target"
