# Kassenstand and Abrechnung (cash drawer and settlements)

How the API records cash, how a cashier counts the drawer down to its target
stock, and how the day/month/year are closed. All amounts are EUR.

Two independent things are involved:

1. **The Kassenstand ledger** (`kassenstand`) is append-only. Every cash sale
   and every cash refund writes an entry with `manuell = false`. A physical
   count, a correction or an `Entnahme` (cash withdrawal) is a **manual entry**
   (`manuell = true`). `neuer_kassenstand` is always the balance *after* the
   entry, never a delta.
2. **The target drawer stock** (`SOLL_MUENZ_KASSENSTAND`, default `50.00`, and
   `SOLL_SCHEIN_KASSENSTAND`, default `100.00`, Java `sollMuenzKassenstand` /
   `sollScheinKassenstand`) is only used by the reset suggestion. It is not
   stored and does not influence any booking.

## End-of-day sequence

```
GET  /abrechnung/tag/vorschau            # what happened since the last settlement?
POST /kassenstand/zuruecksetzen/vorschau # counted coins/notes -> what to remove/exchange
POST /kassenstand/                       # book the counted balance (manual entry)
POST /abrechnung/tag/                    # close the day (optional Zählprotokoll)
GET  /abrechnung/tag/{id}                # the stored settlement incl. VAT per rate
```

Month and year are closed after their days: `POST /abrechnung/monat/`,
`POST /abrechnung/jahr/`. A backdated daily settlement deletes the month/year
settlement that covers it, so the next `POST /abrechnung/monat|jahr` recreates
them.

---

## `POST /kassenstand/zuruecksetzen/vorschau`

Read-only suggestion for bringing the counted drawer back to the target stock
(Java `KassenstandZuruecksetzenDialog`). Nothing is written; the reset itself is
the manual `POST /kassenstand/` entry.

Request: the count in the same shape as the `zaehlprotokoll` detail rows —
denomination (`einheit`) and number of pieces (`anzahl`). Missing denominations
count as zero, unknown ones are rejected with `400`.

```json
[
  {"einheit": 10.0, "anzahl": 3}, {"einheit": 5.0, "anzahl": 2},
  {"einheit": 2.0, "anzahl": 18}, {"einheit": 1.0, "anzahl": 6},
  {"einheit": 0.10, "anzahl": 3}, {"einheit": 0.01, "anzahl": 5}
]
```

Response — drawer too low, nothing to exchange:

```json
{
  "soll_scheine": 100.0, "soll_muenzen": 50.0, "soll_kassenstand": 150.0,
  "gezaehlt_scheine": 40.0, "gezaehlt_muenzen": 42.35, "gezaehlt_kassenstand": 82.35,
  "entnahme": -67.65,
  "tausch": 0.0,
  "scheine_delta": 60.0, "muenzen_delta": 7.65
}
```

Response — 130.00 EUR in notes, 42.35 EUR in coins (notes too many, coins too
few, 22.35 EUR too much in the drawer):

```json
{
  "soll_scheine": 100.0, "soll_muenzen": 50.0, "soll_kassenstand": 150.0,
  "gezaehlt_scheine": 130.0, "gezaehlt_muenzen": 42.35, "gezaehlt_kassenstand": 172.35,
  "entnahme": 22.35,
  "tausch": 10.0,
  "scheine_delta": -20.0, "muenzen_delta": -2.35
}
```

How to read it:

- `entnahme` — net change of the drawer total. Positive: that much money must
  leave the drawer. Negative: that much must be added from the spare-change till.
  It is `gezaehlt_kassenstand - soll_kassenstand`.
- `tausch` — amount exchanged between notes and coins with the spare-change till.
  **Positive: notes out, coins in. Negative: coins out, notes in.** Only whole
  notes are exchanged (`5/10/20/50/100/200`).
- `scheine_delta` / `muenzen_delta` — signed change of each bucket *after* the
  exchange. Positive: take that much from the spare till. Negative: remove it
  from the drawer.

Apply `tausch` first, then both deltas — the drawer always ends at exactly
`soll_scheine` in notes and `soll_muenzen` in coins:

| counted | tausch | scheine_delta | muenzen_delta | result |
|---|---|---|---|---|
| 110 / 20 | +10.00 | 0.00 | +20.00 | exchange 10 notes to coins, add 20 coins |
| 130 / 42.35 | +10.00 | −20.00 | −2.35 | exchange 10, remove 20 notes and 2.35 coins |
| 90 / 70 | −10.00 | 0.00 | −10.00 | exchange 10 coins to notes, remove 10 coins |
| 120 / 60 | 0.00 | −20.00 | −10.00 | remove 20 notes and 10 coins |
| 90 / 40 | 0.00 | +10.00 | +10.00 | add 10 notes and 10 coins |

The drawer's note stock is always a whole multiple of 5 EUR (all notes are), so a
note movement is always expressible; the exchange is capped so that neither more
notes nor more coins leave the drawer than are counted.

---

## `POST /kassenstand/` — book the counted balance

The cashier enters the balance that is physically in the drawer (usually
`soll_kassenstand` after following the suggestion). This is the "Kassenstand
zurücksetzen" action of the Java POS.

```json
{"neuer_kassenstand": 150.0, "manuell": true, "kommentar": "Gezaehlter Kassenstand"}
```

Response (`KassenstandPublic`):

```json
{
  "kassenstand_id": 4,
  "buchungsdatum": "2026-10-31T11:25:43.691289Z",
  "neuer_kassenstand": 150.0,
  "manuell": true,
  "entnahme": false,
  "rechnungs_nr": null,
  "kommentar": "Gezaehlter Kassenstand"
}
```

Fields:

- `neuer_kassenstand` — the new balance after the entry, `>= 0` (`422` otherwise).
  It is an absolute balance, not a difference.
- `manuell` — `true` for anything entered by hand. The default list
  (`GET /kassenstand/`) only shows manual entries; sale entries only appear with
  `?rechnungen=true`.
- `entnahme` — a cash withdrawal (money leaves the shop). The new balance must be
  lower than the previous one and must not go below zero, otherwise `400`. An
  `Entnahme` is a manual entry with `manuell: true`; "Tagesabschluss" is not one.
- `rechnungs_nr` — optional link to a receipt; the receipt must exist (`400`).
- `kommentar` — free text, max. 70 characters. Use `"Tagesabschluss"` for the
  closing count, so it is recognizable in the ledger.
- The entry is attributed to the authenticated user (`user_id` from the token).

Reading the ledger:

- `GET /kassenstand/` — manual entries, newest first. Filters: `rechnungen=true`
  (include sale entries), `von` / `bis` (ISO datetimes), `offset` / `limit`
  (max 100).
- `GET /kassenstand/aktuell` — the last entry, `null` if the drawer has never been
  booked. `neuer_kassenstand` is the current expected balance.
- `GET /kassenstand/{kassenstand_id}` — single entry.

---

## `GET /abrechnung/tag/vorschau` — what is open

Read-only preview of the open day (nothing is written; same calculation as the
settlement itself, so preview and booking cannot drift apart).

```json
{
  "open": true,
  "rechnungs_nr_von": 1, "rechnungs_nr_bis": 3,
  "sales": 3, "cash_sales": 3, "ec_sales": 0,
  "stornos": 0, "storno_summe": 0.0, "retouren_summe": 0.0,
  "mwst": [
    {"mwst_satz": 0.19, "mwst_netto": 42.02, "mwst_betrag": 7.98, "bar_brutto": 50.0}
  ],
  "current_balance": 30.0,
  "entnahmen": 0.0,
  "expected_balance": 30.0
}
```

- The period is every receipt after the last settlement's `rechnungs_nr_bis`.
  `open: false` with `null` ranges means there is nothing to settle yet.
- `mwst_netto` / `mwst_betrag` come from the stored VAT rows of the receipts;
  `bar_brutto` is the gross sum of the **cash** (non-EC) receipt positions of that
  VAT rate, including stornos as negative values.
- `storno_summe` is the cancelled original amount (positive), `retouren_summe` the
  sum of negative-quantity positions.
- `entnahmen` is the sum of cash withdrawals since the previous settlement.
- `current_balance` is the last Kassenstand entry. `expected_balance` equals it,
  because the ledger already contains every cash movement of the period.

`GET /abrechnung/tag/offen` lists the dates (`YYYY-MM-DD`) of unsettled receipts;
`GET /abrechnung/tag/` lists the stored settlements.

## `POST /abrechnung/tag/` — close the day

All fields are optional:

```json
{
  "zeitpunkt": "2026-10-31T20:00:00Z",
  "rechnungs_nr_von": null,
  "rechnungs_nr_bis": null,
  "kassenstand_id": null,
  "z_kasse_id": null,
  "last_tse_sig_counter": null,
  "zaehlprotokoll": {
    "kommentar": "Abendzählung",
    "details": [{"einheit": 10.0, "anzahl": 3}, {"einheit": 2.0, "anzahl": 18}]
  }
}
```

Response:

```json
{
  "id": 1,
  "z_kasse_id": "1",
  "zeitpunkt": "2026-10-31T11:25:43.716139Z",
  "zeitpunkt_real": "2026-10-31T11:25:43.716139Z",
  "kassenstand_id": 4,
  "rechnungs_nr_von": 1, "rechnungs_nr_bis": 3,
  "last_tse_sig_counter": null,
  "user_id": 1,
  "storno_summe": 0.0, "retouren_summe": 0.0,
  "mwst_nach_id": {"1": [0.19, 42.02, 7.98, 50.0]}
}
```

- Without `rechnungs_nr_von/bis` the open period is settled; with both, a backdated
  explicit range (the month/year settlements covering it are deleted and become
  due again).
- `kassenstand_id` defaults to the **latest** Kassenstand entry — which is why the
  counted balance must be booked with `POST /kassenstand/` *before* closing. A
  closing balance is never invented by the settlement.
- `zeitpunkt` is the accounting time, `zeitpunkt_real` the wall clock; both
  default to now, `zeitpunkt` is what decides month/year membership.
- `last_tse_sig_counter` normally comes from the TSE export performed during the
  settlement; set it explicitly for scripts/manual exports (it also becomes the
  start of the next export). Without a TSE it stays `null`.
- `zaehlprotokoll` is inserted after the settlement, and deactivates previous
  active counts of the same settlement.
- `mwst_nach_id` maps VAT ID → `[rate, netto, betrag, brutto]` (Java
  `getAllCurrentMwstValuesByID`), computed from the settled receipts.
- Side effects: one `abrechnung_tag_tse` status row, a best-effort incremental TSE
  export and (when `DSFINVK_EXPORT_DIR` is set) a `dsfinvk_<id>.zip`. All are
  skipped in training mode; the DSFinV-K ZIP can always be fetched with
  `GET /export/dsfinvk/{id}`.
- `400` when there is nothing to settle (`"No sales to settle"`) or the explicit
  range contains no sales.

`GET /abrechnung/tag/{id}` returns the stored settlement plus the `mwst` rows:

```json
{
  "id": 1, "z_kasse_id": "1", "kassenstand_id": 4,
  "rechnungs_nr_von": 1, "rechnungs_nr_bis": 3,
  "storno_summe": null, "retouren_summe": null, "mwst_nach_id": null,
  "mwst": [
    {"id": 1, "mwst_satz": 0.19, "mwst_netto": 42.02, "mwst_betrag": 7.98, "bar_brutto": 50.0}
  ]
}
```

Note: `storno_summe`, `retouren_summe` and `mwst_nach_id` are computed while
creating and are **not stored** — they are `null` on `GET`. Recompute them from
`GET /verkauf/?von=..&bis=..` (or from `GET /abrechnung/tag/vorschau` before
closing) if a client needs them later.

## Month and year

- `GET /abrechnung/monat/offen` / `GET /abrechnung/jahr/offen` — due periods
  (`YYYY-MM`, `YYYY`).
- `POST /abrechnung/monat/` with `{"monat": "2026-10"}` (or nothing = earliest
  unsettled month) aggregates the daily settlements of that month, including
  `bar_brutto`. `POST /abrechnung/jahr/` works the same per year. Both require
  existing daily settlements (`400` otherwise) and replace an existing settlement
  of the same period.
- `GET /abrechnung/monat/{id}` / `GET /abrechnung/jahr/{id}` add the `mwst` array.

## Zählprotokoll

`POST /zaehlprotokoll` stores a count that belongs to an existing settlement
(`abrechnung_tag_id` required, `400` otherwise); previous active counts of that
settlement are deactivated. The count is usually submitted with the settlement
itself (see above).

---

## Errors and caveats

| status | reason |
|---|---|
| `400` | unknown denomination, `Entnahme` increasing the balance, receipt not found, nothing to settle, Zählprotokoll without settlement |
| `401` | missing/invalid token (all endpoints require `Authorization: Bearer`) |
| `404` | unknown `kassenstand_id`, `tag_id`, receipt |
| `422` | negative `neuer_kassenstand`, invalid `von`/`bis` datetime, unknown field values |

- Money is serialized as JSON floats; treat it as cents-precision and round after
  summing (the Java POS uses `BigDecimal`, the API `Decimal` internally).
- `verkauf`, `kassenstand`, `gutschein`, `anzahlung` and `abrechnung_tag` are
  immutable: no update/delete endpoints. Corrections are new entries (Storno).
- Cash balance writes are serialized per process (`KASSENSTAND_LOCK`) and by
  `SELECT ... FOR UPDATE` on MariaDB; run a single API worker if scripts and the
  POS write simultaneously.
- `GET /kassenstand/` shows manual entries by default — use `?rechnungen=true` to
  see the sale entries of the ledger.
