"""
Pydantic Request and Response schemas for the Actuarial Valuation API.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from actuary_engine.models.assumptions import ExpenseAssumption, LapseAssumption
from actuary_engine.models.contracts import ProductType
from actuary_engine.stochastic.dynamic_lapse import DynamicLapseParams
from actuary_engine.stochastic.esg import VasicekParams


class DeterministicValuationRequest(BaseModel):
    """Request payload for Level 1-3 deterministic life insurance valuation."""

    product_type: ProductType = Field(
        default=ProductType.ENDOWMENT, description="Insurance product type."
    )
    issue_age: int = Field(default=30, ge=0, le=105, description="Policyholder issue age.")
    term: Optional[int] = Field(default=20, gt=0, description="Coverage term in years.")
    sum_assured: float = Field(default=1_000_000.0, gt=0.0, description="Sum assured / Face amount.")
    premium_paying_term: Optional[int] = Field(default=None, gt=0, description="Premium paying term.")
    interest_rate: float = Field(default=0.05, gt=0.0, le=0.50, description="Annual effective interest rate.")
    gross_premium: Optional[float] = Field(
        default=None, gt=0.0, description="Gross premium. If None, calculated with 20% loading."
    )
    expense: Optional[ExpenseAssumption] = Field(
        default=None, description="Expense loadings."
    )
    lapse: Optional[LapseAssumption] = Field(
        default=None, description="Policyholder lapse decrement rates."
    )


class DeterministicValuationResponse(BaseModel):
    """Response schema for deterministic valuation results."""

    product_type: str
    issue_age: int
    term: Optional[int]
    sum_assured: float
    annual_net_premium: float
    annual_gross_premium: float
    nsp: float
    annuity_factor: float
    bel: float
    reserve_profile: list[dict[str, Any]]
    cash_flows: list[dict[str, Any]]


class StochasticValuationRequest(BaseModel):
    """Request payload for Level 4 stochastic Monte Carlo risk simulation."""

    product_type: ProductType = Field(
        default=ProductType.ENDOWMENT, description="Insurance product type."
    )
    issue_age: int = Field(default=30, ge=0, le=105, description="Policyholder issue age.")
    term: Optional[int] = Field(default=20, gt=0, description="Coverage term in years.")
    sum_assured: float = Field(default=1_000_000.0, gt=0.0, description="Sum assured / Face amount.")
    premium_paying_term: Optional[int] = Field(default=None, gt=0, description="Premium paying term.")
    gross_premium: Optional[float] = Field(
        default=None, gt=0.0, description="Gross premium. If None, calculated with 25% loading."
    )
    vasicek: VasicekParams = Field(
        default_factory=lambda: VasicekParams(r0=0.05, kappa=0.20, theta=0.05, sigma=0.015),
        description="Vasicek ESG short-rate model parameters.",
    )
    dynamic_lapse: Optional[DynamicLapseParams] = Field(
        default=None, description="Dynamic S-curve lapse parameters."
    )
    expense: Optional[ExpenseAssumption] = Field(
        default=None, description="Expense loadings."
    )
    n_scenarios: int = Field(
        default=2000, ge=50, le=50000, description="Number of Monte Carlo scenario paths."
    )
    seed: Optional[int] = Field(default=42, description="Random seed for reproducibility.")


class StochasticValuationResponse(BaseModel):
    """Response schema for stochastic Monte Carlo valuation and fan chart data."""

    mean_bel: float
    std_bel: float
    min_bel: float
    max_bel: float
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    percentiles: dict[str, float]
    fan_chart_rates: list[dict[str, Any]]
    liability_histogram: list[dict[str, Any]]
    sample_paths: list[list[float]]


class AsyncJobCreateResponse(BaseModel):
    """Response returned upon enqueuing an asynchronous simulation task."""

    job_id: str = Field(..., description="Unique simulation job identifier.")
    status: str = Field(default="QUEUED", description="Initial job status.")
    total_paths: int = Field(..., description="Target number of Monte Carlo paths.")
    ws_endpoint: str = Field(..., description="WebSocket URI for streaming progress.")


class AsyncJobStatusResponse(BaseModel):
    """Polling response schema for job status."""

    job_id: str
    status: str
    progress: float
    completed_paths: int
    total_paths: int
    partial_metrics: Optional[dict[str, Any]] = None
    result: Optional[StochasticValuationResponse] = None
    error: Optional[str] = None


# ────────────────────────────────────────────────────────────
# Portfolio Batch Valuation Schemas
# ────────────────────────────────────────────────────────────

class PortfolioPolicyRecord(BaseModel):
    """Individual policy input item for JSON portfolio batch requests."""

    policy_id: Optional[str] = Field(default=None, description="Unique policy identifier.")
    issue_age: int = Field(..., ge=0, le=105, description="Issue age.")
    term_years: Optional[int] = Field(default=20, ge=1, description="Policy term in years.")
    sum_assured: float = Field(..., gt=0.0, description="Sum assured / Face amount.")
    gross_premium: float = Field(..., gt=0.0, description="Annual gross premium.")
    product_type: str = Field(default="term", description="Product type (term, endowment, whole_life, pure_endowment).")
    policy_duration_years: int = Field(default=0, ge=0, description="Current policy in-force duration.")
    gender: Optional[str] = Field(default="U", description="Gender (M, F, U).")


class PortfolioValuationJSONRequest(BaseModel):
    """JSON batch request schema for evaluating a portfolio of contracts."""

    policies: list[PortfolioPolicyRecord] = Field(..., description="List of policy contracts.")
    interest_rate: float = Field(default=0.05, gt=0.0, le=0.50, description="Discount rate.")
    expense: Optional[ExpenseAssumption] = Field(default=None, description="Expense assumptions.")
    lapse: Optional[LapseAssumption] = Field(default=None, description="Lapse assumptions.")


class PortfolioValuationResponse(BaseModel):
    """Response schema for aggregate portfolio liabilities and segment breakdowns."""

    total_policies: int
    total_sum_assured: float
    total_pvfb: float
    total_pvfp: float
    total_pvfe: float
    total_bel: float
    annual_cash_flows: list[dict[str, Any]]
    product_breakdown: dict[str, dict[str, Any]]
    age_breakdown: dict[str, dict[str, Any]]
    duration_breakdown: dict[str, dict[str, Any]]
    sample_seriatim: list[dict[str, Any]]
