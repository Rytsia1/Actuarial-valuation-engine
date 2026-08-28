import pytest
import numpy as np
from actuary_engine.stochastic.insurance import StochasticWholeLife

def test_quantile_consistency(deterministic_whole_life):
    stochastic_life = StochasticWholeLife(
        age=deterministic_whole_life.age,
        mortality=deterministic_whole_life.mortality,
        discount_rate=deterministic_whole_life.discount_rate
    )
    
    # Capture the full array of present values
    pv_array = stochastic_life.simulate_present_values(num_paths=10000, seed=42)
    
    # Manually sort the array and compute the 95th percentile
    manual_quantile = np.percentile(np.sort(pv_array), 95)
    
    # Compare against the engine's .calculate_quantile(0.95) method
    engine_quantile = stochastic_life.calculate_quantile(0.95, num_paths=10000, seed=42)
    assert np.isclose(engine_quantile, manual_quantile, rtol=1e-12)
