"""Fill ODF spreadsheet templates (ODS) without LibreOffice or jOpenDocument.

The templates in `VORLAGEN_DIR` are ordinary LibreOffice files. Values are
written by coordinate, like the Java POS did with jOpenDocument: existing cell
styles (currency, date, borders) stay intact, and rows are cloned from a model
row when a table grows. ODF files are ZIP containers of XML; this module uses
`odfpy` instead of patching that XML by hand.
"""
from __future__ import annotations

import copy
import io
from datetime import date, datetime
from decimal import Decimal

from odf.opendocument import load
from odf.table import Table, TableCell, TableRow
from odf.text import P


def load_sheet(content: bytes, model_row: int = 0) -> tuple:
    """Open an ODS file and return `(document, Sheet)` for its first sheet.

    `model_row` is the row cloned when the table has to grow (a data row in the
    template, so new rows keep its formatting).
    """
    document = load(io.BytesIO(content))
    tables = document.getElementsByType(Table)
    if not tables:
        raise ValueError("ODS template contains no table")
    return document, Sheet(document, tables[0], model_row)


def save(document) -> bytes:
    """Serialize a loaded document back to ODS bytes."""
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class Sheet:
    """Coordinate-based cell writer for one sheet of a loaded template."""

    def __init__(self, document, table, model_row: int = 0):
        self.document = document
        self.table = table
        self._model = copy.deepcopy(
            table.getElementsByType(TableRow)[model_row]
        )
        if self._model.getAttribute("numberrowsrepeated") is not None:
            self._model.setAttribute("numberrowsrepeated", 1)

    def set(self, row: int, column: int, value) -> None:
        """Set one cell (0-based), growing the table by cloning the model row."""
        table_row = self._row(row)
        cells = _expand_row(table_row, column + 1)
        _set_value(cells[column], value)

    def _row(self, index: int) -> TableRow:
        rows = self.table.getElementsByType(TableRow)
        if index < len(rows):
            # A template may mark the data row as repeated (e.g. 57 empty rows
            # of the same style). Writing into it must not duplicate the value.
            row = rows[index]
            if row.getAttribute("numberrowsrepeated") is not None:
                row.setAttribute("numberrowsrepeated", 1)
            return row
        while len(rows) <= index:
            clone = copy.deepcopy(self._model)
            for cell in clone.getElementsByType(TableCell):
                for child in list(cell.childNodes):
                    cell.removeChild(child)
                for attribute in ("valuetype", "value", "datevalue", "timevalue", "booleanvalue"):
                    if cell.getAttribute(attribute) is not None:
                        cell.removeAttribute(attribute)
            self.table.addElement(clone)
            rows = self.table.getElementsByType(TableRow)
        return rows[index]


def _expand_row(row: TableRow, upto: int) -> list:
    """Materialize repeated cells up to `upto`, keeping the rest repeated."""
    specs = [(cell, int(cell.getAttribute("numbercolumnsrepeated") or 1))
             for cell in row.getElementsByType(TableCell)]
    for cell, _ in specs:
        row.removeChild(cell)
    cells, index = [], 0
    for cell, repeat in specs:
        while repeat > 0 and index < upto:
            single = copy.deepcopy(cell)
            single.setAttribute("numbercolumnsrepeated", 1)
            row.addElement(single)
            cells.append(single)
            repeat -= 1
            index += 1
        if repeat > 0:
            rest = copy.deepcopy(cell)
            rest.setAttribute("numbercolumnsrepeated", repeat)
            row.addElement(rest)
    while len(cells) < upto:  # row had fewer cells than requested
        filler = copy.deepcopy(cells[-1]) if cells else TableCell()
        row.addElement(filler)
        cells.append(filler)
    return cells


def _set_value(cell: TableCell, value) -> None:
    """Write a string, number or date into a cell, clearing its old content."""
    for child in list(cell.childNodes):
        cell.removeChild(child)
    for attribute in ("valuetype", "value", "datevalue", "timevalue", "booleanvalue"):
        if cell.getAttribute(attribute) is not None:
            cell.removeAttribute(attribute)
    if value is None:
        return
    if isinstance(value, bool):
        cell.setAttribute("valuetype", "boolean")
        cell.setAttribute("booleanvalue", "true" if value else "false")
        cell.addElement(P(text="WAHR" if value else "FALSCH"))
    elif isinstance(value, (int, float, Decimal)):
        cell.setAttribute("valuetype", "float")
        cell.setAttribute("value", _decimal(value))
    elif isinstance(value, (datetime, date)):
        cell.setAttribute("valuetype", "date")
        cell.setAttribute("datevalue", value.strftime("%Y-%m-%d"))
        cell.addElement(P(text=value.strftime("%d.%m.%Y")))
    else:
        cell.setAttribute("valuetype", "string")
        cell.addElement(P(text=str(value)))


def _decimal(value) -> str:
    number = Decimal(str(value))
    return format(number.normalize(), "f") if number == number.to_integral() else str(number)
