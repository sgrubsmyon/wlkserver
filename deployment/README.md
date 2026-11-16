# Deploying the API as a systemd service

The unit file `wlkserver.service` assumes:

- the checkout lives in `/opt/wlkserver`,
- a dedicated system user `wlkserver` runs it,
- the venv is `/opt/wlkserver/python/venv`,
- the API listens on port 8000.

Adjust those paths/user in the unit if your layout differs.

## 0. Prerequisites

The system packages and the MariaDB database must exist first; the main
`README.md` describes them in detail. In short, on a fresh Ubuntu:

```
sudo apt update
sudo apt install -y mariadb-server python3-venv build-essential pkg-config libmariadb-dev rsync
sudo systemctl enable --now mariadb
sudo mariadb-secure-installation
```

`build-essential`, `pkg-config` and `libmariadb-dev` are required because the
Python MariaDB connector is built from source.

Create the database users, then the database itself (from the repository
root; this **drops** an existing `kasse` and `kasse_training`):

```
sudo mariadb
```
```sql
CREATE USER 'kassenadmin'@'localhost' IDENTIFIED BY 'your-admin-password';
CREATE USER 'mitarbeiter'@'localhost' IDENTIFIED BY 'your-cashier-password';
```
```
sudo mariadb < deployment/create_db.sql
```

Set the same `kassenadmin` password in `/opt/wlkserver/python/.env` (step 4).

## 1. Create the service user

The API only needs read access to the code and `.env` plus access to the
database (and the TSE serial device, if used). It has no reason to log in:

```
sudo useradd --system --home /opt/wlkserver --shell /usr/sbin/nologin wlkserver
```

For the TSE, add it to the group that owns the device (usually `dialout`) and
uncomment `SupplementaryGroups=dialout` in the unit:

```
sudo usermod -aG dialout wlkserver
ls -l /dev/ttyACM0   # check owner/group
```

## 2. Copy the code

From the repository root:

```
sudo mkdir -p /opt/wlkserver
sudo rsync -a --delete --exclude python/venv --exclude python/.env --exclude .git \
    ./ /opt/wlkserver/
sudo chown -R wlkserver:wlkserver /opt/wlkserver
```

`python/tse_commissioning.jsonl`, if present, is runtime data — keep it out of
the copy or leave it in place on updates.

## 3. Install the Python environment (as the service user)

```
sudo -u wlkserver python3 -m venv /opt/wlkserver/python/venv
sudo -u wlkserver /opt/wlkserver/python/venv/bin/pip install -r /opt/wlkserver/python/requirements.txt
```

No C toolchain beyond step 0 is needed for the TSE: the SE-API libraries are
vendored prebuilt in `assets/SE-API-C/bin/` (see `python/README.md`).

## 4. Configure

Create `/opt/wlkserver/python/.env` (git-ignored, never commit it) with at
least:

```
DBHOST=localhost
DBNAME=kasse
DBUSER=kassenadmin
DBPASS=your-admin-password
AUTH_SECRET=…          # long random value, not the dev placeholder
```

Generate `AUTH_SECRET` with
`python3 -c "import secrets; print(secrets.token_hex(32))"`.
Add the TSE and DSFinV-K variables from the table in `python/README.md` when
they apply. The file is read by `config.py` itself, so no `EnvironmentFile` is
needed in the unit. Make it readable for the service user only:

```
sudo chown wlkserver:wlkserver /opt/wlkserver/python/.env
sudo chmod 600 /opt/wlkserver/python/.env
```

For a fresh install the schema is created by `deployment/create_db.sql` (step
0). When upgrading an existing database instead, run the migrations in
`migrations/` (see `migrations/migrate_current_db.sh`) as `kassenadmin` before
the first start.

## 5. Install and start the service

```
sudo cp deployment/wlkserver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wlkserver
systemctl status wlkserver
journalctl -u wlkserver -f
```

Check `http://<server>:8000/docs` or `GET /tse/status`. If a firewall is
active, open the API port: `sudo ufw allow 8000/tcp`.

Then change the bootstrap admin password (`admin` / `changeme`) as described in
the main `README.md`:

```
curl -X POST http://localhost:8000/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"username": "admin", "password": "changeme"}'
curl -X POST "http://localhost:8000/users/1/reset-password?new_password=your-new-password" \
    -H "Authorization: Bearer <access_token>"
```

## Updating

From the repository root:

```
sudo systemctl stop wlkserver
sudo rsync -a --delete --exclude python/venv --exclude python/.env --exclude .git \
    ./ /opt/wlkserver/
sudo -u wlkserver /opt/wlkserver/python/venv/bin/pip install -r /opt/wlkserver/python/requirements.txt
sudo chown -R wlkserver:wlkserver /opt/wlkserver
sudo systemctl start wlkserver
```

`python/.env` is excluded so the server configuration and secrets are not
overwritten by the development checkout.

Keep the service at **one worker** (the unit sets `--workers 1`): the TSE
client serializes SE-API calls with a per-process lock.
