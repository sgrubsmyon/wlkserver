# TSE commissioning — failure pathways and safety analysis

**Status:** 2026-11-12. Analysis of the first commissioning of the brand-new, still
uninitialised production TSE through `POST /tse/init` (`python/utils/tse_client.py:513`).
It is a **one-shot** operation: the goal is that a failed attempt leaves the TSE
*uninitialised* (retryable), never half-configured with unknown secrets, and that a
"successful but wrong" outcome is caught before the values are written.

Sources (all verified, not assumed):
`assets/SE-API-C/se-api-c/include/se_api.h`, `.../se-api-common/include/se_types.h`,
`.../se_result_t.h`, the vendor `firstBootTest` in
`assets/SE-API-C/se-api-c-test/se_api_test.c:535`, the bundled v3.1 library
(`se_getApiVersionString()` → `cryptovision SE-API v3.1`), the Java POS
`kasse/TSEInitDialog.java` and `kasse/WeltladenTSE.java`, and the current Python code.

---

## 1. What is irreversible, what is not

| Thing | Set by | Changeable later? |
|---|---|---|
| Admin PUK | `se_initializePuk("Admin")` | **No** — "PUK values cannot be changed once initialized" (`se_api.h:391`, `:539`) |
| TimeAdmin PUK | `se_initializePuk("TimeAdmin")` | **No** |
| Admin PIN | `se_unblockUser("Admin", puk, pin)` | Yes, with the Admin PUK |
| TimeAdmin PIN | `se_unblockUser("TimeAdmin", puk, pin)` | Yes, with the TimeAdmin PUK |
| Initialised state (LCS) | `se_initialize()` | **No** — one-way; a retry returns `ErrorSECommunicationFailed` (`se_api.h:445`) |
| TSE time | `se_updateTime(unixTime)` | Yes going forward; **already written log times keep the wrong value** |
| Client registration | `se_registerClient(clientId)` | Yes (Admin) |
| Stored log data | — | Deletable by design (`se_deleteStoredDataUpTo`) |

Consequence: **the PUKs are the only permanent secrets.** A wrong value written into a
PUK field is unrecoverable in the field. A wrong PIN is recoverable *only* with the
correct PUK. There is no factory reset.

Note also: a written PIN is not exercised during commissioning with the human-typed
string — the API re-authenticates with *the same bytes it just wrote*. A mangled but
length-valid PIN therefore passes the whole commissioning and only fails later, when a
person types the intended string (for TimeAdmin: at the next server start). That is
precisely the "initialisation finishes but wrong" class the user wants to avoid.

---

## 2. The implemented sequence (`initialize()`)

1. `se_getPinStatus()` → `pin_state` (0 = all PINs/PUKs initialised).
2. For each user, based on the snapshot: `se_initializePuk(user, puk)` if the PUK bit is
   set, then `se_unblockUser(user, puk, pin)` if the PIN bit is set.
3. Re-read `pin_state`; abort if anything is still in transport state.
4. `se_authenticateUser("Admin", admin_pin)` (only when LCS is `notInitialized`).
5. `se_initialize()`.
6. `se_authenticateUser("TimeAdmin")` + `se_updateTime(server now)` + `se_logOut("TimeAdmin")`.
7. `se_registerClient(TSE_CLIENT_ID)`.
8. `se_logOut("Admin")`, then `status()`.

This matches the vendor `firstBootTest` order (except the vendor's final
`se_lockTransactionLogging`/`se_unlockTransactionLogging`, which is not needed for a
fresh TSE and is not implemented).

---

## 3. Catastrophic pathways (TSE ends up with unknown secrets)

**C1 — PUK typo written and not noticed.**
There is no double-entry confirmation anywhere (the Java `TSEInitDialog` uses four plain
`JTextField`s, `TSEInitDialog.java:93-124`). A single mistyped PUK is written permanently.
The TSE keeps working until a PIN must be unblocked; then it is unusable for its purpose.

**C2 — Whitespace / invisible characters in a PIN or PUK.**
The router validates *character count* (`routers/tse.py:170-177`), then sends
`payload.…encode()`. `"1234 5678"` is 8 characters and passes; the space is written into
the PIN. Commissioning succeeds (step 6 uses the same bytes), and the failure surfaces
only when the human enters `"12345678"`. Then the TimeAdmin PIN is effectively lost and
recovery needs the PUK — catastrophic if C1 also happened.

**C3 — Non-ASCII input.**
The length check counts characters, but the C API counts bytes. 8 characters containing
non-ASCII signs encode to more than 8 bytes → `ErrorTSECommandDataInvalid` (fails safely,
but possibly *after* earlier writes). Worse in principle: any character whose UTF-8
encoding happens to produce exactly 8 bytes would be accepted and stored verbatim.
Also: the C header documents no content policy; nothing stops control characters or
embedded NULs (a NUL truncates the string for any C-side consumer).

**C4 — Partial write, then a retry with different values (the most dangerous current behaviour).**
Example: attempt 1 writes Admin PUK = P1, then fails at `se_unblockUser` (USB glitch).
The next attempt supplies P2. The bit-guard skips `se_initializePuk("Admin")` (PUK bit is
now clear) but still calls `se_unblockUser("Admin", P2, …)` — with the *wrong* PUK. The
result is `unblockFailed`, and `unblockPinIsBlocked` exists as an outcome
(`se_types.h:90-96`), i.e. **repeated wrong PUKs can permanently block the PUK**. Every
"try again with other values" makes it worse. Nothing in the current code prevents this
or even warns about it.

**C5 — Concurrent or duplicated commissioning.**
FastAPI runs sync endpoints in a thread pool, and `tse_client` has **no lock**. Two
`POST /tse/init` requests (double click, a retry after a client timeout, two admins)
interleave PUK/PIN writes through the same open device handle. The stored secrets can be
a mixture of both requests; neither operator knows the full set. The same race exists
between commissioning and a sale/time sync. (The codebase already uses
`threading.Lock` for voucher numbering and Kassenstand — the precedent exists.)

**C6 — Secrets never recorded before the irreversible write.**
Nothing persists the values and the response does not echo them. If the browser tab, the
server process or the network dies right after a PUK write, the only copy is whatever the
operator wrote down — and there is no "I have written these down" gate before submitting.

---

## 4. Blocked / burnt credentials (recoverable while the PUK is known)

**R1 — `TSE_TIME_ADMIN_PIN` does not match the PIN set at commissioning.**
`initialize()` takes the TimeAdmin PIN from the request body, but every later time sync
(`_ensure_time`, `utils/tse_client.py:324`) uses `config.tse_time_admin_pin()`
(`python/README.md:41`). `.env` is loaded once at import (`config.py:11`), so a newly
entered value needs a server restart. If the value in `.env` is wrong, every restart /
sync-interval expiry calls `se_authenticateUser("TimeAdmin", wrong)` and **burns one PIN
retry**; after the retry limit the PIN is blocked, the TSE goes to LCS `noTime`, and every
sale fails with `ErrorTimeNotSet` until the PIN is unblocked with the PUK. Not fatal if
the PUK is known — catastrophic together with C1. Fixing `.env` does not un-burn retries.

**R2 — Time sync attempted on a not-yet-commissioned TSE.**
`_ensure_time` does not check `pin_state`/LCS before authenticating TimeAdmin. It is
reached from `_ensure_open` (every transaction, export, `get_signature_counter`, and
`status()` once the device is open) and from `ensure_ready()` (`POST /tse/init` without a
body). On a transport-state TSE the result of `se_authenticateUser("TimeAdmin", …)` is
undocumented; if it counts as a failed attempt, a few clicks before commissioning could
block the TimeAdmin PIN entry.

**R3 — Re-running `POST /tse/init` with a wrong TimeAdmin PIN on an already commissioned TSE.**
The PUK/PIN block is skipped (bits clear), LCS is `active` so no Admin auth happens — but
step 6 still authenticates TimeAdmin with the *request's* PIN. A typo there burns retries
(R1-like). There is no guard that says "already commissioned, use `ensure_ready`".

**R4 — Any authenticated user can commission.**
`POST /tse/init` depends on `require_user`, not `require_admin`
(`routers/tse.py:158`; the global dependency in `main.py:76` is also only `require_user`).
A cashier or a misbehaving client can trigger C4/C5/R1.

**R5 — Destructive export without admin rights.**
`POST /tse/export/delete` deletes stored TSE data and was only user-protected. Not an
init risk, but it destroys the evidence needed to reconstruct what happened during
commissioning. Closed 2026-11-13 (gap G12): the endpoint now requires an admin.

---

## 5. "Initialised, but wrong"

**W1 — Wrong server clock.**
The TSE time is `int(datetime.now().timestamp())` from the API host
(`utils/tse_client.py`). A skewed clock is signed into every subsequent log and
cannot be corrected retroactively. Closed 2026-11-13 (gap G11): `initialize()` refuses
before any write unless `timedatectl` reports `NTPSynchronized=yes`, and the preflight
reports the clock state; the NTP check remains part of the live-run protocol.

**W2 — Wrong `TSE_CLIENT_ID`.**
`config.tse_client_id()` defaults to `WeltladenKasse` (14 bytes; valid 1–30). A value
longer than 30 bytes makes `se_registerClient` fail (safe, TSE stays usable). A wrong but
valid value maps the wrong ERS id into every signature and the DSFinV-K `Kassen-ID`;
re-registering is possible with Admin rights, but the old mapping must be removed.

**W3 — `ErrorERSalreadyMapped` treated as success** (`utils/tse_client.py:348-356`).
Harmless on a brand-new TSE (no mappings exist), but it would silently accept a client-id
collision on a reused TSE. Not applicable here; keep in mind for replacements.

**W4 — `TSE_TIME_ADMIN_PIN` forgotten in `.env`.**
Commissioning succeeds, but the first restart cannot set the time (R1). The TSE is
"correctly initialised" yet operationally dead until `.env` is fixed.

**W5 — Wrong PUK recorded despite a correct write.**
Same outcome as C1, discovered only in an emergency.

---

## 6. Fail-safe paths (verified: no secret is written)

These are the good cases — they abort before or without corrupting the TSE:

- **S1** Wrong character count → HTTP 400 in the router before any C call.
- **S2** Missing/wrong `TSE_DEVICE_PATH`, no permission, device busy (Java POS still
  running, `bin/tse-test` running) → `se_openDirect` fails, `_open()` returns False,
  "device not available"; zero writes.
- **S3** `se_getPinStatus` fails → abort before the first write.
- **S4** `se_initializePuk` fails (already set, wrong length) → abort. Fields of an earlier
  user may already be written (partial state, see the recovery matrix).
- **S5** `se_unblockUser` returns non-zero or `unblockResult != 0` → abort, reporting the
  named enum value (`unblockPinIsBlocked` vs `unblockFailed`) as `unblock_result` (G8).
- **S6** `se_initialize` fails with `ErrorSECommunicationFailed` because the TSE is already
  initialised → harmless; the LCS check on the next attempt handles it.
- **S7** `se_initialize` fails (expired certificate, storage, secure element) → LCS normally
  stays `notInitialized`, retry later.
- **S8** Time update fails → LCS stays `noTime`; recoverable with the PIN.
- **S9** `se_registerClient` fails (bad id length) → TSE stays initialised/active;
  re-runnable.
- **S10** Library missing / incompatible / stub path → no device access, no writes
  (an incompatible library fails at import, i.e. at startup, which is also safe).

---

## 7. Process and environment

- **P1** Double submit / retry after an HTTP timeout → C5 or C4.
- **P2** Server killed or restarted mid-sequence → partial state; resumable **only with the
  same values**.
- **P3** Several uvicorn workers → separate processes; the in-process lock would not help.
  The docs already recommend one worker (`IMPLEMENTATION_PLAN.md:629`); commissioning needs
  that guarantee (or a file lock).
- **P4** The old Java POS or another tool holding the serial device → open fails (safe),
  but a confusing "device not available".
- **O1** The PUKs/PINs travel as plain JSON. With HTTP (no TLS) they are readable on the
  wire; use TLS or run the commissioning GUI on the server host (`localhost`).
- **O2** Secrets could end up in logs if request bodies are ever logged. FastAPI does not
  log bodies by default; keep it that way and never log the payload.
- **O3** USB/serial disconnect or power loss mid-write → partial state (P2).
- **O4** Wrong TSE on another port → harmless for the new device, but verify the path.

---

## 8. Verified gaps in the current code

| # | Gap | Where | Enables |
|---|---|---|---|
| G1 | ~~Init only requires `require_user`~~ **closed 2026-11-13** (`require_admin`) | `routers/tse.py` | R4, C5 |
| G2 | ~~TimeAdmin PIN comes from the request at init but from `.env` afterwards; no consistency check~~ **closed 2026-11-13** (init rejects a body value != `TSE_TIME_ADMIN_PIN` with 400) | `utils/tse_client.py:513`, `config.py:96` | R1, W4 |
| G3 | ~~`_ensure_time` authenticates before checking `pin_state`/LCS~~ **fixed 2026-11-13**: guarded on `pin_state == 0` + LCS `noTime`/`active`; reports "not ready" without authenticating | `utils/tse_client.py:324` | R2 |
| G4 | ~~Re-running init on a commissioned TSE still performs a TimeAdmin auth with the request PIN~~ **closed 2026-11-13** (refused before any authentication, points to `ensure_ready`) | `utils/tse_client.py` | R3 |
| G5 | ~~Length validation on characters, not ASCII bytes; no charset check~~ **closed 2026-11-13** (`_credential_bytes`: UTF-8 byte count, printable non-whitespace ASCII only) | `routers/tse.py` | C2, C3 |
| G6 | ~~Partial state + new PUK → `se_unblockUser` with an unverified PUK~~ **closed 2026-11-13** (refused before any write unless `confirm_stored_puks=true`; response lists what is already set) | `utils/tse_client.py`, `routers/tse.py` | C4 |
| G7 | ~~No lock around SE-API calls~~ **closed 2026-11-13** (every public operation under a reentrant lock; one worker still required) | `utils/tse_client.py` | C5, P3 |
| G8 | ~~`unblockResult` / `remainingRetries` discarded~~ **closed 2026-11-13** (named `unblock_result` and `remaining_retries` in failed responses) | `utils/tse_client.py` | diagnosis of R1/C4 |
| G9 | ~~No record of what was written (no secrets, but also no progress state)~~ **closed 2026-11-13** (`TSE_COMMISSIONING_LOG` JSONL: pin_state, fields set, timestamps, client id, serial; never secrets) | `utils/tse_client.py`, `config.py` | C6, P2 |
| G10 | ~~No preflight/dry-run endpoint~~ **closed 2026-11-13** (`POST /tse/init/preflight`: read-only state + expected writes) | `routers/tse.py:157`, `utils/tse_client.py` | all |
| G11 | ~~Server clock not validated~~ **closed 2026-11-13** (`_clock_error`: init refuses before any write unless NTP-synchronised; preflight reports it) | `utils/tse_client.py` | W1 |
| G12 | ~~`/tse/export/delete` only user-protected~~ **closed 2026-11-13** (`require_admin`) | `routers/tse.py` | R5 |

---

## 9. Preflight checklist for the one-shot run

Do this in order; stop at the first deviation.

1. **Values chosen and written down first.** All four values on paper (or a password
   manager), double-checked character by character, **before** the first HTTP call. PUKs
   are permanent.
2. **`.env` completed and the API restarted:** `TSE_DEVICE_PATH`, `TSE_TIME_ADMIN_PIN`
   (**exactly** the value to be used at commissioning), optionally `TSE_CLIENT_ID`,
   `TSE_ID`. Verify the loaded value, e.g.
   `python/venv/bin/python -c "from python import config; print(config.tse_time_admin_pin())"`.
3. **NTP/clock:** `timedatectl` shows synchronised; the host timezone is correct.
4. **Java POS closed** and no other process on the device (`fuser -v /dev/ttyACM*`).
5. **Read-only hardware check with the vendor tool** (no PIN writes — built with
   `TEST_TOOL=1`, it only runs `runTests()` + `exportAll()`):
   `assets/SE-API-C/bin/tse-test /dev/ttyACM0`
   It prints the SE-API version, PIN states, LCS, serial number, counters, memory and
   temperature. Expected on a new device: `pin_state != 0` (transport bits set) and LCS
   `notInitialized`. **Do not run `assets/SE-API-C/bin/se-api-c-test`** — it runs
   `firstBootTest` itself.
6. **API preflight:** `POST /tse/init/preflight` with the four values — read-only, returns
   what would be written and whether everything is consistent (G10).
7. **Two-person protocol:** one reads the value aloud, the other types it; use the GUI's
   double-entry confirmation; submit exactly once.
8. **After success:** verify with `GET /tse/status` (`pin_state == 0`, LCS `active`,
   `tse.serial_number` present), then restart the API once and confirm the time sync works
   with `.env` (no `time_error`), then make one test sale and one storno.
9. **If an attempt fails:** do not change any value. Read the reported state, re-use
   **exactly the same** four values for the retry (see the recovery matrix).

---

## 10. Recovery matrix

| State after an attempt | Safe action |
|---|---|
| `pin_state != 0`, nothing written yet | Retry with corrected values; nothing is set |
| Some PUK/PIN bits set, all values known | Retry with **identical** values (the bit-guard skips written fields) |
| PUK written, `se_unblockUser` failed | Retry once with the same PUK/PIN; if it fails again, stop |
| Retry must use a different PUK than before | **Stop.** Wrong PUKs can block the PUK permanently (C4) |
| LCS `noTime`, PINs known | Re-run init (or `ensure_ready`) to set the time |
| LCS `active`, client id wrong | Re-register (Admin) — needs the Admin PIN |
| TimeAdmin PIN unknown, PUK known | `POST /tse/unblock` with the PUK and `TSE_TIME_ADMIN_PIN` (2026-11-13) |
| `.env` value wrong | Fix `.env`, restart; watch for burnt retries |
| PUK lost/wrong | Not recoverable in the field; contact the manufacturer |

---

## 11. Prevention backlog

Must be done **before** the live run (tracked in `TODO.md`):

1. ✅ `POST /tse/init` → `require_admin`; refuse when `pin_state == 0` (already commissioned) and point to `ensure_ready` for time refresh (G1+G4, 2026-11-13).
2. ✅ Single source of truth for the TimeAdmin PIN: the body value must equal
   `TSE_TIME_ADMIN_PIN`, otherwise 400 **before** any write (G2, 2026-11-13).
3. ✅ Byte-accurate validation of all four values before opening the device: exact ASCII byte
   length, printable charset, no whitespace, no control characters (G5, 2026-11-13).
4. ✅ Read-only preflight endpoint that reports library version, device path, `pin_state`,
   LCS, client-id length, `.env` consistency, server clock, and whether commissioning is
   possible — without a single write (G10, 2026-11-13).
5. ✅ `threading.RLock` around all SE-API calls and keep the API at one worker
   (G7, 2026-11-13).
6. ✅ Partial-state policy: never call `se_unblockUser` with a PUK that this request did not
   just install, unless the caller explicitly confirms "these are the PUKs already stored"
   (`confirm_stored_puks=true`). Default: refuse and report which fields are already set
   (G6, 2026-11-13).
7. **Done (2026-11-13):** Guard `_ensure_time`: skip unless `pin_state == 0` and LCS is `noTime`/`active`.
8. ✅ Report `unblockResult` and `remainingRetries` in the response and stop on the first
   failure (never loop retries) (G8, 2026-11-13).
9. ✅ Record commissioning progress server-side (which fields were set, timestamps, client id
   — **never the secrets**) so a retry knows what happened (G9, 2026-11-13).
10. ✅ `/tse/export/delete` → `require_admin` (G12, 2026-11-13).
11. ✅ Repair endpoint `POST /tse/unblock` for `se_unblockUser` (Admin/TimeAdmin) so a
    lost/blocked PIN is recoverable with the PUK (admin-only, same byte validation as init,
    TimeAdmin keeps `TSE_TIME_ADMIN_PIN`; 2026-11-13).
12. Client GUI (see §12) with masked double-entry, confirmation, preflight button, and
    clear per-field reporting.
13. ✅ Validate the server clock before commissioning: `initialize()` refuses before any
    write unless `timedatectl` confirms `NTPSynchronized=yes`; preflight reports it
    (G11, 2026-11-13).

---

## 12. GUI before the hardware run?

**Recommendation: yes — but the GUI is the ergonomics layer, not the safety layer.**

Arguments for doing login + TSE init in `../wlkclient` first:

- A token is required for `/tse/init` anyway; login is a prerequisite.
- Double-entry, masked fields, a "I wrote the PUKs down" checkbox and a disabled submit
  button eliminate most human-error pathways (C1, C2, C6) far better than a JSON request.
- A preflight button can show the live `pin_state`/LCS and the exact four values that will
  be written, and the result screen can report each field.
- The whole HTTP flow can be rehearsed end-to-end against the library-less stub
  (`lib is None`) before any hardware is touched.

Arguments against relying on it:

- The GUI cannot make the operation non-atomic; only the server-side guards (G1–G12) can.
- If the GUI is used from a laptop over plain HTTP, the PUKs cross the network; the
  commissioning screen should run on the server host or behind TLS.
- GUI state is ephemeral; the record of what was written must live on the server.

Suggested order: server safeguards (1–11) → GUI login + TSE init screen → dry run through
the GUI against the stub → vendor read-only `tse-test` → the one live attempt following
the checklist. This keeps the one-shot risk out of the UI code.
