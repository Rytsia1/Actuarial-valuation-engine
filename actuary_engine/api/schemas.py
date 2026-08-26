"""
API Data Transfer Objects (DTOs) and Pydantic schemas for valuation endpoints.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from actuary_engine.models.assumptions import (
    ExpenseAssumption,
    LapseAssumption,
)
from actuary_engine.models.contracts import ProductType
from actuary_engine.stochastic.dynamic_lapse import DynamicLapseParams
from actuary_engine.stochastic.esg import VasicekParams


class DeterministicValuationRequest(BaseModel):
    """Request schema for deterministic pricing, reserves, and GPV rollout."""

    product_type: ProductType = Field(
        default=ProductType.TERM,
        description="Insurance product type (term, whole_life, endowment, pure_endowment).",
    )
    issue_age: int = Field(default=30, ge=0, le=120, description="Age at policy issue.")
    term: Optional[int] = Field(default=20, gt=0, description="Policy coverage term (years).")
    sum_assured: float = Field(default=1_000_000.0, gt=0.0, description="Face amount / death benefit.")
    premium_paying_term: Optional[int] = Field(
        default=None, gt=0, description="Premium paying period (years)."
    )
    interest_rate: float = Field(
        default=0.05, gt=0.0, lt=1.0, description="Annual effective interest rate (e.g. 0.05 for 5%)."
    )
    gross_premium: Optional[float] = Field(
        default=None, gt=0.0, description="Annual gross premium (defaults to net premium with 20% loading)."
    )
    expense: Optional[ExpenseAssumption] = Field(
        default=None, description="Acquisition and maintenance expense loadings."
    )
    lapse: Optional[LapseAssumption] = Field(
        default=None, description="Static lapse / surrender assumption."
    )


class DeterministicValuationResponse(BaseModel):
    """Response schema for deterministic valuation."""

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
    """Request schema for Monte Carlo stochastic liability and tail-risk simulation."""

    product_type: ProductType = Field(
        default=ProductType.TERM, description="Product type."
    )
    issue_age: int = Field(default=30, ge=0, le=120, description="Issue age.")
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

