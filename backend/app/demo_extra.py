"""Extra DEMO personas for the demo day (SUG-61). ALL FICTIONAL — names carry "(DEMO)", lenders "(fictional)".

Runs after `demo.seed` from the admin CLI only (`seed-demo`, `reset-demo`); the golden fixtures D1-D4 in
db/seed_demo.sql and their tests are untouched. Plain records go in as rows; everything the app derives
(assessments, scenarios, consents, snapshots + SHA-256, lender reviews) is produced by the real services, so
a judge sees exactly what an owner or lender would have produced by clicking. `reset` removes all of it
(every row is is_demo or belongs to an is_demo user / profile / organisation).

Shops:   Hasan General Store (grocery, repaying a samity loan) · Nasima Bostro Bitan (clothing, Eid loan shared
         with a bank, bank asked for more) · Jamal Fol Bhandar (fruit, only checking — the check says it does
         not fit yet).
Farms:   Rokeya Sobji Khet (leased land, winter vegetables, stuck mid-season; shared with the samity) ·
         Abdul Dhan Khet (village rice farmer tracking his NGO crop loan) · Monir Dhan Khet (about to start Boro;
         the bank asked to see it, the owner has not answered yet).
Lenders: DEMO Shonali Samity (fictional) — local installment lender · DEMO Krishi o Babsa Bank (fictional)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from .core.clock import today
from .core.deps import LenderContext
from .core.security import hash_password
from .models import (
    BusinessProfile, DebtFacility, FarmingSeason, FinancingRequest, FinancingRequestItem, LenderOfficer,
    LenderOrganization, SeasonCostItem, Supplier, Transaction, User,
)
from .services import assessment_service, consent_service, lender_service, snapshot_service

EXTRA_PHONES = ("+8801900000201", "+8801900000202", "+8801900000203", "+8801900000204", "+8801900000205",
                "+8801900000206", "+8801900000111", "+8801900000112")
D = Decimal


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _Seeder:
    def __init__(self, db: Session, password: str):
        self.db, self.pw, self.a = db, password, today()

    def flush(self, obj):
        self.db.add(obj)
        self.db.flush()
        return obj

    def user(self, name: str, phone: str, email: str, role: str = "owner") -> User:
        return self.flush(User(full_name=name, phone_e164=phone, email=email, password_hash=hash_password(self.pw),
                               role=role, is_demo=True))

    def profile(self, owner: User, **kw) -> BusinessProfile:
        return self.flush(BusinessProfile(owner_user_id=owner.id, is_demo=True, household_declared_at=_now(), **kw))

    def tx(self, p: BusinessProfile, who: User, txn_type: str, amount, d: date, **kw) -> None:
        self.db.add(Transaction(profile_id=p.id, txn_type=txn_type, amount=D(str(amount)), value_date=d,
                                entry_method="seed", created_by=who.id, **kw))

    def week(self, i: int) -> date:
        """Middle of complete week i (1 = oldest of the 8 the forecast reads, 8 = last week)."""
        return self.a - timedelta(days=7 * (9 - i) - 3)

    def lender(self, org: LenderOrganization, name: str, phone: str, email: str, designation: str) -> LenderContext:
        u = self.user(name, phone, email, role="lender_officer")
        off = self.flush(LenderOfficer(user_id=u.id, organization_id=org.id, designation=designation))
        return LenderContext(user=u, officer=off, organization=org)

    def share(self, lender: LenderContext, owner: User, p: BusinessProfile, req: FinancingRequest,
              sections: list[str], message: str, approve: bool):
        lender_service.access_request(self.db, lender, lender_service.AccessRequestIn(
            share_code=p.share_code, requested_sections=sections, message=message))
        c = next(c for c in consent_service.list_consents(self.db, p) if c.status == "requested")
        if approve:
            allowed = [x for x in sections if x in snapshot_service.allowed_sections(p)]
            consent_service.approve(self.db, owner, p, c.id, consent_service.ApproveIn(
                approved_sections=allowed, financing_request_id=req.id, valid_days=14))
        return c


def seed_extra(db: Session, password: str) -> dict[str, str]:
    """Insert the extra personas inside the caller's transaction (after demo.seed). Returns {profile: check status}."""
    s = _Seeder(db, password)
    a = s.a
    status: dict[str, str] = {}

    # ---------------------------------------------------------------- lenders (fictional)
    samity = s.flush(LenderOrganization(name="DEMO Shonali Samity (fictional)", org_type="ngo", is_demo=True))
    bank = s.flush(LenderOrganization(name="DEMO Krishi o Babsa Bank (fictional)", org_type="bank", is_demo=True))
    l_samity = s.lender(samity, "Rafiq Samity Officer (DEMO)", "+8801900000111", "l4.rafiq@demo.invalid",
                        "Field Credit Officer")
    l_bank = s.lender(bank, "Shirin Bank Officer (DEMO)", "+8801900000112", "l5.shirin@demo.invalid", "SME & Agri Officer")

    # ================================================================ S1 Hasan — grocery, repaying a samity loan
    u = s.user("Hasan Ali (DEMO)", "+8801900000201", "s1.hasan@demo.invalid")
    p = s.profile(u, activity_type="shop", display_name="Hasan General Store", business_category="grocery",
                  district="Dhaka", upazila="Mirpur", market_area="Section 10 bazar (DEMO)",
                  household_withdrawal_monthly=D(20000), share_code="HSN4MD7K2Q")
    sa = s.flush(Supplier(profile_id=p.id, display_name="Mirpur wholesaler (DEMO)", goods_supplied="rice, oil, sugar",
                          district="Dhaka", upazila="Mirpur"))
    sb = s.flush(Supplier(profile_id=p.id, display_name="Kawran Bazar dealer (DEMO)", goods_supplied="onion, potato, eggs",
                          district="Dhaka", upazila="Tejgaon"))
    loan = s.flush(DebtFacility(profile_id=p.id, lender_type="ngo", lender_label="Shonali Samity weekly loan (DEMO)",
                                original_principal=D(100000), outstanding_balance=D(77500), outstanding_as_of=a,
                                installment_amount=D(2750), installment_frequency="weekly", next_due_date=a + timedelta(days=2),
                                interest_fee_note="Tk 250 service charge each week (DEMO)"))
    s.tx(p, u, "loan_received", 100000, a - timedelta(days=66), debt_facility_id=loan.id, note="Samity loan received (DEMO)")
    sales = [68000, 72500, 65000, 79000, 70500, 74000, 81000, 69500]
    buys = [52000, 55000, 50000, 60000, 54000, 56000, 62000, 53000]
    for i in range(1, 9):
        d = s.week(i)
        s.tx(p, u, "sale_cash", sales[i - 1], d, note="weekly cash sales (DEMO)")
        s.tx(p, u, "sale_credit", 6000, d, note="baki to regular customers (DEMO)")
        s.tx(p, u, "receivable_collection", 5500, d + timedelta(days=2))
        s.tx(p, u, "purchase_cash", round(buys[i - 1] * 0.6), d, supplier_id=sa.id)
        s.tx(p, u, "purchase_cash", round(buys[i - 1] * 0.4), d, supplier_id=sb.id)
        s.tx(p, u, "operating_expense", 9000, d, category="rent_salary_utilities")
        s.tx(p, u, "loan_principal_repayment", 2500, d + timedelta(days=1), debt_facility_id=loan.id)
        s.tx(p, u, "loan_interest_fee_payment", 250, d + timedelta(days=1), debt_facility_id=loan.id)
        if i % 2 == 0:
            s.tx(p, u, "owner_withdrawal", 10000, d, note="household (DEMO)")
    s.tx(p, u, "loan_principal_repayment", 2500, a - timedelta(days=63), debt_facility_id=loan.id)
    status["Hasan General Store"] = "tracking loan (no new request)"

    # ================================================================ S2 Nasima — clothing, Eid loan shared with the bank
    u = s.user("Nasima Begum (DEMO)", "+8801900000202", "s2.nasima@demo.invalid")
    p = s.profile(u, activity_type="shop", display_name="Nasima Bostro Bitan", business_category="clothing",
                  district="Dhaka", upazila="Keraniganj", market_area="Zinjira bazar (DEMO)",
                  household_withdrawal_monthly=D(15000), no_debt_declared_at=_now(), share_code="NSM8KPR3XB")
    sa = s.flush(Supplier(profile_id=p.id, display_name="Islampur cloth wholesaler (DEMO)", goods_supplied="sarees, three-piece",
                          district="Dhaka", upazila="Kotwali"))
    sb = s.flush(Supplier(profile_id=p.id, display_name="Madhabdi weaver (DEMO)", goods_supplied="lungi, gamchha",
                          district="Narsingdi", upazila="Madhabdi"))
    sales = [82000, 86000, 79000, 91000, 95000, 88000, 99000, 104000]
    buys = [44000, 46000, 42000, 48000, 50000, 47000, 52000, 55000]
    for i in range(1, 9):
        d = s.week(i)
        s.tx(p, u, "sale_cash", sales[i - 1], d, note="weekly cash sales (DEMO)")
        s.tx(p, u, "purchase_cash", round(buys[i - 1] * 0.7), d, supplier_id=sa.id)
        s.tx(p, u, "purchase_cash", round(buys[i - 1] * 0.3), d, supplier_id=sb.id)
        s.tx(p, u, "operating_expense", 8000, d, category="rent_salary_utilities")
        if i % 2 == 0:
            s.tx(p, u, "owner_withdrawal", 7500, d, note="household (DEMO)")
    req = s.flush(FinancingRequest(
        profile_id=p.id, requested_amount=D(200000), purpose_text="ঈদের আগে শাড়ি আর পাঞ্জাবির স্টক (DEMO)",
        purpose_category="inventory", desired_start_date=a, associated_expenses=D(5000), liquidity_buffer=D(15000),
        buffer_justification="Eid rush: keep cash for change and small buys (DEMO)", cash_safely_available=D(20000),
        committed_financing=D(0), current_cash_balance=D(45000), minimum_cash_reserve=D(10000),
        schedule_type="equal_installments", installment_count=12, installment_frequency="weekly",
        first_due_date=a + timedelta(days=7), interest_fees_total=D(12000)))
    db.add_all([
        FinancingRequestItem(profile_id=p.id, financing_request_id=req.id, item_name="Eid sarees (DEMO)", quantity=D(100),
                             unit="piece", unit_price=D(1200), price_source_type="supplier_quote", price_date=a - timedelta(days=3),
                             price_source_note="Quotation from Islampur wholesaler (DEMO)"),
        FinancingRequestItem(profile_id=p.id, financing_request_id=req.id, item_name="Panjabi (DEMO)", quantity=D(80),
                             unit="piece", unit_price=D(1000), price_source_type="supplier_quote", price_date=a - timedelta(days=3),
                             price_source_note="Quotation from Islampur wholesaler (DEMO)"),
    ])
    db.flush()
    status["Nasima Bostro Bitan"] = assessment_service.run(db, p, req.id, a).status
    c = s.share(l_bank, u, p, req, ["profile_summary", "money_summary", "forecast", "financing_request", "obligations",
                                    "supplier_risk"], "Eid stock loan — please share your records (DEMO)", approve=True)
    lender_service.add_event(db, l_bank, c.id, lender_service.EventIn(
        event_type="info_request", body="Please share the written quotation for the sarees (DEMO)."))
    lender_service.add_event(db, l_bank, c.id, lender_service.EventIn(
        event_type="note", body="Sales rise every week before Eid; one supplier gives 70 % of the stock (DEMO note)."))

    # ================================================================ S3 Jamal — fruit, only checking
    u = s.user("Jamal Uddin (DEMO)", "+8801900000203", "s3.jamal@demo.invalid")
    p = s.profile(u, activity_type="shop", display_name="Jamal Fol Bhandar", business_category="fruit",
                  district="Rajshahi", upazila="Boalia", market_area="Shaheb bazar (DEMO)",
                  household_withdrawal_monthly=D(8000), no_debt_declared_at=_now(), share_code="JML6FRT9WA")
    sa = s.flush(Supplier(profile_id=p.id, display_name="Rajshahi mango aratdar (DEMO)", goods_supplied="mango, litchi, guava",
                          district="Rajshahi", upazila="Puthia"))
    sales = [30000, 34000, 28000, 36000, 33000, 31000, 35000]
    buys = [24000, 27000, 23000, 29000, 26000, 25000, 28000]
    for i in range(2, 9):
        d = s.week(i)
        s.tx(p, u, "sale_cash", sales[i - 2], d, note="daily fruit sales, weekly total (DEMO)")
        s.tx(p, u, "purchase_cash", buys[i - 2], d, supplier_id=sa.id)
        s.tx(p, u, "operating_expense", 3500, d, category="other", note="van rent, ice, polythene (DEMO)")
    req = s.flush(FinancingRequest(
        profile_id=p.id, requested_amount=D(150000), purpose_text="আমের মৌসুমে আগাম মাল আর একটা কোল্ড বক্স (DEMO)",
        purpose_category="inventory", desired_start_date=a, associated_expenses=D(5000), liquidity_buffer=D(0),
        cash_safely_available=D(0), committed_financing=D(0), current_cash_balance=D(8000), minimum_cash_reserve=D(3000),
        schedule_type="equal_installments", installment_count=12, installment_frequency="weekly",
        first_due_date=a + timedelta(days=7), interest_fees_total=D(9000)))
    db.add_all([
        FinancingRequestItem(profile_id=p.id, financing_request_id=req.id, item_name="Mango stock, advance (DEMO)", quantity=D(1),
                             unit="lot", unit_price=D(120000), price_source_type="owner_estimate", price_date=a),
        FinancingRequestItem(profile_id=p.id, financing_request_id=req.id, item_name="Cold box (DEMO)", quantity=D(1),
                             unit="piece", unit_price=D(25000), price_source_type="public_listing", price_date=a - timedelta(days=5),
                             price_source_note="Price seen in an online listing (DEMO)"),
    ])
    db.flush()
    status["Jamal Fol Bhandar"] = assessment_service.run(db, p, req.id, a).status

    # ================================================================ F1 Rokeya — leased land, winter vegetables, stuck mid-season
    u = s.user("Rokeya Khatun (DEMO)", "+8801900000204", "f1.rokeya@demo.invalid")
    p = s.profile(u, activity_type="crop_farm", display_name="Rokeya Sobji Khet", business_category="crop",
                  district="Brahmanbaria", upazila="Sarail", household_withdrawal_monthly=D(3000),
                  no_debt_declared_at=_now(), share_code="RKY5SBZ2LC")
    season = s.flush(FarmingSeason(
        profile_id=p.id, crop_name="Winter vegetables — cauliflower, tomato (DEMO)", season_name="winter_vegetables",
        season_label="Winter 2026-27", area_value=D(60), area_unit="decimal", area_acres=D("0.6"),
        sowing_date=a - timedelta(days=40), expected_harvest_date=a + timedelta(days=45),
        expected_output_low=D(7000), expected_output_expected=D(9000), expected_output_high=D(10500),
        expected_price_low=D(18), expected_price_expected=D(22), expected_price_high=D(26), status="growing"))
    costs = {}
    for cat, name, cost in [("land_lease", "Leased land, one season (DEMO)", 15000), ("seed", "Seedlings (DEMO)", 6000),
                            ("fertilizer", "Fertilizer (DEMO)", 9000), ("pesticide", "Pesticide (DEMO)", 7000),
                            ("irrigation", "Irrigation (DEMO)", 5000), ("labour", "Labour (DEMO)", 12000),
                            ("transport", "Transport to market (DEMO)", 3000)]:
        costs[cat] = s.flush(SeasonCostItem(profile_id=p.id, season_id=season.id, category=cat, item_name=name,
                                            quantity=D(1), unit="lot", unit_cost=D(cost)))
    for cat, days in [("land_lease", 50), ("seed", 40), ("fertilizer", 25)]:
        ci = costs[cat]
        s.tx(p, u, "purchase_cash", ci.unit_cost, a - timedelta(days=days), category=cat, season_id=season.id,
             season_cost_item_id=ci.id)
    req = s.flush(FinancingRequest(
        profile_id=p.id, season_id=season.id, requested_amount=D(30000),
        purpose_text="খেতের মাঝপথে কীটনাশক, সেচ আর শ্রমিকের টাকা লাগবে (DEMO)", purpose_category="farm_inputs",
        desired_start_date=a, associated_expenses=D(3000), liquidity_buffer=D(3000),
        buffer_justification="Pesticide price may rise (DEMO)", cash_safely_available=D(0), committed_financing=D(0),
        current_cash_balance=D(12000), minimum_cash_reserve=D(2000), schedule_type="single_payment", installment_count=1,
        first_due_date=a + timedelta(days=55), interest_fees_total=D(1500)))
    for cat, src in [("pesticide", "supplier_quote"), ("irrigation", "owner_estimate"), ("labour", "owner_estimate")]:
        ci = costs[cat]
        db.add(FinancingRequestItem(profile_id=p.id, financing_request_id=req.id, item_name=ci.item_name, quantity=D(1),
                                    unit="lot", unit_price=ci.unit_cost, price_source_type=src, price_date=a,
                                    source_season_cost_item_id=ci.id,
                                    price_source_note="Sarail input dealer (DEMO)" if src == "supplier_quote" else None))
    db.flush()
    status["Rokeya Sobji Khet"] = assessment_service.run(db, p, req.id, a).status
    c = s.share(l_samity, u, p, req, ["profile_summary", "money_summary", "financing_request", "obligations",
                                      "season_summary"], "Mid-season input loan (DEMO)", approve=True)
    lender_service.add_event(db, l_samity, c.id, lender_service.EventIn(
        event_type="info_request", body="Please show the land lease paper for this season (DEMO)."))

    # ================================================================ F2 Abdul — village rice farmer tracking his NGO loan
    u = s.user("Abdul Karim (DEMO)", "+8801900000205", "f2.abdul@demo.invalid")
    p = s.profile(u, activity_type="crop_farm", display_name="Abdul Dhan Khet", business_category="crop",
                  district="Mymensingh", upazila="Trishal", household_withdrawal_monthly=D(4000), share_code="ABD7BRD4HN")
    aman = s.flush(FarmingSeason(
        profile_id=p.id, crop_name="Rice", variety="BRRI dhan49 (DEMO)", season_name="aman", season_label="Aman 2026",
        area_value=D("1.5"), area_unit="bigha", decimals_per_bigha=D(33), area_acres=D("0.495"),
        sowing_date=a - timedelta(days=150), expected_harvest_date=a - timedelta(days=28),
        expected_output_low=D(1300), expected_output_expected=D(1500), expected_output_high=D(1650),
        expected_price_low=D(26), expected_price_expected=D(29), expected_price_high=D(32), status="harvested",
        actual_harvest_date=a - timedelta(days=25), actual_output=D(1450)))
    for cat, name, cost, days in [("seed", "Seed (DEMO)", 2500, 150), ("fertilizer", "Fertilizer (DEMO)", 6000, 120),
                                  ("labour", "Labour (DEMO)", 8000, 30), ("irrigation", "Irrigation (DEMO)", 2000, 90)]:
        ci = s.flush(SeasonCostItem(profile_id=p.id, season_id=aman.id, category=cat, item_name=name, quantity=D(1),
                                    unit="lot", unit_cost=D(cost)))
        s.tx(p, u, "purchase_cash", cost, a - timedelta(days=days), category=cat, season_id=aman.id, season_cost_item_id=ci.id)
    s.tx(p, u, "sale_cash", 26000, a - timedelta(days=20), season_id=aman.id, note="Aman paddy sold to the local arat (DEMO)")
    s.tx(p, u, "sale_cash", 12000, a - timedelta(days=10), season_id=aman.id, note="Rest of the Aman paddy (DEMO)")
    loan = s.flush(DebtFacility(profile_id=p.id, season_id=aman.id, lender_type="ngo", lender_label="Village NGO crop loan (DEMO)",
                                original_principal=D(30000), outstanding_balance=D(18000), outstanding_as_of=a,
                                installment_amount=D(3300), installment_frequency="monthly",
                                next_due_date=a + timedelta(days=12), interest_fee_note="Tk 300 a month (DEMO)"))
    s.tx(p, u, "loan_received", 30000, a - timedelta(days=130), debt_facility_id=loan.id)
    for days in (100, 70, 40, 10):
        s.tx(p, u, "loan_principal_repayment", 3000, a - timedelta(days=days), debt_facility_id=loan.id)
        s.tx(p, u, "loan_interest_fee_payment", 300, a - timedelta(days=days), debt_facility_id=loan.id)
    boro = s.flush(FarmingSeason(
        profile_id=p.id, crop_name="Rice", variety="BRRI dhan28 (DEMO)", season_name="boro", season_label="Boro 2026-27",
        area_value=D("1.5"), area_unit="bigha", decimals_per_bigha=D(33), area_acres=D("0.495"),
        sowing_date=a + timedelta(days=50), expected_harvest_date=a + timedelta(days=170),
        expected_output_low=D(1600), expected_output_expected=D(1900), expected_output_high=D(2150),
        expected_price_low=D(28), expected_price_expected=D(31), expected_price_high=D(34), status="planned"))
    for cat, name, cost in [("seed", "Seed (DEMO)", 3000), ("fertilizer", "Fertilizer (DEMO)", 7000),
                            ("irrigation", "Irrigation (DEMO)", 6000), ("labour", "Labour (DEMO)", 9000)]:
        s.flush(SeasonCostItem(profile_id=p.id, season_id=boro.id, category=cat, item_name=name, quantity=D(1),
                               unit="lot", unit_cost=D(cost)))
    status["Abdul Dhan Khet"] = "tracking loan (no new request)"

    # ================================================================ F3 Monir — about to start Boro; bank asked, owner not answered
    u = s.user("Monir Hossain (DEMO)", "+8801900000206", "f3.monir@demo.invalid")
    p = s.profile(u, activity_type="crop_farm", display_name="Monir Dhan Khet", business_category="crop",
                  district="Dinajpur", upazila="Birganj", household_withdrawal_monthly=D(2000),
                  no_debt_declared_at=_now(), share_code="MNR3MNS8EV")
    season = s.flush(FarmingSeason(
        profile_id=p.id, crop_name="Rice", variety="BRRI dhan89 (DEMO)", season_name="boro", season_label="Boro 2026-27",
        area_value=D(100), area_unit="decimal", area_acres=D(1), sowing_date=a + timedelta(days=20),
        expected_harvest_date=a + timedelta(days=130), expected_output_low=D(1800), expected_output_expected=D(2200),
        expected_output_high=D(2500), expected_price_low=D(27), expected_price_expected=D(30), expected_price_high=D(33),
        status="planned"))
    costs = {}
    for cat, name, cost in [("seed", "Seed (DEMO)", 5000), ("fertilizer", "Fertilizer (DEMO)", 14000),
                            ("irrigation", "Irrigation, shallow pump (DEMO)", 10000), ("labour", "Labour (DEMO)", 16000),
                            ("pesticide", "Pesticide (DEMO)", 4000)]:
        costs[cat] = s.flush(SeasonCostItem(profile_id=p.id, season_id=season.id, category=cat, item_name=name,
                                            quantity=D(1), unit="lot", unit_cost=D(cost)))
    req = s.flush(FinancingRequest(
        profile_id=p.id, season_id=season.id, requested_amount=D(40000),
        purpose_text="বোরো মৌসুম শুরু: সার, সেচ আর শ্রমিকের খরচ (DEMO)", purpose_category="farm_inputs",
        desired_start_date=a + timedelta(days=15), associated_expenses=D(0), liquidity_buffer=D(0),
        cash_safely_available=D(0), committed_financing=D(0), current_cash_balance=D(22000), minimum_cash_reserve=D(3000),
        schedule_type="single_payment", installment_count=1, first_due_date=a + timedelta(days=140),
        interest_fees_total=D(2400)))
    for cat in ("fertilizer", "irrigation", "labour"):
        ci = costs[cat]
        db.add(FinancingRequestItem(profile_id=p.id, financing_request_id=req.id, item_name=ci.item_name, quantity=D(1),
                                    unit="lot", unit_price=ci.unit_cost, price_source_type="owner_estimate", price_date=a,
                                    source_season_cost_item_id=ci.id))
    db.flush()
    status["Monir Dhan Khet"] = assessment_service.run(db, p, req.id, a).status
    s.share(l_bank, u, p, req, ["profile_summary", "financing_request", "obligations", "season_summary"],
            "Boro input loan — may we see your season plan? (DEMO)", approve=False)

    db.flush()
    return status
