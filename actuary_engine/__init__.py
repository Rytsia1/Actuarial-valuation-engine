"""
Actuary Engine — Modular Actuarial Valuation & Risk Simulation Engine.

A production-ready Python engine for life insurance liability modeling,
prospective reserves, and stochastic risk simulation.
"""

__version__ = "0.3.0"

from actuary_engine.curves.survival import SurvivalCurve
from actuary_engine.models.assumptions import (
    ExpenseAssumption,
    InterestAssumption,
    LapseAssumption,
    MortalityAssumption,
    ValuationAssumptions,
)
from actuary_engine.models.contracts import PolicyContract, ProductType
from actuary_engine.pricing.annuity import AnnuityPricer
from actuary_engine.pricing.insurance import InsurancePricer
from actuary_engine.pricing.premium import LevelPremiumCalculator, PremiumResult
from actuary_engine.projections.cash_flow import CashFlowProjector
from actuary_engine.stochastic.dynamic_lapse import DynamicLapseModel, DynamicLapseParams
from actuary_engine.stochastic.esg import VasicekESG, VasicekParams
from actuary_engine.stochastic.monte_carlo import (
    RiskMetricsResult,
    StochasticValuationEngine,
)
from actuary_engine.tables.commutation import CommutationFunctions
from actuary_engine.tables.mortality_table import MortalityTable
from actuary_engine.valuation.gpv import GrossPremiumValuation
from actuary_engine.valuation.portfolio import PortfolioSummary, PortfolioValuationEngine
from actuary_engine.valuation.reserves import ReserveCalculator

__all__ = [
    "MortalityTable",
    "CommutationFunctions",
    "InsurancePricer",
    "AnnuityPricer",
    "LevelPremiumCalculator",
    "PremiumResult",
    "SurvivalCurve",
    "CashFlowProjector",
    "InterestAssumption",
    "MortalityAssumption",
    "ExpenseAssumption",
    "LapseAssumption",
    "ValuationAssumptions",
    "PolicyContract",
    "ProductType",
    "ReserveCalculator",
    "GrossPremiumValuation",
    "PortfolioValuationEngine",
    "PortfolioSummary",
    "VasicekParams",
    "VasicekESG",
    "DynamicLapseParams",
    "DynamicLapseModel",
    "RiskMetricsResult",
    "StochasticValuationEngine",
]
