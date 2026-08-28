import pytest
import numpy as np

def test_prospective_reserve_whole_life(deterministic_whole_life):
    # _t V = A_{x+t} - P * a_ddot_{x+t}
    # Retrieve the net premium P from the model, compute the expected reserve at t=10
    
    t = 10
    age = deterministic_whole_life.age
    p = deterministic_whole_life.calculate_net_premium()
    
    ax_t = deterministic_whole_life.calculate_epv(age_offset=t)
    annuity_due_x_t = deterministic_whole_life.calculate_annuity_due(age_offset=t)
    
    expected_reserve = ax_t - p * annuity_due_x_t
    
    engine_reserve = deterministic_whole_life.calculate_reserve(term=t)
    assert np.isclose(engine_reserve, expected_reserve, rtol=1e-10)
