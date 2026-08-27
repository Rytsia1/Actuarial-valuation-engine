"""
Actuarial assumption data models.

Provides clean Pydantic v2 data structures for interest rate, mortality,
expense, and lapse assumptions used throughout the valuation engine.
The assumptions layer is intentionally decoupled from product contracts
and pricing engines.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class InterestAssumption(BaseModel):
    """Flat deterministic interest rate assumption.

    Provides the discount factor v = 1 / (1 + i) and the force of interest
    δ = ln(1 + i). Designed as an extensible base — stochastic interest
    models (Vasicek, Hull-White) will subclass or replace this in Level 4.

    Attributes:
        annual_rate: Annual effective interest rate (e.g., 0.05 for 5%).
    """

    annual_rate: float = Field(
        ...,
        ge=0.0,
        lt=1.0,
        description="Annual effective interest rate, e.g. 0.05 for 5% (0.0 allowed).",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def discount_factor(self) -> float:
        """Discount factor v = 1 / (1 + i)."""
        return 1.0 / (1.0 + self.annual_rate)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def force_of_interest(self) -> float:
        """Force of interest δ = ln(1 + i)."""
        import math

        return math.log(1.0 + self.annual_rate)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def effective_discount_rate(self) -> float:
        """Effective discount rate d = i / (1 + i) = 1 - v."""
        return self.annual_rate / (1.0 + self.annual_rate)


class MortalityAssumption(BaseModel):
    """Reference to a mortality table source.

    Points to either a named bundled table or a custom CSV path.
    The select period supports select-and-ultimate tables (Level 3+).

    Attributes:
        table_name: Name of the mortality table (e.g., 'soa_ilt').
        custom_path: Optional path to a custom CSV file.
        select_period: Select period duration (0 = ultimate only).
    """

    table_name: str = Field(
        default="soa_ilt",
        description="Name of the mortality table, e.g. 'soa_ilt'.",
    )
    custom_path: Optional[str] = Field(
        default=None,
        description="Path to a custom mortality table CSV file.",
    )
    select_period: int = Field(
        default=0,
        ge=0,
        description="Select period duration. 0 = ultimate table only.",
    )


class ExpenseAssumption(BaseModel):
    """Expense loading assumptions for gross premium calculation.

    Models both percentage-of-premium and per-policy flat-fee expenses,
    split between first-year (acquisition) and renewal years.

    Attributes:
        percent_of_premium_first: First-year expense as % of premium.
        percent_of_premium_renewal: Renewal expense as % of premium.
        per_policy_first: First-year per-policy flat expense.
        per_policy_renewal: Renewal per-policy flat expense.
    """

    percent_of_premium_first: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="First-year expense as a fraction of premium.",
    )
    percent_of_premium_renewal: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Renewal-year expense as a fraction of premium.",
    )
    per_policy_first: float = Field(
        default=0.0,
        ge=0.0,
        description="First-year per-policy flat expense amount.",
    )
    per_policy_renewal: float = Field(
        default=0.0,
        ge=0.0,
        description="Renewal per-policy flat expense amount.",
    )


class LapseAssumption(BaseModel):
    """Lapse and surrender rate assumptions.

    Supports both a flat annual lapse rate and a vector of duration-specific
    rates. When both are provided, the duration-specific vector takes priority.

    Attributes:
        flat_annual_rate: Constant annual lapse rate.
        duration_rates: Optional list of lapse rates by policy duration.
    """

    flat_annual_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Flat annual lapse rate (e.g. 0.05 for 5%).",
    )
    duration_rates: Optional[list[float]] = Field(
        default=None,
        description="Duration-specific lapse rates [year1, year2, ...].",
    )

    @field_validator("duration_rates", mode="after")
    @classmethod
    def validate_duration_rates(cls, v: Optional[list[float]]) -> Optional[list[float]]:
        """Validate that all duration-specific lapse rates are valid probabilities in [0.0, 1.0]."""
        if v is None:
            return None
        import math

        for idx, rate in enumerate(v):
            if rate is None or math.isnan(rate) or math.isinf(rate):
                raise ValueError(
                    f"duration_rates[{idx}] must be a finite number, got {rate}."
                )
            if not (0.0 <= rate <= 1.0):
                raise ValueError(
                    f"duration_rates[{idx}] ({rate}) must be a valid probability in range [0.0, 1.0]."
                )
        return v

    def get_rate(self, duration: int) -> float:
        """Get lapse rate for a specific policy duration (1-indexed).

        Args:
            duration: Policy year (1 = first year).

        Returns:
            Lapse rate for that duration.
        """
        if self.duration_rates is not None and 1 <= duration <= len(self.duration_rates):
            return self.duration_rates[duration - 1]
        return self.flat_annual_rate


class ValuationAssumptions(BaseModel):
    """Complete bundle of assumptions for a valuation run.

    Aggregates all assumption dimensions needed to value a life insurance
    policy or portfolio. Optional components (expenses, lapses) default
    to zero-impact when omitted.

    Attributes:
        interest: Interest rate assumption.
        mortality: Mortality table reference.
        expense: Optional expense loading (Level 3).
        lapse: Optional lapse/surrender assumption (Level 3).
        valuation_date: Optional valuation date string (ISO format).
    """

    interest: InterestAssumption
    mortality: MortalityAssumption = Field(default_factory=MortalityAssumption)
    expense: Optional[ExpenseAssumption] = None
    lapse: Optional[LapseAssumption] = None
    valuation_date: Optional[str] = Field(
        default=None,
        description="Valuation date in ISO format (YYYY-MM-DD).",
    )

    @model_validator(mode="after")
    def validate_assumptions(self) -> "ValuationAssumptions":
        """Ensure assumption bundle is internally consistent."""
        # Future: cross-validate interest rate period with mortality table period, etc.
        return self
