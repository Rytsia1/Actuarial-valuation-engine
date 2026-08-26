"""
FastAPI application layer for the Actuarial Valuation & Risk Engine.

Provides REST and WebSocket endpoints for:
- Health check & mortality table metadata (/api/v1/health, /api/v1/tables/soa_ilt)
- Deterministic life insurance valuation (/api/v1/valuation/deterministic)
- Stochastic Monte Carlo valuation with Vasicek ESG (/api/v1/valuation/stochastic)
- Asynchronous large-scale simulation dispatch (/api/v1/valuation/stochastic/async)
- Polling status endpoint (/api/v1/valuation/stochastic/status/{job_id})
- Bidirectional WebSocket progress streaming (/ws/simulations/{job_id})
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from actuary_engine.api.job_manager import JobStatus, job_manager
from actuary_engine.api.schemas import (
    AsyncJobCreateResponse,
    AsyncJobStatusResponse,
    DeterministicValuationRequest,
    DeterministicValuationResponse,
    StochasticValuationRequest,
    StochasticValuationResponse,
)
from actuary_engine.models.assumptions import ExpenseAssumption, InterestAssumption, LapseAssumption
from actuary_engine.models.contracts import PolicyContract
from actuary_engine.pricing.premium import LevelPremiumCalculator
from actuary_engine.stochastic.dynamic_lapse import DynamicLapseModel
from actuary_engine.stochastic.esg import VasicekESG
from actuary_engine.stochastic.monte_carlo import StochasticValuationEngine
from actuary_engine.tables.commutation import CommutationFunctions
from actuary_engine.tables.mortality_table import MortalityTable
from actuary_engine.valuation.gpv import GrossPremiumValuation
from actuary_engine.valuation.reserves import ReserveCalculator

logger = logging.getLogger("actuary_engine.api")

# Initialize FastAPI App
app = FastAPI(
    title="Actuarial Valuation & Risk Engine API",
    version="0.3.0",
    description="Production-grade API for life insurance liabilities, reserves, and Monte Carlo risk analytics with WebSockets.",
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
def get_soa_ilt_info() -> dict[str, object]:
    """Retrieve metadata and sample mortality rates for SOA Illustrative Life Table."""
    sample_ages = [20, 30, 40, 50, 60, 70, 80, 90, 100]
    sample_qx = {f"q{age}": round(float(table.get_tqx(age, 1)), 6) for age in sample_ages}
    return {
        "name": table.name,
        "min_age": table.min_age,
        "max_age": table.max_age,
        "omega": table.omega,
        "radix": table.radix,
        "sample_qx": sample_qx,
    }


@app.post("/api/v1/valuation/deterministic", response_model=DeterministicValuationResponse)
def evaluate_deterministic(request: DeterministicValuationRequest) -> DeterministicValuationResponse:
    """Run deterministic valuation computing net level premiums, prospective/retrospective reserves, and GPV rollout."""
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
    prem_calc = LevelPremiumCalculator(comm)

    # 1. Net Level Premium Pricing & Equivalence
    prem_res = prem_calc.price_contract(contract)
    net_premium = prem_res.annual_premium
    nsp = prem_res.nsp
    annuity_factor = prem_res.annuity_factor

    # 2. Derive gross premium if not explicitly supplied (default 20% loading)
    gross_premium = request.gross_premium if request.gross_premium is not None else net_premium * 1.20

    # 3. Reserve Calculation (Prospective & Retrospective)
    res_calc = ReserveCalculator(comm)
    net_res_df = res_calc.reserve_profile(contract, annual_premium=net_premium, method="both")

    # 4. Gross Premium Valuation (GPV)
    expense = request.expense or ExpenseAssumption(
        percent_of_premium_first=0.35,
        percent_of_premium_renewal=0.05,
        per_policy_first=200.0,
        per_policy_renewal=20.0,
    )
    lapse = request.lapse or LapseAssumption(flat_annual_rate=0.03)

    gpv_engine = GrossPremiumValuation(
        table=table,
        interest=interest,
        expense=expense,
        lapse=lapse,
    )

    gpv_cf_df = gpv_engine.project(contract, gross_premium=gross_premium)
    bel = gpv_engine.best_estimate_liability(contract, gross_premium=gross_premium)
    gpv_res_df = gpv_engine.gross_reserve_profile(contract, gross_premium=gross_premium)

    # Prepare combined reserve profile list
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


async def _compute_stochastic_valuation_core(
    request: StochasticValuationRequest,
    progress_callback: Optional[Callable[[int, int, dict[str, Any]], Coroutine[Any, Any, None]]] = None,
) -> StochasticValuationResponse:
    """Internal helper to compute stochastic Monte Carlo valuation with chunking and fan chart analytics."""
    contract = PolicyContract(
        product_type=request.product_type,
        issue_age=request.issue_age,
        term=request.term,
        sum_assured=request.sum_assured,
        premium_paying_term=request.premium_paying_term,
    )

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

    chunk_size = min(1000, max(250, request.n_scenarios // 10))
    stoch_res, _ = await engine.evaluate_liability_distribution(
        contract=contract,
        gross_premium=gross_premium,
        n_scenarios=request.n_scenarios,
        chunk_size=chunk_size,
        seed=request.seed,
        progress_callback=progress_callback,
    )

    # Fan chart analytics for short rates
    n_years = contract.term if contract.term is not None else (table.omega - contract.issue_age)
    rates_paths = esg.simulate_paths(
        n_scenarios=min(2500, request.n_scenarios),
        n_years=n_years,
        dt=1.0,
        method="exact",
        seed=request.seed,
    )

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

    sample_paths = [
        [round(float(r), 5) for r in rates_paths[i, :]]
        for i in range(min(12, request.n_scenarios))
    ]

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


@app.post("/api/v1/valuation/stochastic", response_model=StochasticValuationResponse)
async def evaluate_stochastic(request: StochasticValuationRequest) -> StochasticValuationResponse:
    """Run synchronous Monte Carlo simulation."""
    try:
        return await _compute_stochastic_valuation_core(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


async def _run_async_simulation_worker(job_id: str, request: StochasticValuationRequest) -> None:
    """Background worker task streaming progress updates to JobManager."""
    async def progress_hook(completed: int, total: int, partial_metrics: dict[str, Any]) -> None:
        await job_manager.update_progress(
            job_id=job_id,
            completed_paths=completed,
            total_paths=total,
            partial_metrics=partial_metrics,
        )

    try:
        response = await _compute_stochastic_valuation_core(
            request=request,
            progress_callback=progress_hook,
        )
        await job_manager.set_completed(job_id=job_id, result_data=response.model_dump())
    except Exception as e:
        logger.exception("Async stochastic simulation failed for job_id=%s", job_id)
        await job_manager.set_failed(job_id=job_id, error_message=str(e))


from fastapi import BackgroundTasks

@app.post("/api/v1/valuation/stochastic/async", response_model=AsyncJobCreateResponse, status_code=202)
def evaluate_stochastic_async(
    request: StochasticValuationRequest,
    background_tasks: BackgroundTasks,
) -> AsyncJobCreateResponse:
    """Enqueue a large-scale stochastic simulation task, returning an immediate job ID and WebSocket URL."""
    try:
        # Validate contract parameters
        PolicyContract(
            product_type=request.product_type,
            issue_age=request.issue_age,
            term=request.term,
            sum_assured=request.sum_assured,
            premium_paying_term=request.premium_paying_term,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    job = job_manager.create_job(total_paths=request.n_scenarios)
    background_tasks.add_task(_run_async_simulation_worker, job.job_id, request)

    return AsyncJobCreateResponse(
        job_id=job.job_id,
        status="QUEUED",
        total_paths=request.n_scenarios,
        ws_endpoint=f"/ws/simulations/{job.job_id}",
    )


@app.get("/api/v1/valuation/stochastic/status/{job_id}", response_model=AsyncJobStatusResponse)
def get_stochastic_job_status(job_id: str) -> AsyncJobStatusResponse:
    """Poll the status and output of an asynchronous simulation job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID '{job_id}' not found.")

    res_obj = StochasticValuationResponse(**job.result) if job.result is not None else None

    return AsyncJobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        completed_paths=job.completed_paths,
        total_paths=job.total_paths,
        partial_metrics=job.partial_metrics,
        result=res_obj,
        error=job.error,
    )


@app.websocket("/ws/simulations/{job_id}")
async def websocket_simulation_progress(websocket: WebSocket, job_id: str) -> None:
    """Bidirectional WebSocket connection broadcasting incremental progress and final simulation results."""
    await websocket.accept()

    job = job_manager.get_job(job_id)
    if not job:
        await websocket.send_json({
            "type": "ERROR",
            "job_id": job_id,
            "status": "FAILED",
            "error": f"Job '{job_id}' not found.",
        })
        await websocket.close()
        return

    # If already completed or failed prior to connection
    if job.status == JobStatus.COMPLETED:
        await websocket.send_json({
            "type": "COMPLETE",
            "job_id": job_id,
            "status": "COMPLETED",
            "percent": 100.0,
            "completed_paths": job.total_paths,
            "total_paths": job.total_paths,
            "data": job.result,
        })
        await websocket.close()
        return
    elif job.status == JobStatus.FAILED:
        await websocket.send_json({
            "type": "ERROR",
            "job_id": job_id,
            "status": "FAILED",
            "error": job.error or "Simulation failed.",
        })
        await websocket.close()
        return

    queue = job_manager.subscribe(job_id)
    try:
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=120.0)
            await websocket.send_json(event)
            if event.get("type") in ("COMPLETE", "ERROR"):
                break
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except asyncio.TimeoutError:
        try:
            await websocket.send_json({
                "type": "ERROR",
                "job_id": job_id,
                "error": "Simulation WebSocket timed out after 120s of inactivity.",
            })
        except Exception:
            pass
    finally:
        job_manager.unsubscribe(job_id, queue)
        try:
            await websocket.close()
        except Exception:
            pass
