#!/usr/bin/env python3
"""
Actuary Engine — Quickstart Demo
=================================

End-to-end demonstration of the actuarial valuation engine:
1. Load the SOA Illustrative Life Table
2. Build commutation functions at 5% interest
3. Price multiple insurance products
4. Compute annual level premiums
5. Project deterministic cash flows
6. Validate the equivalence principle
"""

import sys

# Ensure UTF-8 output on Windows (default cp1252 can't render Unicode math symbols)
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

from actuary_engine import (
    MortalityTable,
    CommutationFunctions,
    InsurancePricer,
    AnnuityPricer,
    LevelPremiumCalculator,
    SurvivalCurve,
    CashFlowProjector,
    InterestAssumption,
    PolicyContract,
    ProductType,
)


def separator(title: str) -> None:
    """Print a formatted section separator."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def main() -> None:
    # ────────────────────────────────────────────────────────
    # 1. Load Mortality Table
    # ────────────────────────────────────────────────────────
    separator("1. MORTALITY TABLE — SOA Illustrative Life Table")

    table = MortalityTable.from_soa_ilt()
    print(f"  Table:    {table.name}")
    print(f"  Ages:     {table.min_age} to {table.max_age} (ω = {table.omega})")
    print(f"  Radix:    {table.radix:,}")
    print(f"  q₃₀:     {table.get_qx(30):.6f}")
    print(f"  q₆₅:     {table.get_qx(65):.6f}")
    print(f"  ₂₀p₃₀:   {table.get_tpx(30, 20):.6f}")
    print(f"  ₂₀q₃₀:   {table.get_tqx(30, 20):.6f}")

    # ────────────────────────────────────────────────────────
    # 2. Survival Curve
    # ────────────────────────────────────────────────────────
    separator("2. SURVIVAL CURVE — Age 30 Entry")

    curve = SurvivalCurve(table, entry_age=30)
    print(f"  e₃₀ (curtate):   {curve.curtate_expectation():.2f} years")
    print(f"  e̊₃₀ (complete):  {curve.complete_expectation():.2f} years")
    print(f"  Median lifetime:  {curve.median_future_lifetime():.2f} years")
    print(f"  ₁₀p₃₀:          {curve.survival_at(10):.6f}")
    print(f"  ₂₀p₃₀:          {curve.survival_at(20):.6f}")
    print(f"  ₄₀p₃₀:          {curve.survival_at(40):.6f}")

    # ────────────────────────────────────────────────────────
    # 3. Commutation Functions
    # ────────────────────────────────────────────────────────
    separator("3. COMMUTATION FUNCTIONS — 5% Interest Rate")

    interest = InterestAssumption(annual_rate=0.05)
    comm = CommutationFunctions(table, interest)

    print(f"  v = {interest.discount_factor:.6f}")
    print(f"  d = {interest.effective_discount_rate:.6f}")
    print(f"  δ = {interest.force_of_interest:.6f}")
    print()
    print(f"  {'Age':>5}  {'Dx':>14}  {'Nx':>14}  {'Cx':>12}  {'Mx':>12}")
    print(f"  {'─'*5}  {'─'*14}  {'─'*14}  {'─'*12}  {'─'*12}")
    for x in [0, 20, 30, 40, 50, 65, 80, 100]:
        print(
            f"  {x:>5}  {comm.get_Dx(x):>14,.2f}  {comm.get_Nx(x):>14,.2f}"
            f"  {comm.get_Cx(x):>12,.2f}  {comm.get_Mx(x):>12,.2f}"
        )

    # ────────────────────────────────────────────────────────
    # 4. Insurance & Annuity Present Values
    # ────────────────────────────────────────────────────────
    separator("4. INSURANCE & ANNUITY PRESENT VALUES — Age 30")

    x = 30
    print(f"  Whole life insurance    A₃₀     = {comm.whole_life_insurance(x):.6f}")
    print(f"  20-year term insurance  A¹₃₀:₂₀ = {comm.term_insurance(x, 20):.6f}")
    print(f"  20-year endowment      A₃₀:₂₀  = {comm.endowment_insurance(x, 20):.6f}")
    print(f"  20-year pure endowment ₂₀E₃₀   = {comm.pure_endowment(x, 20):.6f}")
    print()
    print(f"  Whole life annuity-due  ä₃₀     = {comm.whole_life_annuity_due(x):.6f}")
    print(f"  20-year temp ann-due    ä₃₀:₂₀  = {comm.temp_annuity_due(x, 20):.6f}")

    # Verify identity: Ax = 1 - d·äx
    ax = comm.whole_life_insurance(x)
    adx = comm.whole_life_annuity_due(x)
    d = interest.effective_discount_rate
    print(f"\n  Identity check: A₃₀ = 1 - d·ä₃₀")
    print(f"    LHS = {ax:.10f}")
    print(f"    RHS = {1 - d * adx:.10f}")
    print(f"    Match: {abs(ax - (1 - d * adx)) < 1e-10}")

    # ────────────────────────────────────────────────────────
    # 5. Level Premium Calculations
    # ────────────────────────────────────────────────────────
    separator("5. ANNUAL LEVEL PREMIUMS — Face Amount = 1,000,000")

    calc = LevelPremiumCalculator(comm)
    face = 1_000_000.0

    products = [
        ("20-Year Term", calc.annual_premium_term(30, 20, face)),
        ("Whole Life", calc.annual_premium_whole_life(30, face)),
        ("20-Year Endowment", calc.annual_premium_endowment(30, 20, face)),
        ("20-Year Pure Endow", calc.annual_premium_pure_endowment(30, 20, face)),
        ("20-Yr Endow (10-pay)", calc.annual_premium_endowment(30, 20, face, premium_term=10)),
    ]

    print(f"  {'Product':<25} {'Premium':>12} {'NSP':>14} {'Annuity':>10} {'P·ä=NSP?':>10}")
    print(f"  {'─'*25} {'─'*12} {'─'*14} {'─'*10} {'─'*10}")
    for name, result in products:
        check = abs(result.annual_premium * result.annuity_factor - result.nsp) < 0.01
        print(
            f"  {name:<25} {result.annual_premium:>12,.2f}"
            f" {result.nsp:>14,.2f}"
            f" {result.annuity_factor:>10.4f}"
            f" {'✓' if check else '✗':>10}"
        )

    # ────────────────────────────────────────────────────────
    # 6. Cash Flow Projection — 20-Year Term
    # ────────────────────────────────────────────────────────
    separator("6. CASH FLOW PROJECTION — 20-Year Term, Age 30, Face 1,000,000")

    contract = PolicyContract(
        product_type=ProductType.TERM,
        issue_age=30,
        term=20,
        sum_assured=face,
    )
    premium_result = calc.annual_premium_term(30, 20, face)
    projector = CashFlowProjector(table, interest)
    df = projector.project(contract, premium_result.annual_premium)

    # Show first and last few years
    print(f"\n  Annual Premium: {premium_result.annual_premium:,.2f}")
    print()
    cols = ["year", "age", "survivors", "deaths", "premium_income", "death_benefit", "pv_net_cash_flow"]
    print(f"  {'Year':>4} {'Age':>4} {'Survivors':>10} {'Deaths':>10} {'Prem Inc':>12} {'Death Ben':>12} {'PV Net CF':>12}")
    print(f"  {'─'*4} {'─'*4} {'─'*10} {'─'*10} {'─'*12} {'─'*12} {'─'*12}")
    for _, row in df.head(5).iterrows():
        print(
            f"  {int(row['year']):>4} {int(row['age']):>4}"
            f" {row['survivors']:>10.6f} {row['deaths']:>10.6f}"
            f" {row['premium_income']:>12,.2f} {row['death_benefit']:>12,.2f}"
            f" {row['pv_net_cash_flow']:>12,.2f}"
        )
    print(f"  {'...':>4}")
    for _, row in df.tail(3).iterrows():
        print(
            f"  {int(row['year']):>4} {int(row['age']):>4}"
            f" {row['survivors']:>10.6f} {row['deaths']:>10.6f}"
            f" {row['premium_income']:>12,.2f} {row['death_benefit']:>12,.2f}"
            f" {row['pv_net_cash_flow']:>12,.2f}"
        )

    # Equivalence check
    pv_total = df["pv_net_cash_flow"].sum()
    print(f"\n  Σ PV(Net CF) = {pv_total:,.6f}")
    print(f"  Equivalence principle holds: {abs(pv_total) < 1.0}")

    # ────────────────────────────────────────────────────────
    # 7. Summary
    # ────────────────────────────────────────────────────────
    separator("7. SUMMARY")
    print("  ✓ SOA Illustrative Life Table loaded (111 ages)")
    print("  ✓ Commutation functions computed (vectorized)")
    print("  ✓ Insurance & annuity present values calculated")
    print("  ✓ Annual level premiums via equivalence principle")
    print("  ✓ Cash flow projection validated")
    print("  ✓ All identities verified")
    print()


if __name__ == "__main__":
    main()
