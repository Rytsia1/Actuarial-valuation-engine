import pytest

# Constant for fixed discount rate
DISCOUNT_RATE = 0.05

@pytest.fixture(scope="session")
def static_mortality_table():
    """
    Fixture that loads a static mortality table for deterministic testing.
    This provides a consistent, mathematically provable baseline for benchmark validation.
    """
    # Returns the path to the placeholder mortality table
    # This path can be passed to the mortality table parser/loader
    file_path = "soa_ilt.csv"
    return file_path

# Stochastic simulation configuration
STOCHASTIC_CONFIG = {
    "NUM_PATHS": 10000,
    "RANDOM_SEED": 42
}

@pytest.fixture(scope="session")
def stochastic_config():
    """
    Fixture providing consistent parameters for stochastic tests.
    Ensures deterministic reproducibility across Monte Carlo simulations.
    """
    return STOCHASTIC_CONFIG
