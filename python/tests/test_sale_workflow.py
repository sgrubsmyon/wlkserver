import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlmodel import select

from python.models import (
    Artikel, Produktgruppe, Lieferant, Mwst, Rabattaktion,
    Verkauf, VerkaufDetails, VerkaufDetailsCreate, VerkaufMwst,
)
from python.business.sale_workflow import (
    validate_detail,
    determine_mwst_satz,
    determine_ges_preis,
    prepare_detail,
    calculate_mwst_summary,
    check_ec_payment_threshold,
)


def _seed_mwst(session, mwst_satz=0.19):
    m = Mwst(mwst_satz=mwst_satz, dsfinvk_ust_schluessel=1)
    m.mwst_id = None
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def _seed_pg(session, mwst_satz=0.19):
    m = _seed_mwst(session, mwst_satz=mwst_satz)
    pg = Produktgruppe(produktgruppen_name="Test PG", mwst_id=m.mwst_id)
    pg.produktgruppen_id = None
    session.add(pg)
    session.commit()
    session.refresh(pg)
    return pg


def _seed_lieferant(session):
    l = Lieferant(lieferant_name="Test Lieferant")
    l.lieferant_id = None
    session.add(l)
    session.commit()
    session.refresh(l)
    return l


def _seed_artikel(session, mwst_satz=0.19, vk_preis=10.0, variabler_preis=False, artikel_nr="001"):
    pg = _seed_pg(session, mwst_satz=mwst_satz)
    l = _seed_lieferant(session)
    a = Artikel(
        artikel_nr=artikel_nr,
        artikel_name="Test Artikel",
        produktgruppen_id=pg.produktgruppen_id,
        lieferant_id=l.lieferant_id,
        vk_preis=vk_preis,
        variabler_preis=variabler_preis,
    )
    a.artikel_id = None
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_validate_detail_zero_stueckzahl(session):
    with pytest.raises(Exception) as exc:
        validate_detail(session, {"stueckzahl": 0})
    assert "stueckzahl" in str(exc.value)


def test_validate_detail_positive_stueckzahl(session):
    validate_detail(session, {"stueckzahl": 2})


def test_determine_mwst_satz_explicit(session):
    satz = determine_mwst_satz(session, {"mwst_satz": 0.07, "stueckzahl": 1})
    assert satz == 0.07


def test_determine_mwst_satz_none(session):
    satz = determine_mwst_satz(session, {"stueckzahl": 1})
    assert satz is None


def test_determine_ges_preis_explicit(session):
    preis = determine_ges_preis(session, {"ges_preis": 25.50, "stueckzahl": 1})
    assert preis == 25.50


def test_determine_ges_preis_from_artikel(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    preis = determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 3})
    assert preis == 30.0


def test_determine_ges_preis_variabler_preis_returns_none(session):
    artikel = _seed_artikel(session, vk_preis=10.0, variabler_preis=True)
    preis = determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 2})
    assert preis is None


def test_prepare_detail_fills_mwst_and_preis(session):
    artikel = _seed_artikel(session, mwst_satz=0.19, vk_preis=10.0)
    d = {"artikel_id": artikel.artikel_id, "stueckzahl": 2}
    vd = prepare_detail(session, d)
    assert vd.mwst_satz == 0.19
    assert vd.ges_preis == 20.0
    assert vd.stueckzahl == 2


def test_prepare_detail_from_verkaufdetailscreate(session):
    artikel = _seed_artikel(session, mwst_satz=0.19, vk_preis=10.0)
    d = VerkaufDetailsCreate(
        artikel_id=artikel.artikel_id, stueckzahl=2,
        mwst_satz=None, ges_preis=None, rechnungs_nr=1,
    )
    vd = prepare_detail(session, d)
    assert vd.mwst_satz == 0.19
    assert vd.ges_preis == 20.0
    assert vd.stueckzahl == 2


def test_calculate_mwst_summary(session):
    details = [
        VerkaufDetails(ges_preis=119.00, mwst_satz=0.19, rechnungs_nr=1, position=1, stueckzahl=1),
        VerkaufDetails(ges_preis=119.00, mwst_satz=0.19, rechnungs_nr=1, position=2, stueckzahl=1),
    ]
    summary = calculate_mwst_summary(details)
    rate = Decimal("0.19")
    assert rate in summary
    assert summary[rate]["brutto"] == Decimal("238.00")
    assert summary[rate]["mwst_betrag"] == Decimal("38.00")
    assert summary[rate]["mwst_netto"] == Decimal("200.00")


def test_calculate_mwst_summary_horizontal_vs_vertical(session, monkeypatch):
    # two positions of 0.03 at 20 %: horizontal rounds each line (0.01 + 0.01),
    # vertical rounds the rate total (0.06 -> 0.01)
    details = [
        VerkaufDetails(ges_preis=0.03, mwst_satz=0.20, rechnungs_nr=1, position=1, stueckzahl=1),
        VerkaufDetails(ges_preis=0.03, mwst_satz=0.20, rechnungs_nr=1, position=2, stueckzahl=1),
    ]
    monkeypatch.setenv("VAT_ROUNDING_METHOD", "horizontal")
    assert calculate_mwst_summary(details)[Decimal("0.20")]["mwst_betrag"] == Decimal("0.02")

    monkeypatch.setenv("VAT_ROUNDING_METHOD", "vertical")
    assert calculate_mwst_summary(details)[Decimal("0.20")]["mwst_betrag"] == Decimal("0.01")


def test_check_ec_threshold_below(session):
    warning = check_ec_payment_threshold(Decimal("5.00"), True)
    assert warning is not None
    assert "10,00" in warning


def test_check_ec_threshold_above(session):
    warning = check_ec_payment_threshold(Decimal("15.00"), True)
    assert warning is None


def test_check_ec_threshold_cash(session):
    warning = check_ec_payment_threshold(Decimal("5.00"), False)
    assert warning is None


# ------------------------------------------------------------ discounts

def _seed_rabatt(session, **kwargs):
    now = datetime.now(timezone.utc)
    values = {"aktionsname": "Aktion", "von": now - timedelta(days=1), "bis": None}
    values.update(kwargs)
    r = Rabattaktion(**values)
    r.rabatt_id = None
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


def test_determine_ges_preis_applies_active_article_rabatt(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(session, artikel_id=artikel.artikel_id, rabatt_relativ=0.10)
    assert determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 2}) == 18.0


def test_determine_ges_preis_ignores_expired_rabatt(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(
        session, artikel_id=artikel.artikel_id, rabatt_relativ=0.10,
        von=datetime.now(timezone.utc) - timedelta(days=10),
        bis=datetime.now(timezone.utc) - timedelta(days=5),
    )
    assert determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 2}) == 20.0


def test_determine_ges_preis_ignores_future_rabatt(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(
        session, artikel_id=artikel.artikel_id, rabatt_relativ=0.10,
        von=datetime.now(timezone.utc) + timedelta(days=5), bis=None,
    )
    assert determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 1}) == 10.0


def test_determine_ges_preis_applies_group_rabatt_with_wildcards(session):
    # action on the top-level group (sub/subsub NULL) applies to a nested article group
    top = _seed_pg(session, mwst_satz=0.19)
    nested = Produktgruppe(produktgruppen_name="Nested", toplevel_id=top.toplevel_id,
                          sub_id=5, subsub_id=7, mwst_id=top.mwst_id)
    session.add(nested)
    session.commit()
    session.refresh(nested)
    l = _seed_lieferant(session)
    a = Artikel(artikel_nr="G1", artikel_name="Gruppenartikel",
                produktgruppen_id=nested.produktgruppen_id, lieferant_id=l.lieferant_id,
                vk_preis=10.0)
    session.add(a)
    session.commit()
    session.refresh(a)

    _seed_rabatt(session, produktgruppen_id=top.produktgruppen_id, rabatt_absolut=2.0)
    assert determine_ges_preis(session, {"artikel_id": a.artikel_id, "stueckzahl": 3}) == 24.0


def test_determine_ges_preis_ignores_group_rabatt_for_other_group(session):
    pg = _seed_pg(session)
    other = Produktgruppe(produktgruppen_name="Other", toplevel_id=99, mwst_id=pg.mwst_id)
    session.add(other)
    session.commit()
    session.refresh(other)
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(session, produktgruppen_id=other.produktgruppen_id, rabatt_absolut=5.0)
    assert determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 1}) == 10.0


def test_explicit_rabatt_id_overrides_automatic_ones(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(session, artikel_id=artikel.artikel_id, rabatt_relativ=0.10)
    explicit = _seed_rabatt(session, artikel_id=artikel.artikel_id, rabatt_relativ=0.30)
    price = determine_ges_preis(session, {
        "artikel_id": artikel.artikel_id, "stueckzahl": 1, "rabatt_id": explicit.rabatt_id,
    })
    assert price == 7.0


def test_explicit_rabatt_id_must_match_article(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    other = _seed_artikel(session, artikel_nr="A2", vk_preis=10.0)
    foreign = _seed_rabatt(session, artikel_id=other.artikel_id, rabatt_relativ=0.10)
    with pytest.raises(Exception) as exc:
        determine_ges_preis(session, {
            "artikel_id": artikel.artikel_id, "stueckzahl": 1, "rabatt_id": foreign.rabatt_id,
        })
    assert "does not apply" in str(exc.value)


def test_explicit_expired_rabatt_id_is_rejected(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    expired = _seed_rabatt(
        session, artikel_id=artikel.artikel_id, rabatt_relativ=0.10,
        von=datetime.now(timezone.utc) - timedelta(days=10),
        bis=datetime.now(timezone.utc) - timedelta(days=1),
    )
    with pytest.raises(Exception) as exc:
        determine_ges_preis(session, {
            "artikel_id": artikel.artikel_id, "stueckzahl": 1, "rabatt_id": expired.rabatt_id,
        })
    assert "expired" in str(exc.value)


def test_determine_ges_preis_stacks_absolute_then_relative(session):
    # Java order: absolute first, then relative on the reduced unit price
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(session, artikel_id=artikel.artikel_id, rabatt_absolut=1.0, rabatt_relativ=0.10)
    assert determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 1}) == 8.1


def test_determine_ges_preis_quantity_relative(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(session, artikel_id=artikel.artikel_id,
                 mengenrabatt_schwelle=3, mengenrabatt_relativ=0.10)
    assert determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 2}) == 20.0
    assert determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 3}) == 27.0


def test_determine_ges_preis_free_items(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(session, artikel_id=artikel.artikel_id,
                 mengenrabatt_schwelle=2, mengenrabatt_anzahl_kostenlos=1)
    # 4 pieces, every 2nd free -> 2 paid
    assert determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 4}) == 20.0


def test_determine_ges_preis_rejects_discount_above_price(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(session, artikel_id=artikel.artikel_id, rabatt_absolut=20.0)
    with pytest.raises(Exception) as exc:
        determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 1})
    assert "exceeds" in str(exc.value)


def test_prepare_detail_records_auto_rabatt_id(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    action = _seed_rabatt(session, artikel_id=artikel.artikel_id, rabatt_relativ=0.10)
    vd = prepare_detail(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 1})
    assert vd.rabatt_id == action.rabatt_id
    assert vd.ges_preis == 9.0


def test_prepare_detail_keeps_explicit_price(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(session, artikel_id=artikel.artikel_id, rabatt_relativ=0.10)
    vd = prepare_detail(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 1, "ges_preis": 7.5})
    assert vd.ges_preis == 7.5
    assert vd.rabatt_id is None


def test_rabatt_without_target_is_ignored(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(session, rabatt_relativ=0.10)
    assert determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 1}) == 10.0


def test_group_rabatt_with_sub_mismatch_is_ignored(session):
    pg = _seed_pg(session)
    nested = Produktgruppe(produktgruppen_name="Nested", toplevel_id=pg.toplevel_id,
                          sub_id=2, subsub_id=7, mwst_id=pg.mwst_id)
    session.add(nested)
    session.commit()
    session.refresh(nested)
    l = _seed_lieferant(session)
    a = Artikel(artikel_nr="G2", artikel_name="Gruppenartikel 2",
                produktgruppen_id=nested.produktgruppen_id, lieferant_id=l.lieferant_id,
                vk_preis=10.0)
    session.add(a)
    session.commit()
    session.refresh(a)

    action_pg = Produktgruppe(produktgruppen_name="Action", toplevel_id=pg.toplevel_id,
                              sub_id=1, subsub_id=7, mwst_id=pg.mwst_id)
    session.add(action_pg)
    session.commit()
    session.refresh(action_pg)
    _seed_rabatt(session, produktgruppen_id=action_pg.produktgruppen_id, rabatt_absolut=2.0)
    assert determine_ges_preis(session, {"artikel_id": a.artikel_id, "stueckzahl": 1}) == 10.0


def test_group_rabatt_with_subsub_mismatch_is_ignored(session):
    pg = _seed_pg(session)
    nested = Produktgruppe(produktgruppen_name="Nested", toplevel_id=pg.toplevel_id,
                          sub_id=1, subsub_id=7, mwst_id=pg.mwst_id)
    session.add(nested)
    session.commit()
    session.refresh(nested)
    l = _seed_lieferant(session)
    a = Artikel(artikel_nr="G3", artikel_name="Gruppenartikel 3",
                produktgruppen_id=nested.produktgruppen_id, lieferant_id=l.lieferant_id,
                vk_preis=10.0)
    session.add(a)
    session.commit()
    session.refresh(a)

    action_pg = Produktgruppe(produktgruppen_name="Action", toplevel_id=pg.toplevel_id,
                              sub_id=1, subsub_id=9, mwst_id=pg.mwst_id)
    session.add(action_pg)
    session.commit()
    session.refresh(action_pg)
    _seed_rabatt(session, produktgruppen_id=action_pg.produktgruppen_id, rabatt_absolut=2.0)
    assert determine_ges_preis(session, {"artikel_id": a.artikel_id, "stueckzahl": 1}) == 10.0


def test_explicit_unknown_rabatt_rejected(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    with pytest.raises(Exception) as exc:
        determine_ges_preis(session, {
            "artikel_id": artikel.artikel_id, "stueckzahl": 1, "rabatt_id": 99999,
        })
    assert "not found" in str(exc.value)


def test_negative_quantity_ignores_discount(session):
    # storno positions keep the plain price (no discount on refunds)
    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_rabatt(session, artikel_id=artikel.artikel_id, rabatt_relativ=0.10)
    assert determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": -1}) == -10.0


def test_validate_detail_rejects_unknown_artikel(session):
    with pytest.raises(Exception) as exc:
        validate_detail(session, {"artikel_id": 99999, "stueckzahl": 1})
    assert "not found" in str(exc.value)


def test_validate_detail_rejects_unknown_rabatt(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    with pytest.raises(Exception) as exc:
        validate_detail(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 1, "rabatt_id": 99999})
    assert "not found" in str(exc.value)


def test_router_applies_discount_as_separate_rabatt_line(session):
    from python.routers.verkauf import create_verkauf as router_create_verkauf
    from python.models import VerkaufCreate

    artikel = _seed_artikel(session, vk_preis=10.0)
    _seed_artikel(session, artikel_nr="RABATT1", vk_preis=None)
    action = _seed_rabatt(session, artikel_id=artikel.artikel_id, rabatt_relativ=0.10)

    payload = VerkaufCreate(verkauf_details=[{"artikel_id": artikel.artikel_id, "stueckzahl": 2}])
    result = router_create_verkauf(payload, session, None, None)

    rows = sorted(result["verkauf_details"], key=lambda d: d.vd_id)
    assert [r.ges_preis for r in rows] == [20.0, -2.0]
    assert rows[0].position == 1
    assert rows[1].position is None
    assert rows[1].rabatt_id == action.rabatt_id


def test_router_adds_pfand_and_price_adjustment_lines(session):
    from python.routers.verkauf import create_verkauf as router_create_verkauf
    from python.models import VerkaufCreate, Pfand

    mwst = _seed_mwst(session, mwst_satz=0.19)
    lieferant = _seed_lieferant(session)
    deposit_pg = Produktgruppe(produktgruppen_name="Pfand", mwst_id=mwst.mwst_id)
    session.add(deposit_pg)
    session.commit()
    session.refresh(deposit_pg)
    deposit = Artikel(artikel_nr="PFAND3", artikel_name="Pfand 0,25",
                      produktgruppen_id=deposit_pg.produktgruppen_id,
                      lieferant_id=lieferant.lieferant_id, vk_preis=0.25)
    session.add(deposit)
    session.commit()
    session.refresh(deposit)
    pfand = Pfand(artikel_id=deposit.artikel_id)
    session.add(pfand)
    session.commit()
    session.refresh(pfand)

    pg = Produktgruppe(produktgruppen_name="Getränk", mwst_id=mwst.mwst_id,
                       pfand_id=pfand.pfand_id)
    session.add(pg)
    session.commit()
    session.refresh(pg)
    artikel = Artikel(artikel_nr="T1", artikel_name="Testgetränk",
                      produktgruppen_id=pg.produktgruppen_id,
                      lieferant_id=lieferant.lieferant_id, vk_preis=2.0)
    session.add(artikel)
    session.commit()
    session.refresh(artikel)
    _seed_artikel(session, artikel_nr="ANPASSUNG", vk_preis=None)
    anpassung = session.exec(select(Artikel).where(Artikel.artikel_nr == "ANPASSUNG")).one()

    payload = VerkaufCreate(verkauf_details=[
        {"artikel_id": artikel.artikel_id, "stueckzahl": 2, "rabatt_absolut": -1.0},
    ])
    result = router_create_verkauf(payload, session, None, None)

    rows = sorted(result["verkauf_details"], key=lambda d: d.vd_id)
    assert [r.ges_preis for r in rows] == [4.0, 2.0, 0.5]
    assert [r.artikel_id for r in rows] == [
        artikel.artikel_id, anpassung.artikel_id, deposit.artikel_id
    ]


def test_router_receipt_discount_one_line_per_vat_rate(session):
    from python.routers.verkauf import create_verkauf as router_create_verkauf
    from python.models import VerkaufCreate

    a = _seed_artikel(session, mwst_satz=0.19, vk_preis=10.0, artikel_nr="A1")
    b = _seed_artikel(session, mwst_satz=0.07, vk_preis=20.0, artikel_nr="A2")
    _seed_artikel(session, artikel_nr="RABATT2", vk_preis=None)

    payload = VerkaufCreate(
        rechnung_rabatt_relativ=0.10,
        verkauf_details=[
            {"artikel_id": a.artikel_id, "stueckzahl": 1},
            {"artikel_id": b.artikel_id, "stueckzahl": 1},
        ],
    )
    result = router_create_verkauf(payload, session, None, None)
    rows = sorted(result["verkauf_details"], key=lambda d: d.vd_id)
    assert [(r.mwst_satz, r.ges_preis) for r in rows] == [
        (0.19, 10.0), (0.07, 20.0), (0.19, -1.0), (0.07, -2.0)
    ]


def test_router_redeems_voucher_as_sale_position(session):
    from python.routers.verkauf import create_verkauf as router_create_verkauf
    from python.models import VerkaufCreate, Gutschein

    artikel = _seed_artikel(session, vk_preis=20.0)
    _seed_artikel(session, artikel_nr="GUTSCHEINEINLOES", vk_preis=None, mwst_satz=0.07)
    g = Gutschein(gutschein_nr=200, datum=datetime.now(timezone.utc),
                  gutschein_in_vd_id=None, einloesung_in_vd_id=None, restbetrag=10.0)
    session.add(g)
    session.commit()

    payload = VerkaufCreate(
        gutschein_einloesung_nr=200,
        verkauf_details=[{"artikel_id": artikel.artikel_id, "stueckzahl": 1}],
    )
    result = router_create_verkauf(payload, session, None, None)
    rows = sorted(result["verkauf_details"], key=lambda d: d.vd_id)
    assert [r.ges_preis for r in rows] == [20.0, -10.0]
    assert session.get(Gutschein, g.gutschein_id).restbetrag == 10.0
    from python.business.voucher_logic import voucher_balance
    assert voucher_balance(session, 200) == 0


# ------------------------------------------------------------ Anzahlung

def test_router_creates_anzahlung_with_vat_split(session):
    from python.routers.verkauf import create_verkauf as router_create_verkauf
    from python.models import VerkaufCreate, Anzahlung, AnzahlungDetails, Kassenstand

    a = _seed_artikel(session, mwst_satz=0.19, vk_preis=10.0, artikel_nr="A1")
    b = _seed_artikel(session, mwst_satz=0.07, vk_preis=20.0, artikel_nr="A2")
    anzahlung_artikel = _seed_artikel(session, artikel_nr="ANZAHLUNG", vk_preis=None)

    payload = VerkaufCreate(
        anzahlung_betrag=15.0,
        verkauf_details=[
            {"artikel_id": a.artikel_id, "stueckzahl": 1},
            {"artikel_id": b.artikel_id, "stueckzahl": 1},
        ],
    )
    result = router_create_verkauf(payload, session, None, None)
    rows = sorted(result["verkauf_details"], key=lambda d: d.vd_id)
    split = [r for r in rows if r.artikel_id == anzahlung_artikel.artikel_id]
    goods = [r for r in rows if r.artikel_id != anzahlung_artikel.artikel_id]

    assert [r.ges_preis for r in goods] == [0.0, 0.0]
    assert {r.mwst_satz: r.ges_preis for r in split} == {0.07: 10.0, 0.19: 5.0}
    assert sum(r.ges_preis for r in split) == 15.0

    anzahlungen = session.exec(select(Anzahlung)).all()
    assert len(anzahlungen) == 1
    assert anzahlungen[0].anzahlung_in_rech_nr == result["rechnungs_nr"]
    details = session.exec(select(AnzahlungDetails).order_by(AnzahlungDetails.ad_id)).all()
    assert [(d.vd_id, d.ges_preis) for d in details] == [
        (goods[0].vd_id, 10.0), (goods[1].vd_id, 20.0),
    ]
    assert session.exec(select(Kassenstand)).one().neuer_kassenstand == 15.0


def test_router_resolves_anzahlung_in_normal_sale(session):
    from python.routers.verkauf import create_verkauf as router_create_verkauf
    from python.models import VerkaufCreate, Anzahlung

    a = _seed_artikel(session, mwst_satz=0.19, vk_preis=10.0, artikel_nr="A1")
    b = _seed_artikel(session, mwst_satz=0.07, vk_preis=20.0, artikel_nr="A2")
    c = _seed_artikel(session, mwst_satz=0.19, vk_preis=5.0, artikel_nr="C1")
    _seed_artikel(session, artikel_nr="ANZAHLUNG", vk_preis=None)
    aufloesung_artikel = _seed_artikel(session, artikel_nr="ANZAHLAUFLOES", vk_preis=None)

    deposit = router_create_verkauf(VerkaufCreate(
        anzahlung_betrag=15.0,
        verkauf_details=[
            {"artikel_id": a.artikel_id, "stueckzahl": 1},
            {"artikel_id": b.artikel_id, "stueckzahl": 1},
        ],
    ), session, None, None)

    result = router_create_verkauf(VerkaufCreate(
        anzahlung_aufloesen_nr=deposit["rechnungs_nr"],
        verkauf_details=[{"artikel_id": c.artikel_id, "stueckzahl": 1}],
    ), session, None, None)
    rows = sorted(result["verkauf_details"], key=lambda d: d.vd_id)

    assert [r.ges_preis for r in rows] == [5.0, 10.0, 20.0, -10.0, -5.0]
    assert [r.artikel_id for r in rows[3:]] == [
        aufloesung_artikel.artikel_id, aufloesung_artikel.artikel_id,
    ]
    assert sum(r.ges_preis for r in rows) == 20.0

    anzahlungen = session.exec(select(Anzahlung).order_by(Anzahlung.anzahlung_id)).all()
    assert len(anzahlungen) == 2
    assert anzahlungen[1].anzahlung_in_rech_nr == deposit["rechnungs_nr"]
    assert anzahlungen[1].aufloesung_in_rech_nr == result["rechnungs_nr"]

    with pytest.raises(Exception) as exc:
        router_create_verkauf(VerkaufCreate(
            anzahlung_aufloesen_nr=deposit["rechnungs_nr"],
        ), session, None, None)
    assert "already resolved" in str(exc.value)




def test_variable_price_article_uses_explicit_line_price(session):
    from python.routers.verkauf import create_verkauf as router_create_verkauf
    from python.models import VerkaufCreate

    artikel = _seed_artikel(session, vk_preis=10.0, variabler_preis=True, artikel_nr="VAR")
    payload = VerkaufCreate(verkauf_details=[
        {"artikel_id": artikel.artikel_id, "stueckzahl": 2, "ges_preis": 12.34},
    ])
    result = router_create_verkauf(payload, session, None, None)

    rows = result["verkauf_details"]
    assert len(rows) == 1
    assert rows[0].ges_preis == 12.34
    assert result["verkauf_mwst"][0]["mwst_netto"] == pytest.approx(12.34 / 1.19, abs=0.01)


def test_failed_sale_rolls_back_everything(session, monkeypatch):
    from python.routers.verkauf import create_verkauf as router_create_verkauf
    from python.models import Kassenstand, VerkaufCreate
    from python.business import cash_register

    artikel = _seed_artikel(session)

    def boom(**kwargs):
        raise RuntimeError("kassenstand update failed")

    monkeypatch.setattr(cash_register, "update_kassenstand_for_sale", boom)
    payload = VerkaufCreate(verkauf_details=[
        {"artikel_id": artikel.artikel_id, "stueckzahl": 1},
    ])
    with pytest.raises(RuntimeError):
        router_create_verkauf(payload, session, None, None)

    # the sale, its details, the VAT rows and the cash entry are all rolled back
    assert session.exec(select(Verkauf)).all() == []
    assert session.exec(select(VerkaufDetails)).all() == []
    assert session.exec(select(VerkaufMwst)).all() == []
    assert session.exec(select(Kassenstand)).all() == []


def test_sale_creates_voucher_with_counter_number(session):
    from python.routers.verkauf import create_verkauf as router_create_verkauf
    from python.models import Gutschein, GutscheinCounter, VerkaufCreate

    artikel = _seed_artikel(session, vk_preis=None, variabler_preis=True, artikel_nr="GUTSCHEIN")
    payload = VerkaufCreate(verkauf_details=[
        {"artikel_id": artikel.artikel_id, "stueckzahl": 1, "ges_preis": 10.0},
    ])
    router_create_verkauf(payload, session, None, None)

    rows = session.exec(select(Gutschein)).all()
    assert len(rows) == 1
    assert rows[0].gutschein_nr == 200
    assert rows[0].restbetrag == 10.0
    assert session.get(GutscheinCounter, 1).last_nr == 200
