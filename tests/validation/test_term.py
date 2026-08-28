import pytest
import numpy as np

from actuary_engine.pricing.insurance import InsurancePricer
from actuary_engine.models.assumptions import InterestAssumption
from actuary_engine.tables.commutation import CommutationFunctions
from actuary_engine.models.contracts import PolicyContract, ProductType
from tests.conftest import DISCOUNT_RATE

def test_term_insurance_one_year(static_mortality_table):
    """
    Cashflow Parity: For a pure premium, EPV(Term, n=1) == v * q_x (within 1e-12)
    """
    interest = InterestAssumption(annual_rate=DISCOUNT_RATE)
    comm = CommutationFunctions(table=static_mortality_table, interest=interest)
    pricer = InsurancePricer(commutation=comm)
    
    age = 30
    contract = PolicyContract(
        issue_age=age,
        product_type=ProductType.TERM,
        term=1,
        sum_assured=1.0
    )
    
    actual_epv = pricer.price_contract(contract)
    
    # Expected: v * q_x
    v = interest.discount_factor
    qx = static_mortality_table.get_qx(age)
    expected_epv = v * qx
    
    assert np.isclose(actual_epv, expected_epv, rtol=1e-12, atol=1e-12), (
        f"1-Year Term EPV mismatch. Expected {expected_epv}, got {actual_epv}"
    )

def test_term_insurance_boundary(static_mortality_table):
    """
    Table Boundary: EPV(Term, n=omega - age + 1) == EPV(Whole Life)
    """
    interest = InterestAssumption(annual_rate=DISCOUNT_RATE)
    comm = CommutationFunctions(table=static_mortality_table, interest=interest)
    pricer = InsurancePricer(commutation=comm)
    
    age = 30
    # max_age in the table is omega. Term up to max_age means term = max_age - age
    # The codebase restricts issue_age + term <= max_age, so term = 80 for age 30, max_age 110.
    term_n = static_mortality_table.max_age - age
    
    term_contract = PolicyContract(
        issue_age=age,
        product_type=ProductType.TERM,
        term=term_n,
        sum_assured=1.0
    )
    
    wl_contract = PolicyContract(
        issue_age=age,
        product_type=ProductType.WHOLE_LIFE,
        sum_assured=1.0
    )
    
    term_epv = pricer.price_contract(term_contract)
    wl_epv = pricer.price_contract(wl_contract)
    
    # The Term policy (n=80) misses the final year of death (age 110 to 111) which Whole Life covers.
    # We mathematically add the missing final year (C_omega / D_x) to match exactly.
    missing_final_year = comm.get_Cx(static_mortality_table.max_age) / comm.get_Dx(age)
    
    assert np.isclose(term_epv + missing_final_year, wl_epv, rtol=1e-12, atol=1e-12), (
        f"Boundary mismatch. Term EPV: {term_epv}, WL EPV: {wl_epv}"
    )

def test_term_insurance_non_negativity(static_mortality_table):
    """
    Non-Negativity: EPV for Term <= EPV for Whole Life (ensures no arbitrage in code)
    """
    interest = InterestAssumption(annual_rate=DISCOUNT_RATE)
    comm = CommutationFunctions(table=static_mortality_table, interest=interest)
    pricer = InsurancePricer(commutation=comm)
    
    age = 30
    term_contract = PolicyContract(
        issue_age=age,
        product_type=ProductType.TERM,
        term=10,
        sum_assured=1.0
    )
    wl_contract = PolicyContract(
        issue_age=age,
        product_type=ProductType.WHOLE_LIFE,
        sum_assured=1.0
    )
    
    term_epv = pricer.price_contract(term_contract)
    wl_epv = pricer.price_contract(wl_contract)
    
    assert term_epv <= wl_epv, "Term EPV should not exceed Whole Life EPV."
    assert term_epv > 0, "Term EPV must be positive."
