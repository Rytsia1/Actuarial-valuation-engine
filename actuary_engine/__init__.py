"""
Actuary Engine — Modular Actuarial Valuation & Risk Simulation Engine.

A production-ready Python engine for life insurance liability modeling,
prospective reserves, and stochastic risk simulation.
"""

__version__ = "0.1.0"

from actuary_engine.tables.mortality_table import MortalityTable
from actuary_engine.tables.commutation import CommutationFunctions
from actuary_engine.pricing.insurance import InsurancePricer
from actuary_engine.pricing.annuity import AnnuityPricer
from actuary_engine.pricing.premium import LevelPremiumCalculator, PremiumResult
from actuary_engine.curves.survival import SurvivalCurve
from actuary_engine.projections.cash_flow import CashFlowProjector
from actuary_engine.models.assumptions import (
    InterestAssumption,
    MortalityAssumption,
    ValuationAssumptions,
)
from actuary_engine.models.contracts import PolicyContract, ProductType

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
    "ValuationAssumptions",
    "PolicyContract",
    "ProductType",
]
