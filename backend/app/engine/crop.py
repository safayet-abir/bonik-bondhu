"""Crop season arithmetic (S1 §5 crop row, §5.1; SUG-13). Pure functions
mirroring reference_calculations.crop_check. Every figure here comes from
the farmer's own estimates and is labelled as such in the UI."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .money import ZERO, money

ONE = Decimal(1)


@dataclass(frozen=True)
class IncomeRange:
    low: Decimal
    expected: Decimal
    high: Decimal


def income_range(output: tuple[Decimal, Decimal, Decimal], price: tuple[Decimal, Decimal, Decimal]) -> IncomeRange:
    """Expected income per case = output (kg) × price (Tk/kg) (FR-SEA-03)."""
    return IncomeRange(*(money(o * p) for o, p in zip(output, price, strict=True)))


def break_even_price(total_planned_costs: Decimal, output_expected: Decimal) -> Decimal:
    return money(total_planned_costs / output_expected)


def crop_check(output_low: Decimal, price_low: Decimal, output_exp: Decimal, total_planned_costs: Decimal,
               remaining_costs_outside_request: Decimal, start_balance: Decimal, debts_due_by_due: Decimal,
               reserve: Decimal, repayment_total: Decimal, harvest_date: date, due_date: date,
               price_factor: Decimal = ONE, yield_factor: Decimal = ONE, cost_factor: Decimal = ONE,
               household_to_harvest: Decimal = ZERO, household_after_harvest: Decimal = ZERO) -> dict:
    """Harvest-time repayment check on the LOW case.

    `household_to_harvest` / `household_after_harvest` are the owner-declared
    household withdrawals of THIS profile (DEC-37) between as_of and harvest
    and between harvest and the due date. They default to 0, which is exactly
    the reference formula; a farm with no other income before harvest must
    still feed the household, so the service passes the declared amount."""
    if harvest_date > due_date:
        return {"status": "insufficient_information", "reason": "repayment_due_before_expected_harvest"}
    out_low = output_low * yield_factor
    income_low = out_low * price_low * price_factor
    remaining = remaining_costs_outside_request * cost_factor
    pre_harvest = start_balance - remaining - household_to_harvest
    available = pre_harvest + income_low - household_after_harvest - debts_due_by_due - reserve
    required = (repayment_total + debts_due_by_due + reserve + remaining + household_to_harvest
                + household_after_harvest - start_balance)
    return {
        "income_low": money(income_low),
        "pre_harvest_balance": money(pre_harvest),
        "pre_harvest_shortfall": money(-pre_harvest) if pre_harvest < 0 else money(Decimal(0)),
        "available_at_due_date": money(available),
        "repayment_due": money(repayment_total),
        "covered": available >= repayment_total,
        "surplus_or_shortfall": money(available - repayment_total),
        "loan_cover_price_per_unit": money(required / out_low),
        "break_even_price_per_unit": break_even_price(total_planned_costs, output_exp),
    }
