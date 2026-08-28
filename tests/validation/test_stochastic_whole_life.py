import pytest
import numpy as np
from scipy.stats import ks_2samp

# Assuming these modules exist in the codebase
from actuary_engine.pricing.stochastic_insurance import StochasticWholeLife
from actuary_engine.tables.mortality_table import MortalityTable
from tests.conftest import DISCOUNT_RATE

def test_stochastic_bel_reproducible(static_mortality_table, stochastic_config):
    """
    Test Case A: Deterministic Reproducibility (Seed Consistency)
    
    Prove that running the exact same simulation twice with the same seed 
    yields strictly equal Best Estimate Liability (BEL) results. 
    
    Deterministic seeding is critical for regulatory audits (e.g., IFRS 17, 
    Solvency II) to prove that results are reproducible, and for regression 
    testing to ensure code changes don't unintentionally alter expected outcomes.
    """
    num_paths = stochastic_config["NUM_PATHS"]
    random_seed = stochastic_config["RANDOM_SEED"]
    
    mortality_table = MortalityTable(static_mortality_table)
    
    # Run 1
    model_run_1 = StochasticWholeLife(
        age=30, 
        discount_rate=DISCOUNT_RATE, 
        mortality_table=mortality_table,
        num_paths=num_paths,
        random_seed=random_seed
    )
    # The interface is assumed to return a tuple of (mean_bel, array_of_paths)
    bel_run_1, paths_run_1 = model_run_1.calculate_bel_simulation()
    
    # Run 2 (re-instantiated to reset any internal state)
    model_run_2 = StochasticWholeLife(
        age=30, 
        discount_rate=DISCOUNT_RATE, 
        mortality_table=mortality_table,
        num_paths=num_paths,
        random_seed=random_seed
    )
    bel_run_2, paths_run_2 = model_run_2.calculate_bel_simulation()
    
    # Assert bitwise-identical/strictly equal results
    assert np.isclose(bel_run_1, bel_run_2, rtol=0, atol=0), "Deterministic reproducibility failed for BEL."
    assert np.array_equal(paths_run_1, paths_run_2), "Deterministic reproducibility failed for simulation paths."


def test_stochastic_bel_seed_consistency(static_mortality_table, stochastic_config):
    """
    Test Case B: Seed Variation and Distributional Consistency
    
    Prove that changing the seed produces a different path-level distribution 
    but a statistically consistent BEL (converging to the same expected value 
    within Monte Carlo standard error).
    """
    num_paths = stochastic_config["NUM_PATHS"]
    seed_1 = stochastic_config["RANDOM_SEED"]
    seed_2 = 123  # Different seed
    
    mortality_table = MortalityTable(static_mortality_table)
    
    # Run with seed 1
    model_42 = StochasticWholeLife(
        age=30, 
        discount_rate=DISCOUNT_RATE, 
        mortality_table=mortality_table,
        num_paths=num_paths,
        random_seed=seed_1
    )
    bel_42, paths_42 = model_42.calculate_bel_simulation()
    
    # Run with seed 2
    model_123 = StochasticWholeLife(
        age=30, 
        discount_rate=DISCOUNT_RATE, 
        mortality_table=mortality_table,
        num_paths=num_paths,
        random_seed=seed_2
    )
    bel_123, paths_123 = model_123.calculate_bel_simulation()
    
    # Validation A (Mean): Assert that bel_42 and bel_123 are close within Monte Carlo noise.
    # 1e-2 relative tolerance is reasonable for 10,000 paths depending on the variance.
    assert np.isclose(bel_42, bel_123, rtol=1e-2), (
        f"Statistical consistency failed. BELs differ too much: {bel_42} vs {bel_123}"
    )
    
    # Validation B (Stream Divergence): Assert underlying random streams are different.
    assert not np.array_equal(paths_42, paths_123), "Simulation paths are identical despite different seeds."
    
    # Validation C (Distribution Shape): Perform a Kolmogorov-Smirnov (KS) test.
    # High p-value indicates the two samples likely come from the same underlying distribution.
    ks_statistic, p_value = ks_2samp(paths_42, paths_123)
    
    # We expect p_value > 0.05, meaning we fail to reject the null hypothesis that
    # the two samples are drawn from the same continuous distribution.
    assert p_value > 0.05, f"KS test failed with p-value={p_value}, indicating distributional inconsistency."
