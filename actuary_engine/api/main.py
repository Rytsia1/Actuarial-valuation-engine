"""
FastAPI application for the Actuarial Valuation & Risk Engine.

Provides RESTful endpoints for deterministic pricing, prospective/retrospective
reserves, multi-decrement Gross Premium Valuation, and stochastic Monte Carlo
simulation with Vasicek ESG and dynamic policyholder behavior.
"""

from __future__ import annotations

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from actuary_engine.api.schemas import (
    DeterministicValuationRequest,
    DeterministicValuationResponse,
    StochasticValuationRequest,
    StochasticValuationResponse,
)
from actuary_engine.models.assumptions import (
    ExpenseAssumption,
    InterestAssumption,
    LapseAssumption,
)
from actuary_engine.models.contracts import PolicyContract, ProductType
from actuary_engine.pricing.premium import LevelPremiumCalculator
from actuary_engine.stochastic.dynamic_lapse import DynamicLapseModel
from actuary_engine.stochastic.esg import VasicekESG
from actuary_engine.stochastic.monte_carlo import StochasticValuationEngine
from actuary_engine.tables.commutation import CommutationFunctions
from actuary_engine.tables.mortality_table import MortalityTable
from actuary_engine.valuation.gpv import GrossPremiumValuation
from actuary_engine.valuation.reserves import ReserveCalculator

# Initialize FastAPI App
app = FastAPI(
    title="Actuarial Valuation & Risk Engine API",
    version="0.3.0",
    description="Production-grade API for life insurance liabilities, reserves, and Monte Carlo risk analytics.",
)

# Configure CORS for Vue 3 frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load SOA Illustrative Life Table singleton
table = MortalityTable.from_soa_ilt()


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "actuary-engine-api",
        "table": table.name,
        "omega": str(table.omega),
    }


@app.get("/api/v1/tables/soa_ilt")
def get_table_metadata() -> dict[str, object]:
    """Return SOA Illustrative Life Table summary metadata."""
    return {
        "name": table.name,
        "min_age": table.min_age,
        "max_age": table.max_age,
        "omega": table.omega,
        "radix": table.radix,
        "sample_qx": {
            "q20": table.get_qx(20),
            "q30": table.get_qx(30),
            "q40": table.get_qx(40),
            "q50": table.get_qx(50),
            "q60": table.get_qx(60),
            "q70": table.get_qx(70),
        },
    }


@app.post("/api/v1/valuation/deterministic", response_model=DeterministicValuationResponse)
def evaluate_deterministic(request: DeterministicValuationRequest) -> DeterministicValuationResponse:
    """Compute deterministic pricing, prospective & retrospective reserves, and GPV rollout."""
    try:
        contract = PolicyContract(
            product_type=request.product_type,
            issue_age=request.issue_age,
            term=request.term,
            sum_assured=request.sum_assured,
            premium_paying_term=request.premium_paying_term,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    interest = InterestAssumption(annual_rate=request.interest_rate)
    comm = CommutationFunctions(table, interest)
    calc = LevelPremiumCalculator(comm)

    # 1. Net Level Premium Pricing
    prem_result = calc.price_contract(contract)
    net_premium = prem_result.annual_premium
    nsp = prem_result.nsp
    annuity_factor = prem_result.annuity_factor

    # Gross premium: use requested or default to 20% loaded
    gross_premium = request.gross_premium if request.gross_premium is not None else net_premium * 1.20

    # 2. Net Reserves (Prospective & Retrospective)
    res_calc = ReserveCalculator(comm)
    net_res_df = res_calc.reserve_profile(contract, net_premium, method="both")

    # 3. Gross Premium Valuation & Multi-Decrement Rollout
    expense = request.expense or ExpenseAssumption(
        percent_of_premium_first=0.35,
        percent_of_premium_renewal=0.05,
        per_policy_first=200.0,
        per_policy_renewal=20.0,
    )
    lapse = request.lapse or LapseAssumption(
        duration_rates=[0.08, 0.05, 0.04, 0.03],
        flat_annual_rate=0.02,
    )

    gpv = GrossPremiumValuation(
        table=table,
        interest=interest,
        expense=expense,
        lapse=lapse,
    )

    gpv_cf_df = gpv.project(contract, gross_premium)
    gpv_res_df = gpv.gross_reserve_profile(contract, gross_premium)
    bel = gpv.best_estimate_liability(contract, gross_premium)

    # Merge reserve profiles
    reserve_profile_data: list[dict[str, object]] = []
    for t_idx in range(len(net_res_df)):
        dur = int(net_res_df["duration"].iloc[t_idx])
        age = int(net_res_df["age"].iloc[t_idx])
        pro_res = float(net_res_df["reserve_prospective"].iloc[t_idx])
        retro_res = float(net_res_df["reserve_retrospective"].iloc[t_idx])
        gross_res = float(gpv_res_df["gross_reserve"].iloc[t_idx]) if t_idx < len(gpv_res_df) else 0.0

        reserve_profile_data.append({
            "duration": dur,
            "age": age,
            "reserve_prospective": round(pro_res, 2),
            "reserve_retrospective": round(retro_res, 2),
            "gross_reserve": round(gross_res, 2),
        })

    # Prepare cash flow list
    cash_flows: list[dict[str, object]] = []
    for _, row in gpv_cf_df.iterrows():
        cash_flows.append({
            "year": int(row["year"]),
            "age": int(row["age"]),
            "inforce_boy": round(float(row["inforce_boy"]), 6),
            "premium_income": round(float(row["premium_income"]), 2),
            "death_claims": round(float(row["death_claims"]), 2),
            "lapse_payouts": round(float(row["lapse_payouts"]), 2),
            "maturity_benefit": round(float(row["maturity_benefit"]), 2),
            "total_expense": round(float(row["total_expense"]), 2),
            "net_liability_cf": round(float(row["net_liability_cf"]), 2),
            "pv_net_liability": round(float(row["pv_net_liability"]), 2),
        })

    return DeterministicValuationResponse(
        product_type=contract.product_type.value,
        issue_age=contract.issue_age,
        term=contract.term,
        sum_assured=contract.sum_assured,
        annual_net_premium=round(net_premium, 2),
        annual_gross_premium=round(gross_premium, 2),
        nsp=round(nsp, 2),
        annuity_factor=round(annuity_factor, 4),
        bel=round(bel, 2),
        reserve_profile=reserve_profile_data,
        cash_flows=cash_flows,
    )


@app.post("/api/v1/valuation/stochastic", response_model=StochasticValuationResponse)
def evaluate_stochastic(request: StochasticValuationRequest) -> StochasticValuationResponse:
    """Run Monte Carlo simulation of path-dependent liabilities, ESG fan chart, and VaR/CVaR."""
    try:
        contract = PolicyContract(
            product_type=request.product_type,
            issue_age=request.issue_age,
            term=request.term,
            sum_assured=request.sum_assured,
            premium_paying_term=request.premium_paying_term,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Derive gross premium if not explicitly supplied
    if request.gross_premium is not None:
        gross_premium = request.gross_premium
    else:
        comm = CommutationFunctions(table, InterestAssumption(annual_rate=request.vasicek.r0))
        calc = LevelPremiumCalculator(comm)
        prem_res = calc.price_contract(contract)
        gross_premium = prem_res.annual_premium * 1.25

    esg = VasicekESG(params=request.vasicek, seed=request.seed)
    dyn_lapse = DynamicLapseModel(params=request.dynamic_lapse) if request.dynamic_lapse is not None else None

    expense = request.expense or ExpenseAssumption(
        percent_of_premium_first=0.35,
        percent_of_premium_renewal=0.05,
        per_policy_first=200.0,
        per_policy_renewal=20.0,
    )

    engine = StochasticValuationEngine(
        table=table,
        esg=esg,
        expense=expense,
        dynamic_lapse=dyn_lapse,
    )

    stoch_res = engine.run_simulation(
        contract=contract,
        gross_premium=gross_premium,
        n_scenarios=request.n_scenarios,
        seed=request.seed,
    )

    # Generate Fan Chart Percentiles for Short Rates across policy years
    n_years = contract.term if contract.term is not None else (table.omega - contract.issue_age)
    rates_paths = esg.simulate_paths(
        n_scenarios=request.n_scenarios,
        n_years=n_years,
        dt=1.0,
        method="exact",
        seed=request.seed,
    )  # (n_scenarios, n_years + 1)

    fan_chart_rates: list[dict[str, object]] = []
    for t_idx in range(n_years + 1):
        step_rates = rates_paths[:, t_idx]
        fan_chart_rates.append({
            "year": t_idx,
            "age": contract.issue_age + t_idx,
            "p5": round(float(np.percentile(step_rates, 5.0)), 5),
            "p25": round(float(np.percentile(step_rates, 25.0)), 5),
            "p50": round(float(np.percentile(step_rates, 50.0)), 5),
            "p75": round(float(np.percentile(step_rates, 75.0)), 5),
            "p95": round(float(np.percentile(step_rates, 95.0)), 5),
            "mean": round(float(np.mean(step_rates)), 5),
        })

    # Sample 12 individual paths for visualization
    sample_paths = [
        [round(float(r), 5) for r in rates_paths[i, :]]
        for i in range(min(12, request.n_scenarios))
    ]

    # Generate Liability Distribution Histogram (30 bins)
    bel_array = stoch_res.scenario_bel
    counts, bin_edges = np.histogram(bel_array, bins=30)
    liability_histogram: list[dict[str, object]] = []
    for i in range(len(counts)):
        mid_bin = 0.5 * (bin_edges[i] + bin_edges[i + 1])
        liability_histogram.append({
            "bin_start": round(float(bin_edges[i]), 2),
            "bin_end": round(float(bin_edges[i + 1]), 2),
            "bin_mid": round(float(mid_bin), 2),
            "count": int(counts[i]),
        })

    return StochasticValuationResponse(
        mean_bel=round(stoch_res.mean_bel, 2),
        std_bel=round(stoch_res.std_bel, 2),
        min_bel=round(stoch_res.min_bel, 2),
        max_bel=round(stoch_res.max_bel, 2),
        var_95=round(stoch_res.var_95, 2),
        var_99=round(stoch_res.var_99, 2),
        cvar_95=round(stoch_res.cvar_95, 2),
        cvar_99=round(stoch_res.cvar_99, 2),
        percentiles={k: round(v, 2) for k, v in stoch_res.percentiles.items()},
        fan_chart_rates=fan_chart_rates,
        liability_histogram=liability_histogram,
        sample_paths=sample_paths,
    )
