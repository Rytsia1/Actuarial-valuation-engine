import pytest
import numpy as np
from scipy.stats import ks_2samp

from actuary_engine.stochastic.monte_carlo import StochasticValuationEngine
from actuary_engine.stochastic.esg import VasicekESG, VasicekParams
from actuary_engine.models.contracts import PolicyContract, ProductType
from actuary_engine.tables.mortality_table import MortalityTable
from tests.conftest import DISCOUNT_RATE

def create_deterministic_esg():
    # kappa must be > 0, so we use a small value.
    params = VasicekParams(
        r0=DISCOUNT_RATE,
        kappa=0.001, 
        theta=DISCOUNT_RATE,
        sigma=0.0
    )
    return VasicekESG(params=params)

def test_stochastic_bel_reproducible(static_mortality_table, stochastic_config):
    """
    Test Case A: Deterministic Reproducibility (Seed Consistency)
    """
    num_paths = stochastic_config["NUM_PATHS"]
    random_seed = stochastic_config["RANDOM_SEED"]
    
    esg = create_deterministic_esg()
    
    contract = PolicyContract(
        issue_age=30,
        product_type=ProductType.WHOLE_LIFE,
        sum_assured=100000.0
    )
    
    # Run 1
    engine_1 = StochasticValuationEngine(table=static_mortality_table, esg=esg)
    result_1 = engine_1.run_simulation(
        contract=contract,
        gross_premium=0.0,
        n_scenarios=num_paths,
        seed=random_seed
    )
    bel_run_1 = result_1.mean_bel
    paths_run_1 = result_1.scenario_bel
    
    # Run 2
    engine_2 = StochasticValuationEngine(table=static_mortality_table, esg=esg)
    result_2 = engine_2.run_simulation(
        contract=contract,
        gross_premium=0.0,
        n_scenarios=num_paths,
        seed=random_seed
    )
    bel_run_2 = result_2.mean_bel
    paths_run_2 = result_2.scenario_bel
    
    # Assert bitwise-identical/strictly equal results
    assert np.isclose(bel_run_1, bel_run_2, rtol=0, atol=0)
    assert np.array_equal(paths_run_1, paths_run_2)

def test_stochastic_bel_seed_consistency(static_mortality_table, stochastic_config):
    """
    Test Case B: Seed Variation and Distributional Consistency
    """
    num_paths = stochastic_config["NUM_PATHS"]
    seed_1 = stochastic_config["RANDOM_SEED"]
    seed_2 = 123
    
    # We want some variation here to ensure RNG paths differ.
    params = VasicekParams(
        r0=DISCOUNT_RATE,
        kappa=0.1, 
        theta=DISCOUNT_RATE,
        sigma=0.015
    )
    esg = VasicekESG(params=params)
    
    contract = PolicyContract(
        issue_age=30,
        product_type=ProductType.WHOLE_LIFE,
        sum_assured=100000.0
    )
    
    engine = StochasticValuationEngine(table=static_mortality_table, esg=esg)
    
    # Run 1
    result_1 = engine.run_simulation(contract, 0.0, n_scenarios=num_paths, seed=seed_1)
    bel_42 = result_1.mean_bel
    paths_42 = result_1.scenario_bel
    
    # Run 2
    result_2 = engine.run_simulation(contract, 0.0, n_scenarios=num_paths, seed=seed_2)
    bel_123 = result_2.mean_bel
    paths_123 = result_2.scenario_bel
    
    assert np.isclose(bel_42, bel_123, rtol=2e-2)
    assert not np.array_equal(paths_42, paths_123)
    
    ks_statistic, p_value = ks_2samp(paths_42, paths_123)
    assert p_value > 0.01
