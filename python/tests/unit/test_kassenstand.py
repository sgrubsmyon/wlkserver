import pytest


def test_validate_balance_change_entnahme_exceeds_balance(session):
    from python.business.errors import DomainError
    from python.business.cash_register import validate_balance_change
    with pytest.raises(DomainError):
        validate_balance_change(10.0, -5.0, entnahme=True)
