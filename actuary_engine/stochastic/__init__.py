"""
Stochastic valuation, Economic Scenario Generator (ESG), and Mortality Forecasting package.

Provides modules for:
- Vasicek Economic Scenario Generator (short-rate paths and discount factors)
- Dynamic policyholder lapse behavior (S-curve interest rate sensitivity)
- Monte Carlo Stochastic Valuation Engine (path-dependent liability rollout, VaR, CVaR)
- Lee-Carter Stochastic Mortality Improvement Model (SVD decomposition & RWD forecasting)
"""

from actuary_engine.stochastic.dynamic_lapse import DynamicLapseModel, DynamicLapseParams
from actuary_engine.stochastic.esg import VasicekESG, VasicekParams
from actuary_engine.stochastic.lee_carter import (
    LeeCarterFitResult,
    LeeCarterForecastSummary,
    LeeCarterModel,
)
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
    "LeeCarterModel",
    "LeeCarterFitResult",
    "LeeCarterForecastSummary",
]
