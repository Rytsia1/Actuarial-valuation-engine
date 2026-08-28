import time
import tracemalloc
import pytest
import numpy as np

# Assuming these modules exist in the codebase
from actuary_engine.pricing.insurance import WholeLife
from actuary_engine.pricing.stochastic_insurance import StochasticWholeLife
from actuary_engine.tables.mortality_table import MortalityTable
from tests.conftest import DISCOUNT_RATE

def benchmark_workload(model_func, *args, **kwargs):
    """Helper to run a function and measure time and peak memory."""
    tracemalloc.start()
    
    # Run multiple iterations for median
    iterations = 3
    times = []
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        model_func(*args, **kwargs)
        end_time = time.perf_counter()
        times.append(end_time - start_time)
        
    median_time = np.median(times)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    peak_mb = peak / (1024 * 1024)
    return median_time, peak_mb

def test_performance_benchmark(static_mortality_table):
    """
    Benchmark suite for actuarial calculations to justify optimization strategies 
    and evaluate the necessity of distributed computing (Celery/Redis).
    """
    mortality_table = MortalityTable(static_mortality_table)
    
    print("\n--- Actuarial Engine Performance Benchmark ---")
    print(f"{'Workload':<25} | {'Paths':<10} | {'Time (sec)':<15} | {'Peak Memory (MB)':<15}")
    print("-" * 75)
    
    results = {}
    
    # Workload 1: Deterministic (Whole Life)
    def run_deterministic():
        policy = WholeLife(age=30, discount_rate=DISCOUNT_RATE, mortality_table=mortality_table)
        policy.calculate_epv()
        
    t_det, m_det = benchmark_workload(run_deterministic)
    print(f"{'Deterministic':<25} | {'N/A':<10} | {t_det:<15.4f} | {m_det:<15.2f}")
    
    # Stochastic workloads
    path_configs = [
        ("Monte Carlo (Small)", 1000),
        ("Monte Carlo (Medium)", 10000),
        ("Monte Carlo (Large)", 100000)
    ]
    
    for name, paths in path_configs:
        def run_stochastic():
            model = StochasticWholeLife(
                age=30, discount_rate=DISCOUNT_RATE, mortality_table=mortality_table,
                num_paths=paths, random_seed=42
            )
            model.calculate_bel_simulation()
            
        t_stoch, m_stoch = benchmark_workload(run_stochastic)
        print(f"{name:<25} | {paths:<10} | {t_stoch:<15.4f} | {m_stoch:<15.2f}")
        results[paths] = t_stoch
        
    print("-" * 75)
    
    # Decision Gate Logic for Celery/Redis
    time_10k = results.get(10000, 0)
    print(f"\n[DECISION GATE]: 10,000-path simulation took {time_10k:.4f} seconds.")
    if time_10k < 3.0:
        print("RECOMMENDATION: If the 10,000-path simulation takes less than 3.0 seconds, "
              "the recommendation is to SKIP Celery/Redis and focus on local optimization.")
    else:
        print("WARNING: Time threshold exceeded. Consider profiling to identify hotspots "
              "before defaulting to Celery/Redis.")
        
    # Test does not fail based on speed, only on execution errors.
    assert True
