"""Fill ODT/ODS text templates by replacing placeholder strings.

jOpenDocument's custom LibreOffice plugin is not available in Python. Instead
the templates contain plain markers such as `__TODAY__` in their text; they are
replaced inside `content.xml` and the ZIP container is written back unchanged.

The Java POS templates still use jOpenDocument fields for the ODT documents, so
this helper is only used once those templates are reworked (see
`concepts/TODO.md`).
"""
from __future__ import annotations

import io
import zipfile


def render_odt_template(template: bytes, replacements: dict[str, str]) -> bytes:
    """Return a copy of the ODT/ODS file with placeholders replaced.

    `replacements` maps marker strings (e.g. `__TODAY__`) to their values. Only
    `content.xml` is touched; styles, pictures and settings are copied as-is.
    """
    source = zipfile.ZipFile(io.BytesIO(template))
    content = source.read("content.xml").decode("utf-8")
    for marker, value in replacements.items():
        content = content.replace(marker, value)

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            if info.filename == "content.xml":
                target.writestr(info, content)
            else:
                target.writestr(info, source.read(info.filename))
    return output.getvalue()
