import pytest
import numpy as np

def test_deterministic_bel_whole_life(deterministic_whole_life):
    # BEL = \sum v^{t+1} * t_p_x * q_{x+t}
    # Compare against WholeLife.calculate_epv() with rtol=1e-10
    
    manual_bel = 0.0
    age = deterministic_whole_life.age
    max_age = deterministic_whole_life.mortality.get_max_age()
    v = 1 / (1 + deterministic_whole_life.discount_rate)
    
    for t in range(max_age - age):
        tpx = deterministic_whole_life.mortality.survival_prob(age=age, t=t)
        qx_t = deterministic_whole_life.mortality.death_prob(age=age + t)
        manual_bel += (v**(t + 1)) * tpx * qx_t
        
    engine_epv = deterministic_whole_life.calculate_epv()
    assert np.isclose(engine_epv, manual_bel, rtol=1e-10)
