"""Accounting effects of the 12 transaction types (S1 F2, Appendix A4;
DB doc §4). Mirrors reference_calculations.TXN_EFFECTS / summarize()."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from .money import ZERO, money

# (cash, sales_recorded, operating_cash, receivable, payable)
TXN_EFFECTS: dict[str, tuple[int, int, int, int, int]] = {
    "sale_cash":                 (+1, +1, +1, 0, 0),
    "sale_credit":               (0, +1, 0, +1, 0),    # baki: receivable, NOT cash
    "receivable_collection":     (+1, 0, +1, -1, 0),
    "purchase_cash":             (-1, 0, -1, 0, 0),
    "purchase_credit":           (0, 0, 0, 0, +1),
    "payable_payment":           (-1, 0, -1, 0, -1),
    "operating_expense":         (-1, 0, -1, 0, 0),
    "loan_received":             (+1, 0, 0, 0, 0),     # financing cash, NOT sales
    "loan_principal_repayment":  (-1, 0, 0, 0, 0),     # reduces debt, NOT expense
    "loan_interest_fee_payment": (-1, 0, 0, 0, 0),     # tracked separately
    "owner_withdrawal":          (-1, 0, 0, 0, 0),     # household, NOT operating
    "owner_contribution":        (+1, 0, 0, 0, 0),     # owner money, NOT income
}
TXN_TYPES = frozenset(TXN_EFFECTS)
PURCHASE_TYPES = frozenset({"purchase_cash", "payable_payment"})  # count as purchases (L2, F3)
SUPPLIER_LINK_TYPES = frozenset({"purchase_cash", "purchase_credit", "payable_payment"})
LOAN_LINK_TYPES = frozenset({"loan_received", "loan_principal_repayment", "loan_interest_fee_payment"})
OPERATING_TYPES = frozenset(t for t, eff in TXN_EFFECTS.items() if eff[2] != 0)

SUMMARY_FIELDS = (
    "cash_net_change", "sales_recorded", "cash_sales", "credit_sales",
    "operating_cash_in", "operating_cash_out", "net_operating_cash",
    "receivables_outstanding", "payables_outstanding",
    "financing_received", "principal_repaid", "interest_fees_paid",
    "owner_withdrawals", "owner_contributions",
)


@dataclass(frozen=True)
class Txn:
    txn_type: str
    amount: Decimal
    status: str = "confirmed"


def summarize(transactions: Iterable[Txn]) -> dict[str, Decimal]:
    """Money summary for ONE profile. Voided rows are ignored."""
    out = {k: ZERO for k in SUMMARY_FIELDS}
    for t in transactions:
        if t.status != "confirmed":
            continue
        a, ty = t.amount, t.txn_type
        cash, sales, op, recv, pay = TXN_EFFECTS[ty]
        out["cash_net_change"] += cash * a
        out["sales_recorded"] += sales * a
        if ty == "sale_cash":
            out["cash_sales"] += a
        elif ty == "sale_credit":
            out["credit_sales"] += a
        if op > 0:
            out["operating_cash_in"] += a
        elif op < 0:
            out["operating_cash_out"] += a
        out["receivables_outstanding"] += recv * a
        out["payables_outstanding"] += pay * a
        if ty == "loan_received":
            out["financing_received"] += a
        elif ty == "loan_principal_repayment":
            out["principal_repaid"] += a
        elif ty == "loan_interest_fee_payment":
            out["interest_fees_paid"] += a
        elif ty == "owner_withdrawal":
            out["owner_withdrawals"] += a
        elif ty == "owner_contribution":
            out["owner_contributions"] += a
    out["net_operating_cash"] = out["operating_cash_in"] - out["operating_cash_out"]
    return {k: money(v) for k, v in out.items()}
