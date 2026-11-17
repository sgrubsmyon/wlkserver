# Migrating from the Java POS to the API

This guide switches the shop's bookkeeping from the Java Swing POS
(`../git/src/org/weltladen_bonn/pos/`) to the HTTP API in this repository. Both
use the **same MariaDB schema**, so the data is not converted: the API is a
new front end that writes the same tables, and the migration is a cutover with
a schema upgrade in between.

The API is not a drop-in replacement for the Java client. Printing receipts,
the ODS/price-tag exports and the Swing dialogs are not part of it; the API
provides the business logic and data, a web client (`../wlkclient`) provides
the UI. Read [API.md](API.md) and [API_REFERENCE.md](API_REFERENCE.md) first.

## What changes

| Java POS | API |
|---|---|
| Swing desktop app, one database connection per client | HTTP API on the LAN, typed JSON, one database connection pool |
| Business logic inside UI classes | `python/business/` services behind the endpoints |
| No user accounts | bcrypt accounts, JWT sessions, `user_id` attribution on transactions, login audit (`anmeldung`) |
| Training via rerouted `training_*` tables | full sandbox database (`TRAINING_MODE`, `kasse_training`) |
| Automatic DSFinV-K files only | DSFinV-K zip per settlement + CSV import/export + TSE export endpoints |
| Printing, ODS/price-tag exports in the app | Not provided; the client or a script does it |

The receipt, voucher, installment, cash-register and settlement semantics are
ported one-to-one (`Kassieren.java`, `HeutigeRechnungen.java`,
`AbrechnungenTag.java`, `WeltladenTSE.java`, `DSFinVKCSV.java`). Where the API
deliberately fixes a Java bug, the reasoning is in
[`concepts/IMPLEMENTATION_PLAN.md`](../concepts/IMPLEMENTATION_PLAN.md) and
[`concepts/TODO.md`](../concepts/TODO.md).

## Prerequisites

- A verified backup of the production database **and** the Java POS
  configuration (including its TSE settings and the written-down TSE PUKs).
- The TSE serial device present, with the SE-API library in
  `assets/SE-API-C/bin/` and read access for the service user.
- A server as described in `deployment/README.md` (MariaDB, Python venv, nginx).
- Java POS closed. Two writers on the same receipt and cash-register tables
  would corrupt the running balance; there is no mixed operation.

## 1. Freeze and back up

1. Close the Java POS on every till. Do not create sales or settlements from
   then on.
2. Note the state you must continue from:
   - last `rechnungs_nr`, last `kassenstand_id`, last settlement
     (`abrechnung_tag`), open `anzahlung` rows, outstanding `gutschein` balances;
   - the current TSE transaction number and signature counter
     (`GET /tse/status` later, or the Java TSE dialog now).
3. Back up the database with `deployment/backup_db.sh` (or
   `mariadb-dump --single-transaction kasse > backup.sql`). Copy the dump off
   the machine.
4. Back up the Java POS state and `python/.env`. `AUTH_SECRET`, the TimeAdmin
   PIN and the TSE PUKs cannot be recreated.

## 2. Upgrade the schema

A fresh installation uses `deployment/create_db.sql`. An existing production
database is upgraded in place with the numbered migrations, **in order**:

```
migrations/migrate_current_db.sh
```

which runs `01_datetime_to_timestamp`, `02_user_auth`, `03_gutschein_counter`,
`04_artikel_bio_vegan` and `05_drop_training_tables`. Each step keeps a
pre-migration dump (`migrations/*/backup_*.sql`) and is idempotent enough to
re-run after a failure; inspect the script before running it. What they change:

- **01** converts `DATETIME` columns to UTC `TIMESTAMP` (the API sets the
  session time zone to `+00:00`; the Java POS used local time).
- **02** creates `user` and `anmeldung`, adds `user_id` to the transaction
  tables and seeds the bootstrap admin (`admin` / `changeme` - change it).
- **03** creates `gutschein_counter` seeded from `MAX(gutschein_nr)`, so the
  first API voucher continues the existing numbering.
- **04** adds `artikel.bio` / `artikel.vegan`.
- **05** drops the legacy `training_*` tables (the sandbox is a separate
  database now).

Verify before starting the API: `user` exists, `gutschein_counter.last_nr`
equals the highest paper/Java voucher number, and no `training_*` table is
left. The full schema reference is [DATABASE.md](DATABASE.md).

## 3. Accounts and attribution

1. Start the API on localhost (`deployment/README.md`, step 5).
2. Log in as `admin` / `changeme` and set a real password
   (`POST /users/{user_id}/reset-password`).
3. Create one account per cashier with role `mitarbeiter`, plus one admin per
   shop. Use a dedicated `mitarbeiter`/service account for scripts, never a
   person's account: the `anmeldung` audit then shows who did what.
4. Old rows keep `user_id = NULL` (the Java POS did not record users); new
   receipts always carry the token's user.

## 4. Configuration

`python/.env` (never committed) holds everything the API needs. The full table
is in `python/README.md`; the migration-relevant ones are:

| Variable | Meaning |
|---|---|
| `DBHOST`, `DBNAME`, `DBUSER`, `DBPASS` | MariaDB connection (`kassenadmin` for the API) |
| `AUTH_SECRET` | JWT signing key - must not be the dev default |
| `TSE_LIB_PATH`, `TSE_DEVICE_PATH` | SE-API library and serial device |
| `TSE_ID`, `TSE_CLIENT_ID`, `TSE_TIME_ADMIN_PIN` | TSE registration and the TimeAdmin secret (server-side, shared by all tills) |
| `TSE_COMMISSIONING_LOG` | JSONL log of a commissioning run (no secrets) |
| `DSFINVK_*` | Company/master data written into the DSFinV-K export |
| `DSFINVK_EXPORT_DIR` | Where the settlement writes its DSFinV-K zip |
| `IMAGES_DIR` | Article pictures (files, not BLOBs) |
| `SOLL_MUENZ_KASSENSTAND`, `SOLL_SCHEIN_KASSENSTAND` | Target coin/note stock for the cash-reset suggestion |

Keep the API at **one worker**: the TSE client serializes SE-API calls with a
per-process lock, and the voucher/Kassenstand code relies on it.

## 5. Dry run against a copy

Do not learn the API on the production data. Create `kasse_test`
(`deployment/create_test_db.sh`) or a copy of the production dump, then:

1. Start the API with `TRAINING_MODE=1` and `TRAINING_DB_URL` pointing at
   `kasse_training` (`deployment/wlkserver-training.service`). The sandbox
   mirrors users and seeds a small catalog; it never touches production.
2. Book the scenarios the shop actually uses: cash and card sale, Pfand and
   Leergut, both discount kinds, voucher sale and redemption, Anzahlung and
   resolution, storno of each, Tagesabschluss with a count protocol, month and
   year settlement, a CSV order import and a DSFinV-K download.
3. Compare totals with the Java POS output for the same period in a copy.

The suite itself runs against MariaDB (`python/run_tests_mariadb.sh`) and covers
these flows; use it before and after the cutover.

## 6. Cutover

1. Stop the Java POS; keep it installed for the rollback window.
2. Run the migrations (step 2) if not already done.
3. Start `wlkserver` (and configure nginx/TLS per `deployment/README.md`).
4. Continue the cash count: if the Java POS ended with a physical count that
   was not yet booked, create the matching `POST /kassenstand` entry before the
   first API sale. The running balance must equal the drawer.
5. Log in on the tills, book one small test sale (cash, then card), and storno
   it if the shop's policy allows; check the TSE transaction number advanced.
6. Check the open items are visible: `GET /anzahlung/offen`,
   `GET /gutschein/ausstehend`, `GET /abrechnung/tag/offen`.
7. Close the first Tagesabschluss at the next close of business and compare it
   with the Java POS's last one (VAT per rate, `bar_brutto`, cash balance).

Receipt and settlement numbers simply continue: they are `AUTO_INCREMENT` and
the settlement range links to existing receipts.

## 7. TSE

The same TSE keeps running for both systems; the API continues the transaction
and signature counters already in the log. The API uses the SE-API **v3.1**
(the Java POS shipped v2.3), so commissioning is a one-shot operation with
permanent PUKs: read `concepts/TSE_FAILURE_PATHWAYS.md` and follow
`deployment/README.md` before the first `POST /tse/init` with credentials. A
commissioned TSE needs no re-initialisation; on power-up the API sets the time
on demand (`TSE_TIME_ADMIN_PIN`).

Training mode signs on the real TSE as well (`training = TRUE`, `AVTraining^`
prefix), which is why the sandbox database must be persistent - the transaction
numbers and counters in `tse_transaction` have to survive restarts.

## 8. Behavioural differences to expect

- **No updates, no deletes** on receipts, cash-register rows, vouchers,
  installments and settlements. Correct with a storno or a new entry. A
  receipt that belongs to a completed Tagesabschluss cannot be stornoed.
- **Article edits version** the article row; positions keep pointing at the old
  version.
- **Special articles must exist** (`RABATT1`, `RABATT2`, `ANPASSUNG`,
  `ANZAHLUNG`, `ANZAHLAUFLOES`, `GUTSCHEIN`, `GUTSCHEINEINLOES`, the `PFAND*`
  articles). `deployment/create_db.sql` seeds them; an existing database
  already has them - verify with `GET /artikel?artikel_nr=RABATT1` before
  cutover.
- **The API computes, the client displays.** Discounts, Pfand lines, VAT and
  change come from the API; the web client must not recompute them.
- **Not part of the API:** receipt printing, ODS exports
  (`Bestellvorlage_*.ods`, `Inventur.ods`, `Tages-/Monats-/Jahresabrechnung.ods`)
  and the price-tag export. These are client-side output; the CSV exports and
  the DSFinV-K zip are available from the API.
- **Auth everywhere.** Every endpoint except `POST /auth/login` needs a bearer
  token, so scripts authenticate per run.

## 9. Scripts instead of manual work

With the API, price lists and orders can be automated even though the GUI is
not open: log in (`POST /auth/login`), call the endpoint, re-login on `401`.
Check state before creating settlements, because `POST` is not idempotent
(`GET /abrechnung/monat/offen`, `GET /abrechnung/jahr/offen`). Verify the
internal CA instead of disabling TLS. Details are in
`concepts/IMPLEMENTATION_PLAN.md`, Phase 7.4.

## 10. Rollback

Both systems cannot run at the same time. To go back after the cutover:

1. Stop `wlkserver` and nginx's `/api/` site, stop `wlkserver-training`.
2. Restore the pre-migration database dump taken in step 1 (the schema
   migrations are additive, but receipts and settlements written by the API do
   not exist in the Java POS's model of the world; restoring is the clean
   rollback).
3. Start the Java POS. Its TSE log contains the API's transactions; the Java
   POS reads the counters from the TSE, not from the database.

## 11. Verification checklist

- [ ] Migrations applied; `gutschein_counter.last_nr` = highest existing voucher
- [ ] Bootstrap admin password changed; one account per cashier; roles correct
- [ ] `GET /tse/status` reports the TSE mode, life-cycle state and client
      registration without errors
- [ ] Test sale (cash + card) and storno produce correct receipt, VAT, cash and
      TSE rows
- [ ] Open installments and vouchers match the Java POS state
- [ ] First Tagesabschluss matches the Java POS settlement for the same data
- [ ] DSFinV-K zip written (`DSFINVK_EXPORT_DIR`) and downloadable via
      `GET /export/dsfinvk/{id}`
- [ ] Backup timer active (`systemctl list-timers wlkserver-backup.timer`)
      and one restore tested into a throwaway database

## Further reading

- [API.md](API.md) - base URL, auth, errors, endpoint groups
- [API_REFERENCE.md](API_REFERENCE.md) - generated reference for all endpoints
- [DATABASE.md](DATABASE.md) - tables, keys and bookkeeping rules
- [KASSENSTAND_UND_ABRECHNUNG.md](KASSENSTAND_UND_ABRECHNUNG.md) - cash register
  and settlement flow with examples
- `deployment/README.md` - installation, nginx/TLS, backups, training instance
- `concepts/IMPLEMENTATION_PLAN.md` - Java-to-API mapping and design decisions
- `concepts/TSE_FAILURE_PATHWAYS.md` - commissioning safety analysis
