"""
Stochastic valuation and Economic Scenario Generator (ESG) package.

Provides modules for:
- Vasicek Economic Scenario Generator (short-rate paths and discount factors)
- Dynamic policyholder lapse behavior (S-curve interest rate sensitivity)
- Monte Carlo Stochastic Valuation Engine (path-dependent liability rollout, VaR, CVaR)
"""

from actuary_engine.stochastic.esg import VasicekESG, VasicekParams
from actuary_engine.stochastic.dynamic_lapse import DynamicLapseModel, DynamicLapseParams
from actuary_engine.stochastic.monte_carlo import (
    RiskMetricsResult,
    StochasticValuationEngine,
)

__all__ = [
    "VasicekParams",
    "VasicekESG",
    "DynamicLapseParams",
    "DynamicLapseModel",
    "RiskMetricsResult",
    "StochasticValuationEngine",
]
