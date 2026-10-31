"""Shared list paging, so the list endpoints do not each spell it out."""
from sqlmodel import Session


def paginate(session: Session, selection, offset=0, limit=100, *order_by):
    """Apply sorting (any number of columns) and paging to a `select()`."""
    if order_by:
        selection = selection.order_by(*order_by)
    return session.exec(selection.offset(offset).limit(limit)).all()
