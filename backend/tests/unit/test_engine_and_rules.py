"""UT-01 (accounting via the production engine), UT-10 rounding, UT-12 phone
normalisation, password policy, amount parsing."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.security import hash_password, normalize_phone, password_problem, verify_password
from app.engine.accounting import Txn, summarize
from app.engine.money import money, money_str, parse_amount

D = Decimal


def test_ut01_e1_fixture_matches_golden() -> None:
    fx = [
        Txn("sale_cash", D(5000)), Txn("sale_credit", D(2000)), Txn("loan_received", D(50000)),
        Txn("purchase_cash", D(3000)), Txn("loan_principal_repayment", D(4000)),
        Txn("loan_interest_fee_payment", D(500)), Txn("receivable_collection", D(1500)),
        Txn("owner_withdrawal", D(1000)), Txn("sale_cash", D(7000), status="voided"),
    ]
    s = {k: money_str(v) for k, v in summarize(fx).items()}
    assert s == {
        "cash_net_change": "48000.00", "sales_recorded": "7000.00", "cash_sales": "5000.00",
        "credit_sales": "2000.00", "operating_cash_in": "6500.00", "operating_cash_out": "3000.00",
        "net_operating_cash": "3500.00", "receivables_outstanding": "500.00",
        "payables_outstanding": "0.00", "financing_received": "50000.00", "principal_repaid": "4000.00",
        "interest_fees_paid": "500.00", "owner_withdrawals": "1000.00", "owner_contributions": "0.00",
    }


def test_engine_matches_reference_effects_table() -> None:
    from app.engine.accounting import TXN_EFFECTS
    from tests.golden import reference_calculations as ref

    assert TXN_EFFECTS == ref.TXN_EFFECTS


def test_ut01_empty_list_gives_zeros() -> None:
    assert all(v == 0 for v in summarize([]).values())


def test_ut10_round_half_up() -> None:
    assert money(D("0.005")) == D("0.01")
    assert money(D("2.675")) == D("2.68")
    assert money_str(D("150000")) == "150000.00"


@pytest.mark.parametrize("raw", ["01712345678", "+8801712345678", "8801712345678", "017-1234 5678", "০১৭১২৩৪৫৬৭৮"])
def test_ut12_phone_normalisation(raw: str) -> None:
    assert normalize_phone(raw) == "+8801712345678"


@pytest.mark.parametrize("raw", ["01212345678", "0171234567", "017123456789", "+9101712345678", "abc"])
def test_ut12_phone_rejected(raw: str) -> None:
    assert normalize_phone(raw) is None


def test_password_policy() -> None:
    phone = "+8801712345678"
    assert password_problem("short1!", phone) == "auth.err.password_length"
    assert password_problem("1234567890", phone) == "auth.err.password_digits"
    assert password_problem("x" * 129, phone) == "auth.err.password_length"
    assert password_problem("bazar-2026!", phone) is None


def test_argon2id_roundtrip() -> None:
    h = hash_password("bazar-2026!")
    assert h.startswith("$argon2id$")
    assert verify_password(h, "bazar-2026!") is True
    assert verify_password(h, "wrong") is False
    assert verify_password(None, "anything") is False  # dummy verify path


@pytest.mark.parametrize("raw,expected", [("৮,৫০০", "8500"), ("1,50,000.50", "150000.50"), (8500, "8500"), (0.1, "0.1")])
def test_parse_amount(raw, expected) -> None:
    assert parse_amount(raw) == D(expected)


@pytest.mark.parametrize("raw", ["abc", "", True, None, "NaN", "Infinity"])
def test_parse_amount_rejects(raw) -> None:
    with pytest.raises(ValueError):
        parse_amount(raw)
