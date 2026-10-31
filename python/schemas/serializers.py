"""Response assembly: the single place that turns sales rows into API schemas."""
from . import VerkaufDetailsPublic, VerkaufMwstPublic, VerkaufPublic


def verkauf_public(verkauf, include_details=True, include_mwst=True) -> dict:
    """Receipt incl. positions (with article data) and VAT rows."""
    obj = VerkaufPublic.model_validate(verkauf).model_dump()
    if include_details:
        obj["verkauf_details"] = [
            VerkaufDetailsPublic.model_validate(d, update={
                "artikel_name": d.artikel.artikel_name if d.artikel else None,
                "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
                "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
            }) for d in (verkauf.verkauf_details or [])
        ]
    if include_mwst:
        obj["verkauf_mwst"] = [
            VerkaufMwstPublic.model_validate(m).model_dump()
            for m in (verkauf.verkauf_mwst or [])
        ]
    return obj
