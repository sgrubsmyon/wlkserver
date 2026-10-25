# VAT rounding in Germany — research result and decision

Status: 2026-10-25. Applies to `python/business/vat_calculator.py` and the Java POS
behaviour it mirrors.

## Question

The Python VAT module rounds VAT amounts to cents with `ROUND_HALF_UP` (commercial
rounding, "kaufmännisches Runden"). Was that mandated by German law, or is it just
what the Java POS happened to do?

## Findings

1. **German law does not prescribe a rounding mode for VAT amounts on invoices.**
   § 14 UStG only requires that an invoice shows the applicable VAT rate and the VAT
   amount falling on the consideration, broken down by rate (§ 14 Abs. 4 Nr. 7 and 8
   UStG). § 33 UStDV (small-amount invoices) contains no rounding rule either. No
   provision in the UStG/UStDV says "round up", "round down" or "round half up".

2. **EU law leaves the method to the Member States.** EuGH, judgment of 10.07.2008,
   C-484/06 (*Fiscale eenheid Koninklijke Ahold*): in the absence of a specific
   Community rule, it is for the Member States to determine the rules and methods for
   rounding VAT amounts, subject to the principles of the VAT system (notably fiscal
   neutrality and proportionality). The Court did **not** require that rounding down
   per sold item be permitted. The related judgment C-302/07 (05.03.2009) confirms that
   rounding is necessary where net prices are round figures.

3. **German practice rounds commercially to cents.** Accounting/ERP and e-invoicing
   tooling describes the standard as "kaufmännisch auf zwei Nachkommastellen runden"
   (round half away from zero). This is practice, not a statutory command.

4. **Two different levels must not be confused.**
   - *Invoice/receipt level*: amounts are stated in euro and cents. For the
     Umsatzsteuer-Voranmeldung, ELSTER explicitly requires the tax amounts **with
     cents** while the taxable bases are entered in **full euro** ("bei den
     Umsatzsteuer- und Vorsteuerbeträgen ist ... stets auch die Eintragung von
     Centbeträgen erforderlich").
   - *Declaration level*: only the declaration rounds to full euro; that has no
     influence on how a receipt is calculated.

5. **Per-item vs per-rate rounding can differ by cents, and both occur in practice.**
   - *Horizontal method*: round the VAT of each line item, then sum (this is what the
     Java POS does: `calculateVAT` per article).
   - *Vertical method*: sum the gross amounts per VAT rate first, then compute VAT once
     from that total.
   Both are used in German practice; what matters is that the method is applied
   consistently and stays traceable (GoBD: § 146 AO, traceability and
   verifiability of the records).

6. **E-invoicing has its own rule.** EN 16931 (and therefore XRechnung/ZUGFeRD) rule
   **BR-CO-17** derives the VAT amount of a VAT category group (BT-117) from the
   category taxable amount (BT-116) times the category rate (BT-119), rounded to two
   decimals. That is the *vertical* method per tax category. Receipts under
   § 146a AO (Kassenbelege) are not B2B e-invoices, so this does not change the POS
   today, but it matters if invoices are generated later.

## Conclusion for this project

- Keep `ROUND_HALF_UP` to cents. It is the commercial standard, matches the Java POS
  (`RoundingMode.HALF_UP` in `BaseClass.priceFormatterIntern` and
  `WindowContent.calculateVAT`), and is not contradicted by any German rule. The Java
  rounding mode was an explicit choice, not an accident of formatting.
- Keep the **horizontal per-position** rounding for sales receipts, because the Java
  POS does it and the receipt shows per-item prices. Do not mix methods within one
  document.
- If B2B e-invoices (EN 16931/XRechnung) are added later, compute the VAT amount per
  VAT category from the summed category gross/taxable amount (BR-CO-17) instead of
  adding per-line VAT. The difference is at most a few cents and must be documented on
  the document.
- Cash rounding to 5 cents is **not** required in Germany (1- and 2-cent coins are
  legal tender) and is not implemented.

## Sources

- § 14 UStG (invoice contents): https://www.gesetze-im-internet.de/ustg_1980/__14.html
- § 33 UStDV (small-amount invoices): https://www.gesetze-im-internet.de/ustdv_1980/__33.html
- EuGH C-484/06, 10.07.2008 (rounding is Member State competence):
  https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:62006CJ0484
- EuGH C-302/07, 05.03.2009 (rounding necessary for round net prices):
  https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:62007CJ0302
- ELSTER help, Umsatzsteuer-Voranmeldung (tax amounts with cents, bases in full euro):
  https://www.elster.de/eportal/helpGlobal?themaGlobal=help_ustva_2022
- EN 16931 business rule BR-CO-17 (VAT category tax amount):
  https://docs.peppol.eu/poacc/billing/3.0/rules/ubl-tc434/BR-CO-17/
- Practice of commercial rounding to cents (software documentation):
  https://www.123rechnung.com/kb/rundungsdifferenzen-bei-der-mwst-ust-berechnung/
