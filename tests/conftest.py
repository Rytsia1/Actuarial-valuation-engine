import pytest
from actuary_engine.tables.mortality_table import MortalityTable

@pytest.fixture(scope="session")
def mortality_table():
    # Use absolute path from environment variable or relative to project root
    return MortalityTable("soa_ilt.csv")

@pytest.fixture(scope="session")
def discount_rate():
    return 0.05  # Fixed for deterministic validation

@pytest.fixture(scope="session")
def deterministic_whole_life(mortality_table, discount_rate):
    from actuary_engine.pricing.insurance import WholeLife
    return WholeLife(age=30, mortality=mortality_table, discount_rate=discount_rate)
