#!/usr/bin/env python3
"""
Actuary Engine — Quickstart Demo
=================================

End-to-end demonstration of the actuarial valuation engine:
1. Load the SOA Illustrative Life Table
2. Build commutation functions at 5% interest
3. Price multiple insurance products
4. Compute annual level premiums
5. Project deterministic cash flows & validate equivalence principle
6. Compute prospective & retrospective policy reserves (_t V)
7. Gross Premium Valuation (GPV / BEL) with expenses & lapses
"""

import sys
from pathlib import Path

# Add project root to sys.path so it works directly across environments
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    ExpenseAssumption,
    LapseAssumption,
    PolicyContract,
    ProductType,
    ReserveCalculator,
    GrossPremiumValuation,
    VasicekParams,
    VasicekESG,
    DynamicLapseParams,
    DynamicLapseModel,
    StochasticValuationEngine,
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
    # 6. Policy Reserves (Level 3)
    # ────────────────────────────────────────────────────────
    separator("6. POLICY RESERVES (_t V) — 20-Year Endowment (Face = 1,000,000)")

    endow_contract = PolicyContract(
        product_type=ProductType.ENDOWMENT,
        issue_age=30,
        term=20,
        sum_assured=face,
    )
    endow_prem = calc.annual_premium_endowment(30, 20, face).annual_premium
    res_calc = ReserveCalculator(comm)

    res_df = res_calc.reserve_profile(endow_contract, endow_prem, method="both")
    print(f"  Annual Premium: {endow_prem:,.2f}")
    print()
    print(f"  {'Duration (t)':>12} {'Age':>5} {'_t V (Prospective)':>20} {'_t V (Retrospective)':>20} {'Match?':>8}")
    print(f"  {'─'*12} {'─'*5} {'─'*20} {'─'*20} {'─'*8}")
    for t_idx in [0, 1, 5, 10, 15, 19, 20]:
        row = res_df.loc[res_df["duration"] == t_idx].iloc[0]
        match = abs(row["reserve_prospective"] - row["reserve_retrospective"]) < 1e-4
        print(
            f"  {int(row['duration']):>12} {int(row['age']):>5}"
            f" {row['reserve_prospective']:>20,.2f}"
            f" {row['reserve_retrospective']:>20,.2f}"
            f" {'✓' if match else '✗':>8}"
        )

    # ────────────────────────────────────────────────────────
    # 7. Gross Premium Valuation / BEL (Level 3)
    # ────────────────────────────────────────────────────────
    separator("7. GROSS PREMIUM VALUATION & BEL — 20-Year Term with Expenses & Lapses")

    term_contract = PolicyContract(
        product_type=ProductType.TERM,
        issue_age=30,
        term=20,
        sum_assured=face,
    )
    term_net_p = calc.annual_premium_term(30, 20, face).annual_premium

    gpv = GrossPremiumValuation(
        table=table,
        interest=interest,
        expense=ExpenseAssumption(
            percent_of_premium_first=0.40,
            percent_of_premium_renewal=0.05,
            per_policy_first=250.0,
            per_policy_renewal=25.0,
        ),
        lapse=LapseAssumption(
            duration_rates=[0.08, 0.05, 0.04, 0.03],
            flat_annual_rate=0.02,
        ),
    )

    bel_net = gpv.best_estimate_liability(term_contract, term_net_p)
    gross_p = term_net_p * 1.30  # 30% gross loading
    bel_gross = gpv.best_estimate_liability(term_contract, gross_p)

    print(f"  Net Level Premium:          ${term_net_p:>10,.2f}")
    print(f"  BEL at Net Premium:         ${bel_net:>10,.2f}  (Unfunded expenses liability)")
    print(f"  Gross Premium (1.3x):       ${gross_p:>10,.2f}")
    print(f"  BEL at Gross Premium:       ${bel_gross:>10,.2f}  (Negative = embedded profit)")

    # ────────────────────────────────────────────────────────
    # 8. Stochastic Monte Carlo Valuation & Tail Risk (Level 4)
    # ────────────────────────────────────────────────────────
    separator("8. STOCHASTIC MONTE CARLO & TAIL RISK — Vasicek ESG + Dynamic Lapses")

    esg = VasicekESG(
        params=VasicekParams(r0=0.05, kappa=0.20, theta=0.05, sigma=0.015),
        seed=42,
    )
    dyn_lapse = DynamicLapseModel(
        params=DynamicLapseParams(
            base_lapse_rate=0.04,
            credited_rate=0.04,
            min_lapse_rate=0.01,
            max_lapse_rate=0.35,
            sensitivity=25.0,
        )
    )

    stoch_engine = StochasticValuationEngine(
        table=table,
        esg=esg,
        expense=ExpenseAssumption(
            percent_of_premium_first=0.40,
            percent_of_premium_renewal=0.05,
            per_policy_first=250.0,
            per_policy_renewal=25.0,
        ),
        dynamic_lapse=dyn_lapse,
    )

    stoch_result = stoch_engine.run_simulation(
        contract=term_contract,
        gross_premium=gross_p,
        n_scenarios=2500,
        seed=100,
    )

    print(f"  Simulated Scenarios:        {len(stoch_result.scenario_bel):,}")
    print(f"  Mean Stochastic BEL:        ${stoch_result.mean_bel:>10,.2f}")
    print(f"  Std Dev (Liability):        ${stoch_result.std_bel:>10,.2f}")
    print(f"  50th Percentile (Median):   ${stoch_result.percentiles['50%']:>10,.2f}")
    print(f"  95% Value at Risk (VaR):    ${stoch_result.var_95:>10,.2f}")
    print(f"  99% Value at Risk (VaR):    ${stoch_result.var_99:>10,.2f}")
    print(f"  95% Expected Shortfall:     ${stoch_result.cvar_95:>10,.2f}  (CVaR / CTE 95)")
    print(f"  99% Expected Shortfall:     ${stoch_result.cvar_99:>10,.2f}  (CVaR / CTE 99)")

    # ────────────────────────────────────────────────────────
    # 9. Summary
    # ────────────────────────────────────────────────────────
    separator("9. SUMMARY")
    print("  ✓ SOA Illustrative Life Table loaded (111 ages)")
    print("  ✓ Commutation functions computed (vectorized)")
    print("  ✓ Insurance & annuity present values calculated")
    print("  ✓ Annual level premiums via equivalence principle")
    print("  ✓ Prospective & retrospective reserves validated (_t V_pro ≡ _t V_retro)")
    print("  ✓ Best Estimate Liability (BEL) computed under multi-decrement model")
    print("  ✓ Vasicek ESG paths & dynamic S-curve lapse simulation executed")
    print("  ✓ Quantitative tail risk metrics (VaR 95/99, CVaR 95/99) aggregated")
    print()


if __name__ == "__main__":
    main()
