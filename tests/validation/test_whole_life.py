import pytest
import numpy as np

# Assuming these modules exist in the codebase
from actuary_engine.pricing.insurance import WholeLife
from actuary_engine.tables.mortality_table import MortalityTable
from tests.conftest import DISCOUNT_RATE

def test_whole_life_epv_analytical(static_mortality_table):
    """
    Test the Expected Present Value (EPV) of a Whole Life insurance policy 
    against a deterministic, mathematically provable benchmark.
    
    This ensures that the core analytical calculation engine is functioning 
    correctly before any stochastic elements are introduced.
    """
    # Hard-coded benchmark from specifications
    expected_epv = 123456.78
    
    # Instantiate the model components
    # Using the static_mortality_table fixture (which provides the filepath "soa_ilt.csv")
    mortality_table = MortalityTable(static_mortality_table)
    
    # Create a Whole Life policy for a person aged 30 with a fixed 5% discount rate
    policy = WholeLife(age=30, discount_rate=DISCOUNT_RATE, mortality_table=mortality_table)
    
    # Calculate the EPV from the engine
    actual_epv = policy.calculate_epv()
    
    # We use np.isclose instead of exact equality because floating-point 
    # arithmetic can introduce minor precision errors during calculation.
    # The relative tolerance (rtol) is set to 1e-7 to demand high precision.
    assert np.isclose(actual_epv, expected_epv, rtol=1e-7), (
        f"Analytical EPV mismatch. Expected: {expected_epv}, "
        f"but got: {actual_epv}. Check the core discounting or mortality logic."
    )
