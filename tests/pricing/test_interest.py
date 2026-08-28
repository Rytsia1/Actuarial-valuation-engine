import pytest
import numpy as np
from actuary_engine.curves.discount import DiscountCurve

def test_discount_factor():
    rate = 0.05
    expected_v = 1 / (1 + rate)
    
    # Instantiate the engine's discount curve
    engine_factor = DiscountCurve(rate=rate).get_discount_factor(time=1)
    
    assert np.isclose(engine_factor, expected_v, rtol=1e-12)

def test_compound_interest():
    rate = 0.05
    n = 10
    pv = 1000
    expected_fv = pv * (1 + rate)**n
    
    engine_curve = DiscountCurve(rate=rate)
    engine_fv = engine_curve.compound(pv=pv, time=n)
    
    assert np.isclose(engine_fv, expected_fv, rtol=1e-12)
