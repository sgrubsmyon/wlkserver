#!/usr/bin/env python3
"""
Migration: User accounts, login auditing, transaction attribution (Phase 7.4)

Creates the `user` and `anmeldung` tables, adds a nullable `user_id`
column (with FK) to the transaction tables, and bootstraps an admin user
(username='admin', password='changeme').

Usage:
    python3 migrations/02_user_auth/migrate_user_auth.py

Reads DB credentials from python/.env (DBHOST, DBNAME, and asks for
password). Requires: python3 + mariadb connector.
"""
import os
import sys
from getpass import getpass

try:
    import mariadb
except ImportError:
    print("ERROR: mariadb connector not installed. pip install mariadb", file=sys.stderr)
    sys.exit(1)

# Load .env
env_path = os.path.join(os.path.dirname(__file__), "..", "..", "python", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

host = os.getenv("DBHOST", "localhost")
db = os.getenv("DBNAME", "kasse")
user = os.getenv("DBUSER", "kassenadmin")

password = os.getenv("DBPASSWORD")
if not password:
    password = getpass(f"Enter MySQL password for {user}@{host}: ")

sql_path = os.path.join(os.path.dirname(__file__), "user_auth.sql")
with open(sql_path) as f:
    sql = f.read()

# Split on semicolons (naive but sufficient for this migration)
conn = mariadb.connect(host=host, user=user, password=password, database=db)
cur = conn.cursor()
for stmt in sql.split(";"):
    stmt = stmt.strip()
    if not stmt:
        continue
    # skip comment-only
    lines = [ln for ln in stmt.splitlines() if ln.strip() and not ln.strip().startswith("--")]
    if not lines:
        continue
    try:
        cur.execute(stmt)
        conn.commit()
        print("OK:", stmt.splitlines()[0][:80])
    except mariadb.Error as e:
        print("WARN:", e, "|", stmt.splitlines()[0][:60])
conn.close()
print("Migration finished.")