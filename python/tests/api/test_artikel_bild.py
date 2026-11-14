"""Tests for the article picture endpoints (files on disk, hardlink on versioning)."""
import os

import pytest
from fastapi.testclient import TestClient

from python.main import app
from python.models import Artikel, Lieferant, Mwst, Produktgruppe
from python.session import get_session


PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)


@pytest.fixture
def client(session, tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGES_DIR", str(tmp_path))
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def _artikel(session):
    m = Mwst(mwst_satz=0.07, dsfinvk_ust_schluessel=2)
    session.add(m)
    session.commit()
    session.refresh(m)
    pg = Produktgruppe(produktgruppen_name="PG Bild", mwst_id=m.mwst_id)
    l = Lieferant(lieferant_name="L Bild")
    session.add(pg)
    session.add(l)
    session.commit()
    session.refresh(pg)
    session.refresh(l)
    a = Artikel(artikel_nr="B1", artikel_name="Bild Artikel",
                produktgruppen_id=pg.produktgruppen_id, lieferant_id=l.lieferant_id,
                vk_preis=1.0)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def upload(client, artikel_id, data, filename="bild.png", content_type="image/png"):
    return client.put(f"/artikel/{artikel_id}/bild",
                      files={"bild": (filename, data, content_type)})


def test_upload_and_read(client, session):
    a = _artikel(session)
    assert client.get(f"/artikel/{a.artikel_id}/bild").status_code == 404

    assert upload(client, a.artikel_id, PNG).status_code == 200
    r = client.get(f"/artikel/{a.artikel_id}/bild")
    assert r.status_code == 200
    assert r.content == PNG
    assert r.headers["content-type"] == "image/png"
    assert r.headers["etag"]


def test_rejects_non_image_and_wrong_type(client, session):
    a = _artikel(session)
    assert upload(client, a.artikel_id, b"<?php echo 1; ?>", "x.png").status_code == 415
    # magic bytes win over the client filename
    assert upload(client, a.artikel_id, b"\xff\xd8\xff\xe0" + b"\x00" * 8, "x.png").status_code == 200
    r = client.get(f"/artikel/{a.artikel_id}/bild")
    assert r.headers["content-type"] == "image/jpeg"


def test_versioned_artikel_shares_picture_via_hardlink(client, session):
    a = _artikel(session)
    upload(client, a.artikel_id, PNG)
    r = client.patch(f"/artikel/{a.artikel_id}", json={"vk_preis": 2.0})
    assert r.status_code == 200
    new_id = r.json()["artikel_id"]
    assert new_id != a.artikel_id

    assert client.get(f"/artikel/{new_id}/bild").content == PNG
    old = os.stat(os.path.join(os.environ["IMAGES_DIR"], f"{a.artikel_id}.png"))
    new = os.stat(os.path.join(os.environ["IMAGES_DIR"], f"{new_id}.png"))
    assert old.st_ino == new.st_ino


def test_delete(client, session):
    a = _artikel(session)
    upload(client, a.artikel_id, PNG)
    assert client.delete(f"/artikel/{a.artikel_id}/bild").status_code == 200
    assert client.get(f"/artikel/{a.artikel_id}/bild").status_code == 404


def test_unconfigured_dir(client, session, monkeypatch):
    a = _artikel(session)
    monkeypatch.delenv("IMAGES_DIR")
    assert client.get(f"/artikel/{a.artikel_id}/bild").status_code == 503
    assert upload(client, a.artikel_id, PNG).status_code == 503
    # versioning must still work without a picture directory
    assert client.patch(f"/artikel/{a.artikel_id}", json={"vk_preis": 3.0}).status_code == 200
