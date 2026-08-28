import pytest
import numpy as np
from actuary_engine.stochastic.insurance import StochasticWholeLife

def test_bel_converges_to_deterministic(deterministic_whole_life):
    stochastic_life = StochasticWholeLife(
        age=deterministic_whole_life.age,
        mortality=deterministic_whole_life.mortality,
        discount_rate=deterministic_whole_life.discount_rate
    )
    
    stochastic_bel = stochastic_life.calculate_bel(num_paths=10000, seed=42)
    deterministic_bel = deterministic_whole_life.calculate_epv()
    
    # Assert that the stochastic BEL is within 2% (rtol=2e-2) of the deterministic value
    assert np.isclose(stochastic_bel, deterministic_bel, rtol=2e-2)
