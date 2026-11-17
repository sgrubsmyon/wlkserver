"""Artikel catalogue: search, CRUD, versioning and article pictures.

Updates never overwrite a row: changes to versioned fields deactivate the old
article and create a new version, keeping sales history intact. Pictures are
files next to the DB, keyed by article id and validated by magic bytes.
"""
from datetime import datetime, timezone

import os
from pathlib import Path

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import select

# from ..dependencies import get_token_header

from .. import config
from ..models import (
    Artikel,
    Lieferant,
    Produktgruppe,
)
from ..schemas import (
    ArtikelPublic,
    ArtikelCreate,
    ArtikelUpdate,
)
from ..session import SessionDep
from ..utils.pagination import paginate


router = APIRouter(
    prefix="/artikel",
    tags=["artikel"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


# Article pictures are files next to the DB, named `<artikel_id>.<ext>`.
# JPEG, PNG and WebP are accepted; the type comes from the magic bytes, never
# from the client-provided filename.
MAX_BILD_BYTES = 5 * 1024 * 1024
BILD_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def _bild_dir() -> Path:
    """Return the configured picture folder, creating it if needed."""
    folder = config.images_dir()
    if not folder:
        raise HTTPException(status_code=503, detail="IMAGES_DIR is not configured")
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
    except OSError:
        raise HTTPException(status_code=503, detail="IMAGES_DIR is not writable")
    return Path(folder)


def _bild_path(artikel_id: int) -> Path | None:
    """Return the picture file of an article, or None if it has none."""
    folder = _bild_dir()
    for ext in BILD_TYPES:
        path = folder / f"{artikel_id}{ext}"
        if path.is_file():
            return path
    return None


def _bild_extension(data: bytes) -> str | None:
    """Detect the picture type from magic bytes; None if unsupported."""
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def _link_bild(old_id: int, new_id: int) -> None:
    """Share the picture of a versioned article: a hardlink, not a copy."""
    if not config.images_dir():
        return  # pictures not configured here; versioning must still work
    old = _bild_path(old_id)
    if old is None or _bild_path(new_id) is not None:
        return
    try:
        os.link(old, old.with_name(f"{new_id}{old.suffix}"))
    except OSError:
        pass  # no hardlink support here; the picture can be uploaded again


@router.get("/{artikel_id}/bild")
def read_artikel_bild(artikel_id: int):
    """Serve the article picture; 404 if the article has none."""
    path = _bild_path(artikel_id)
    if path is None:
        raise HTTPException(status_code=404, detail="No picture for this artikel")
    # Starlette adds ETag/Last-Modified from the file and answers 304 itself.
    return FileResponse(path, media_type=BILD_TYPES[path.suffix])


@router.put("/{artikel_id}/bild")
def upload_artikel_bild(artikel_id: int, bild: UploadFile, session: SessionDep):
    """Replace the picture of an article (JPEG, PNG or WebP, max. 5 MB).

    Raises 404 for an unknown article, 413 for oversized uploads and 415 for
    other formats. The type comes from the content; the old file is removed.
    """
    if not session.get(Artikel, artikel_id):
        raise HTTPException(status_code=404, detail="Artikel not found")
    folder = _bild_dir()
    data = bild.file.read(MAX_BILD_BYTES + 1)
    if len(data) > MAX_BILD_BYTES:
        raise HTTPException(status_code=413, detail="Bild too large (max. 5 MB)")
    ext = _bild_extension(data)
    if ext is None:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG or WebP pictures")
    # Write next to the target and rename, so a failed upload never leaves half a file.
    tmp = folder / f".{artikel_id}.tmp"
    tmp.write_bytes(data)
    os.replace(tmp, folder / f"{artikel_id}{ext}")
    for other in BILD_TYPES:
        if other != ext:
            (folder / f"{artikel_id}{other}").unlink(missing_ok=True)
    return {"bild": f"/artikel/{artikel_id}/bild"}


@router.delete("/{artikel_id}/bild")
def delete_artikel_bild(artikel_id: int, session: SessionDep):
    """Delete the picture of an article; 404 if there is none."""
    if not session.get(Artikel, artikel_id):
        raise HTTPException(status_code=404, detail="Artikel not found")
    path = _bild_path(artikel_id)
    if path is None:
        raise HTTPException(status_code=404, detail="No picture for this artikel")
    path.unlink()
    return {"message": "Bild deleted"}


@router.get("/")
def read_artikel(
    session: SessionDep, aktiv_only: bool = True,
    search_string: str = "",
    barcode: str = "", artikel_nr: str = "", artikel_name: str = "",
    lieferant_id: int = 0, produktgruppen_id: int = 0,
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[ArtikelPublic]:
    """List articles with filters and pagination.

    `aktiv_only` (default) hides deactivated versions. Filters are applied in
    this precedence: `search_string` (all space separated terms must match),
    `barcode`, `artikel_nr` (plus `lieferant_id`), `lieferant_id`,
    `produktgruppen_id`, `artikel_name`.
    """
    selection = select(Artikel).join(Produktgruppe).join(Lieferant)
    if aktiv_only:
        selection = selection.where(Artikel.aktiv == True)
    if search_string:
        # Split the search string into space separated terms
        search_terms = search_string.split()
        # Each search term must be present in one of the searchable columns
        for (term) in search_terms:
            selection = selection.where(
                Artikel.artikel_name.contains(term) |
                Artikel.kurzname.contains(term) |
                Artikel.artikel_nr.contains(term) |
                Artikel.herkunft.contains(term) |
                Artikel.barcode.contains(term)
            )
    elif barcode:
        selection = selection.where(Artikel.barcode == barcode)
    elif artikel_nr and lieferant_id:
        selection = selection.where(Artikel.artikel_nr == artikel_nr).where(Artikel.lieferant_id == lieferant_id)
    elif artikel_nr:
        selection = selection.where(Artikel.artikel_nr.contains(artikel_nr))
    elif lieferant_id:
        selection = selection.where(Artikel.lieferant_id == lieferant_id)
    elif produktgruppen_id:
        selection = selection.where(Artikel.produktgruppen_id == produktgruppen_id)
    elif artikel_name:
        # Space separated terms must all match (in any order), e.g.
        # "bio apfel" finds "Apfel bio" and "Bio-Apfel".
        for term in artikel_name.split():
            selection = selection.where(
                Artikel.artikel_name.contains(term) | Artikel.kurzname.contains(term))
    artikel = paginate(session, selection, offset, limit, Artikel.artikel_name, Artikel.lieferant_id)
    
    # Prepare the response
    # (add data from the joined tables)
    return_obj = []
    for a in artikel:
        obj = ArtikelPublic.model_validate(a, update={
            "produktgruppen_name": a.produktgruppe.produktgruppen_name if a.produktgruppe else None,
            "lieferant_name": a.lieferant.lieferant_name if a.lieferant else None,
            "pfand_artikel_id": a.produktgruppe.pfand.artikel_id if a.produktgruppe and a.produktgruppe.pfand else None,
            "pfand_wert": a.produktgruppe.pfand.artikel.vk_preis \
                if a.produktgruppe and a.produktgruppe.pfand and \
                    a.produktgruppe.pfand.artikel else None
        })
        return_obj.append(obj)
    
    return return_obj


@router.get("/{artikel_id}")
def read_single_artikel(artikel_id: int, session: SessionDep) -> ArtikelPublic:
    """Read one article incl. product group, supplier and Pfand details."""
    artikel = session.get(Artikel, artikel_id)
    if not artikel:
        raise HTTPException(status_code=404, detail="Artikel not found")
    artikel = ArtikelPublic.model_validate(artikel, update={
            "produktgruppen_name": artikel.produktgruppe.produktgruppen_name if artikel.produktgruppe else None,
            "lieferant_name": artikel.lieferant.lieferant_name if artikel.lieferant else None,
            "pfand_artikel_id": artikel.produktgruppe.pfand.artikel_id if artikel.produktgruppe and artikel.produktgruppe.pfand else None,
            "pfand_wert": artikel.produktgruppe.pfand.artikel.vk_preis \
                if artikel.produktgruppe and artikel.produktgruppe.pfand and \
                    artikel.produktgruppe.pfand.artikel else None
        })
    return artikel


@router.post("/", response_model=ArtikelPublic)
def create_artikel(artikel: ArtikelCreate, session: SessionDep):
    """Create an article; 400 if supplier and artikel_nr already exist."""
    new_artikel = Artikel.model_validate(artikel)

    # Check if this article already exists (combination of lieferant_id and artikel_nr)
    # artikel = session.get(Artikel, (new_artikel.lieferant_id, new_artikel.artikel_nr))
    # if artikel:
    #     raise HTTPException(status_code=400, detail="Artikel already exists")
    artikel_list = read_artikel(
        session,
        aktiv_only=True,
        artikel_nr=new_artikel.artikel_nr, lieferant_id=new_artikel.lieferant_id
    )
    if len(artikel_list) > 0:
        raise HTTPException(status_code=400, detail="Artikel already exists")

    new_artikel.artikel_id = None # whatever has been set here, unset it so that the ID will be set by the DB
    new_artikel.von = datetime.now(timezone.utc)
    new_artikel.bis = None
    new_artikel.aktiv = True

    session.add(new_artikel)
    session.commit()
    session.refresh(new_artikel)
    new_artikel = ArtikelPublic.model_validate(new_artikel, update={
        "produktgruppen_name": new_artikel.produktgruppe.produktgruppen_name if new_artikel.produktgruppe else None,
        "lieferant_name": new_artikel.lieferant.lieferant_name if new_artikel.lieferant else None,
        "pfand_artikel_id": new_artikel.produktgruppe.pfand.artikel_id if new_artikel.produktgruppe and new_artikel.produktgruppe.pfand else None,
        "pfand_wert": new_artikel.produktgruppe.pfand.artikel.vk_preis \
            if new_artikel.produktgruppe and new_artikel.produktgruppe.pfand and \
                new_artikel.produktgruppe.pfand.artikel else None
    })
    return new_artikel


def delete_artikel_intern(artikel_id: int, session: SessionDep):
    """Deactivate an article and set its `bis` date (used by versioning).

    Raises 404 if missing and 400 if already deactivated. Articles are never
    deleted, so old sales keep their reference.
    """
    artikel = session.get(Artikel, artikel_id)
    if not artikel:
        raise HTTPException(status_code=404, detail="Artikel not found")
    if artikel.aktiv == False:
        raise HTTPException(status_code=400, detail="Artikel already deactivated")
    artikel.aktiv = False
    artikel.bis = datetime.now(timezone.utc)
    session.add(artikel)
    session.commit()
    session.refresh(artikel) # needed, or returned article will be empty
    return artikel


@router.delete("/{artikel_id}")
def delete_artikel(artikel_id: int, session: SessionDep):
    """Deactivate an article instead of deleting the row."""
    delete_artikel_intern(artikel_id, session)
    return {"message": "Artikel deactivated"}


@router.patch("/{artikel_id}", response_model=ArtikelPublic)
def update_artikel(artikel_id: int, artikel: ArtikelUpdate, session: SessionDep):
    """Update an article, creating a new version when needed.

    Changes to `bestand`, `beliebtheit`, `lieferbar` and `sortiment` are applied
    in place. Any other change deactivates the row and creates a new version
    that shares the picture. Raises 400 for deactivated articles or no changes.
    """
    print("Update artikel:", artikel_id, artikel)

    old_artikel = session.get(Artikel, artikel_id)
    if not old_artikel:
        raise HTTPException(status_code=404, detail="Artikel not found")
    if old_artikel.aktiv == False:
        raise HTTPException(status_code=400, detail="Cannot update deactivated artikel")
    artikel_data = artikel.model_dump(exclude_unset=True)

    changed_keys = []
    for key, value in artikel_data.items():
        if value is not None:
            print(f"  {key} = {value}")
            old_value = old_artikel.__dict__.get(key, None)
            print(f"    old value: {old_value}")
            if old_value != value:
                print("    value of", key, "changed")
                changed_keys.append(key)

    # If there are no changes, just return the old article
    if len(changed_keys) == 0:
        # return old_artikel
        raise HTTPException(status_code=400, detail="No changes to artikel")

    # If the changes were only to fields that do not require a new article, just update the article
    non_versioned_fields = ['bestand', 'beliebtheit', 'lieferbar', 'sortiment']
    if all(key in non_versioned_fields for key in changed_keys):
        for key, value in artikel_data.items():
            setattr(old_artikel, key, value)
        session.add(old_artikel)
        session.commit()
        session.refresh(old_artikel)
        old_artikel = ArtikelPublic.model_validate(old_artikel, update={
            "produktgruppen_name": old_artikel.produktgruppe.produktgruppen_name if old_artikel.produktgruppe else None,
            "lieferant_name": old_artikel.lieferant.lieferant_name if old_artikel.lieferant else None,
            "pfand_artikel_id": old_artikel.produktgruppe.pfand.artikel_id if old_artikel.produktgruppe and old_artikel.produktgruppe.pfand else None,
            "pfand_wert": old_artikel.produktgruppe.pfand.artikel.vk_preis \
                if old_artikel.produktgruppe and old_artikel.produktgruppe.pfand and \
                    old_artikel.produktgruppe.pfand.artikel else None
        })
        return old_artikel
    
    # Instead we just deactivate the article and create a new one
    old_artikel = delete_artikel_intern(artikel_id, session)
    old_artikel_data = old_artikel.model_dump(exclude_unset=False)
    for key, value in artikel_data.items():
        old_artikel_data[key] = value
    new_artikel = create_artikel(old_artikel_data, session)
    _link_bild(artikel_id, new_artikel.artikel_id)

    return new_artikel
