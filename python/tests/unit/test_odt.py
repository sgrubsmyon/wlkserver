"""Placeholder replacement in ODT/ODS templates (for the later text exports)."""
import io
import zipfile

from python.utils.odt import render_odt_template


def _template(content: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("content.xml", content)
        archive.writestr("styles.xml", "<styles/>")
    return buffer.getvalue()


def test_render_odt_template_replaces_all_markers():
    template = _template("<text>Am __TODAY__ in __ORT__</text>")

    result = render_odt_template(template, {"__TODAY__": "17.11.2026", "__ORT__": "Bonn"})

    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        assert archive.read("content.xml").decode() == "<text>Am 17.11.2026 in Bonn</text>"
        assert archive.read("styles.xml") == b"<styles/>"


def test_render_odt_template_leaves_unknown_markers():
    template = _template("<text>__UNKNOWN__</text>")
    result = render_odt_template(template, {"__TODAY__": "x"})
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        assert archive.read("content.xml").decode() == "<text>__UNKNOWN__</text>"
