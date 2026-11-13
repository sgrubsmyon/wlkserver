# Deploying the API as a systemd service

The unit file `wlkserver.service` assumes:

- the checkout lives in `/opt/wlkserver`,
- a dedicated system user `wlkserver` runs it,
- the venv is `/opt/wlkserver/python/venv`,
- the API listens on port 8000.

Adjust those paths/user in the unit if your layout differs.

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
sudo rsync -a --delete --exclude python/venv --exclude .git \
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

No C toolchain is needed: the TSE libraries are vendored prebuilt in
`assets/SE-API-C/bin/` (see `python/README.md`).

## 4. Configure

Create `/opt/wlkserver/python/.env` (git-ignored, never commit it) with at
least:

```
DBHOST=…
DBNAME=…
DBUSER=kassenadmin
DBPASS=…
AUTH_SECRET=…          # long random value, not the dev placeholder
```

Add the TSE and DSFinV-K variables from the table in `python/README.md` when
they apply. The file is read by `config.py` itself, so no `EnvironmentFile` is
needed in the unit.

Run the one-off database migrations described in `python/README.md`
("Database migration") as `kassenadmin` before the first start.

## 5. Install and start the service

```
sudo cp deployment/wlkserver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wlkserver
systemctl status wlkserver
journalctl -u wlkserver -f
```

Check `http://<server>:8000/docs` or `GET /tse/status`.

## Updating

From the repository root:

```
sudo systemctl stop wlkserver
sudo rsync -a --delete --exclude python/venv --exclude .git ./ /opt/wlkserver/
sudo -u wlkserver /opt/wlkserver/python/venv/bin/pip install -r /opt/wlkserver/python/requirements.txt
sudo chown -R wlkserver:wlkserver /opt/wlkserver
sudo systemctl start wlkserver
```

Keep the service at **one worker** (the unit sets `--workers 1`): the TSE
client serializes SE-API calls with a per-process lock.
