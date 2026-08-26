"""
Stochastic Valuation & Monte Carlo Risk Metrics Engine.

Provides:
- ``RiskMetricsResult``: Container for scenario BEL distributions, quantiles (VaR),
  and tail-risk measures (CVaR / Expected Shortfall).
- ``StochasticValuationEngine``: High-performance vectorized Monte Carlo engine
  coupling the Vasicek Economic Scenario Generator, dynamic policyholder lapse
  behavior, and mortality tables.

Mathematical Risk Measures:
    VaR_α (Value at Risk):
        VaR_α = inf { x ∈ ℝ : P(BEL ≤ x) ≥ α }

    CVaR_α / CTE_α (Conditional Value at Risk / Tail Value at Risk):
        CVaR_α = E[ BEL | BEL ≥ VaR_α ]
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from actuary_engine.models.assumptions import ExpenseAssumption, LapseAssumption
from actuary_engine.models.contracts import PolicyContract, ProductType
from actuary_engine.stochastic.dynamic_lapse import DynamicLapseModel
from actuary_engine.stochastic.esg import VasicekESG
from actuary_engine.tables.mortality_table import MortalityTable


class RiskMetricsResult(BaseModel):
    """Aggregated quantitative risk metrics from stochastic simulation.

    Attributes:
        mean_bel: Expected (mean) Best Estimate Liability across all scenarios.
        std_bel: Sample standard deviation of scenario BELs.
        var_95: Value at Risk at the 95% confidence level (95th percentile).
        var_99: Value at Risk at the 99% confidence level (99th percentile).
        cvar_95: Conditional Value at Risk / CTE at 95% (mean of worst 5% outcomes).
        cvar_99: Conditional Value at Risk / CTE at 99% (mean of worst 1% outcomes).
        min_bel: Best-case scenario liability (minimum).
        max_bel: Worst-case scenario liability (maximum).
        percentiles: Dictionary of selected percentiles (50%, 75%, 90%, 95%, 99%, 99.5%).
        scenario_bel: Full 1D array of scenario BELs (length = n_scenarios).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    mean_bel: float = Field(..., description="Mean Best Estimate Liability.")
    std_bel: float = Field(..., description="Standard deviation of liability.")
    var_95: float = Field(..., description="Value at Risk (95% percentile).")
    var_99: float = Field(..., description="Value at Risk (99% percentile).")
    cvar_95: float = Field(..., description="Conditional Value at Risk (95%).")
    cvar_99: float = Field(..., description="Conditional Value at Risk (99%).")
    min_bel: float = Field(..., description="Minimum scenario BEL.")
    max_bel: float = Field(..., description="Maximum scenario BEL.")
    percentiles: dict[str, float] = Field(default_factory=dict)
    scenario_bel: np.ndarray = Field(..., description="Array of all scenario BEL values.")

    def summary(self) -> pd.DataFrame:
        """Return a formatted summary DataFrame of key risk statistics."""
        data = {
            "Metric": [
                "Mean BEL",
                "Std Dev (BEL)",
                "Min BEL",
                "Median (50%)",
                "75th Percentile",
                "90th Percentile",
                "VaR 95%",
                "VaR 99%",
                "CVaR 95% (CTE 95)",
                "CVaR 99% (CTE 99)",
                "Max BEL",
            ],
            "Value": [
                self.mean_bel,
                self.std_bel,
                self.min_bel,
                self.percentiles.get("50%", np.nan),
                self.percentiles.get("75%", np.nan),
                self.percentiles.get("90%", np.nan),
                self.var_95,
                self.var_99,
                self.cvar_95,
                self.cvar_99,
                self.max_bel,
            ],
        }
        return pd.DataFrame(data)


class StochasticValuationEngine:
    """Vectorized Monte Carlo liability valuation and risk engine.

    Integrates:
    1. Vasicek ESG for short-rate scenario simulation and stochastic discounting.
    2. Mortality table decrement rollout.
    3. Dynamic interest-rate-sensitive policyholder lapses.
    4. Expense cash flows (acquisition, maintenance, per-policy).
    5. Quantitative tail risk metrics (VaR & CVaR).

    Attributes:
        table: Mortality table.
        esg: Economic Scenario Generator instance.
        expense: Optional expense loading assumptions.
        dynamic_lapse: Optional dynamic lapse model (S-curve).
        base_lapse: Optional static baseline lapse assumptions.
    """

    __slots__ = ("table", "esg", "expense", "dynamic_lapse", "base_lapse")

    def __init__(
        self,
        table: MortalityTable,
        esg: VasicekESG,
        expense: Optional[ExpenseAssumption] = None,
        dynamic_lapse: Optional[DynamicLapseModel] = None,
        base_lapse: Optional[LapseAssumption] = None,
    ) -> None:
        """Initialize stochastic valuation engine.

        Args:
            table: Mortality table instance.
            esg: VasicekESG economic scenario generator.
            expense: Optional expense loading assumptions.
            dynamic_lapse: Optional dynamic interest-rate-sensitive lapse model.
            base_lapse: Optional static baseline lapse assumptions.
        """
        self.table = table
        self.esg = esg
        self.expense = expense or ExpenseAssumption()
        self.dynamic_lapse = dynamic_lapse
        self.base_lapse = base_lapse

    def run_simulation(
        self,
        contract: PolicyContract,
        gross_premium: float,
        n_scenarios: int = 2000,
        seed: Optional[int] = None,
        surrender_values: Optional[np.ndarray] = None,
        dt: float = 1.0,
        compounding: str = "continuous",
    ) -> RiskMetricsResult:
        """Run path-dependent Monte Carlo simulation of policy liabilities.

        Simulates n_scenarios paths over the contract coverage term, computes
        the present value of net liabilities along each path, and returns
        aggregated risk metrics.

        Args:
            contract: Policy contract specification.
            gross_premium: Annual gross premium paid by policyholder.
            n_scenarios: Number of Monte Carlo scenario paths (default 2000).
            seed: Optional random seed for reproducible runs.
            surrender_values: Optional 1D array of cash surrender values by duration.
            dt: Time step size in years (default 1.0 for annual).
            compounding: Discount compounding model ('continuous' or 'discrete').

        Returns:
            RiskMetricsResult containing distribution statistics and scenario array.
        """
        if n_scenarios <= 0:
            raise ValueError(f"n_scenarios must be positive. Got {n_scenarios}.")

        x = contract.issue_age
        face = contract.sum_assured
        ptype = contract.product_type

        # Projection horizon (years)
        n = contract.term if contract.term is not None else (self.table.omega - x)
        h = contract.effective_premium_term if contract.effective_premium_term is not None else n

        # ────────────────────────────────────────────────────────
        # 1. Simulate Economic Scenarios & Discount Factors
        # ────────────────────────────────────────────────────────
        # Shape: (n_scenarios, n + 1)
        short_rates = self.esg.simulate_paths(
            n_scenarios=n_scenarios,
            n_years=n,
            dt=dt,
            method="exact",
            seed=seed,
        )

        # Stochastic discount factor matrix: (n_scenarios, n + 1)
        discount_matrix = self.esg.compute_discount_factors(
            short_rates, dt=dt, compounding=compounding
        )
        disc_boy = discount_matrix[:, :n]      # Beginning of year (t=0..n-1)
        disc_eoy = discount_matrix[:, 1:n + 1]  # End of year (t=1..n)

        # ────────────────────────────────────────────────────────
        # 2. Dynamic / Static Decrements (Lapse & Mortality)
        # ────────────────────────────────────────────────────────
        years = np.arange(n, dtype=np.int64)

        # Independent lapse rates matrix: (n_scenarios, n)
        if self.dynamic_lapse is not None:
            market_rates_during = short_rates[:, :n]
            if self.base_lapse is not None:
                base_vec = np.array([self.base_lapse.get_rate(int(t) + 1) for t in years])
                w_indep = self.dynamic_lapse.compute_lapse_rates(market_rates_during, base_vec)
            else:
                w_indep = self.dynamic_lapse.compute_lapse_rates(market_rates_during)
        elif self.base_lapse is not None:
            base_vec = np.array([self.base_lapse.get_rate(int(t) + 1) for t in years])
            w_indep = np.broadcast_to(base_vec, (n_scenarios, n))
        else:
            w_indep = np.zeros((n_scenarios, n), dtype=np.float64)

        # Independent mortality rates: (n,) broadcast to (n_scenarios, n)
        x_idx = x - self.table.min_age
        q_indep_vec = self.table.qx[x_idx: x_idx + n]
        q_indep = np.broadcast_to(q_indep_vec, (n_scenarios, n))

        # Dependent rates via UDD double-decrement formulation
        q_dep = q_indep * (1.0 - w_indep / 2.0)
        w_dep = w_indep * (1.0 - q_indep / 2.0)
        p_survival_step = np.clip(1.0 - q_dep - w_dep, 0.0, 1.0)

        # In-force cohort matrix rollout: (n_scenarios, n)
        # inforce[:, 0] = 1.0; inforce[:, t] = inforce[:, t-1] * p_survival_step[:, t-1]
        inforce = np.empty((n_scenarios, n), dtype=np.float64)
        inforce[:, 0] = 1.0
        if n > 1:
            inforce[:, 1:] = np.cumprod(p_survival_step[:, :-1], axis=1)

        # ────────────────────────────────────────────────────────
        # 3. Cash Flow Components (Vectorized across scenarios)
        # ────────────────────────────────────────────────────────

        # Premium income (BOY)
        prem_mask = (years < h).astype(np.float64)
        prem_income = gross_premium * inforce * prem_mask  # (n_scenarios, n)

        # Death claims (EOY)
        if ptype == ProductType.PURE_ENDOWMENT:
            death_claims = np.zeros((n_scenarios, n), dtype=np.float64)
        else:
            death_claims = face * inforce * q_dep  # (n_scenarios, n)

        # Surrender / Lapse payouts (EOY)
        if surrender_values is not None:
            cv = np.asarray(surrender_values, dtype=np.float64)
            if len(cv) < n:
                cv = np.pad(cv, (0, n - len(cv)), constant_values=0.0)
            cv_mat = np.broadcast_to(cv[:n], (n_scenarios, n))
            lapse_payouts = cv_mat * inforce * w_dep
        else:
            lapse_payouts = np.zeros((n_scenarios, n), dtype=np.float64)

        # Maturity benefit (EOY of last year)
        if ptype in (ProductType.ENDOWMENT, ProductType.PURE_ENDOWMENT):
            # Survivors at end of term: inforce at year n-1 * survival in year n-1
            survivors_at_mat = inforce[:, -1] * p_survival_step[:, -1]
            maturity_payout = face * survivors_at_mat  # (n_scenarios,)
        else:
            maturity_payout = np.zeros(n_scenarios, dtype=np.float64)

        # Expenses (BOY)
        exp = self.expense
        pct_rate = np.where(
            years == 0,
            exp.percent_of_premium_first,
            exp.percent_of_premium_renewal,
        )
        pct_exp = prem_income * pct_rate

        per_pol_rate = np.where(
            years == 0,
            exp.per_policy_first,
            exp.per_policy_renewal,
        )
        per_pol_exp = inforce * per_pol_rate
        total_exp = pct_exp + per_pol_exp

        # ────────────────────────────────────────────────────────
        # 4. Stochastic Discounted Cash Flows & Scenario BEL
        # ────────────────────────────────────────────────────────

        pv_prem = np.sum(prem_income * disc_boy, axis=1)
        pv_death = np.sum(death_claims * disc_eoy, axis=1)
        pv_lapse = np.sum(lapse_payouts * disc_eoy, axis=1)
        pv_exp = np.sum(total_exp * disc_boy, axis=1)
        pv_maturity = maturity_payout * disc_eoy[:, -1]

        # Scenario Best Estimate Liability = PV(outgo) - PV(income)
        scenario_bel = pv_death + pv_lapse + pv_maturity + pv_exp - pv_prem

        # ────────────────────────────────────────────────────────
        # 5. Risk Statistics & Quantiles
        # ────────────────────────────────────────────────────────

        mean_bel = float(np.mean(scenario_bel))
        std_bel = float(np.std(scenario_bel, ddof=1)) if n_scenarios > 1 else 0.0
        min_bel = float(np.min(scenario_bel))
        max_bel = float(np.max(scenario_bel))

        # Quantile calculations
        var_95 = float(np.percentile(scenario_bel, 95.0))
        var_99 = float(np.percentile(scenario_bel, 99.0))

        # Conditional Value at Risk (Expected Shortfall / CTE)
        tail_95 = scenario_bel[scenario_bel >= var_95]
        cvar_95 = float(np.mean(tail_95)) if len(tail_95) > 0 else var_95

        tail_99 = scenario_bel[scenario_bel >= var_99]
        cvar_99 = float(np.mean(tail_99)) if len(tail_99) > 0 else var_99

        percentiles_dict = {
            "50%": float(np.percentile(scenario_bel, 50.0)),
            "75%": float(np.percentile(scenario_bel, 75.0)),
            "90%": float(np.percentile(scenario_bel, 90.0)),
            "95%": var_95,
            "99%": var_99,
            "99.5%": float(np.percentile(scenario_bel, 99.5)),
        }

        return RiskMetricsResult(
            mean_bel=mean_bel,
            std_bel=std_bel,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            min_bel=min_bel,
            max_bel=max_bel,
            percentiles=percentiles_dict,
            scenario_bel=scenario_bel,
        )

    def __repr__(self) -> str:
        return (
            f"StochasticValuationEngine(table='{self.table.name}', "
            f"esg={self.esg!r}, dynamic_lapse={self.dynamic_lapse is not None})"
        )
