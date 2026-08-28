import pytest
import numpy as np
from actuary_engine.pricing.annuities import AnnuityCertain

def test_annuity_certain_pv():
    n = 10
    i = 0.05
    v = 1 / (1 + i)
    # Formula for an annuity-immediate: a_{n} = (1 - v^n) / i
    expected_pv = (1 - v**n) / i
    
    annuity = AnnuityCertain(n=n, rate=i)
    assert np.isclose(annuity.present_value(), expected_pv, rtol=1e-12)
