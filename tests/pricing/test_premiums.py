import pytest
import numpy as np

def test_net_premium_whole_life(deterministic_whole_life):
    # P = A_x / a_ddot_x
    # Use the deterministic EPV from WholeLife and a manual AnnuityDue calculation
    epv = deterministic_whole_life.calculate_epv()
    annuity_due = deterministic_whole_life.calculate_annuity_due()
    expected_premium = epv / annuity_due
    
    engine_premium = deterministic_whole_life.calculate_net_premium()
    assert np.isclose(engine_premium, expected_premium, rtol=1e-12)
