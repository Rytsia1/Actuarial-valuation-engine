import cProfile
import pstats
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from actuary_engine.stochastic.monte_carlo import StochasticValuationEngine
from actuary_engine.stochastic.esg import VasicekESG, VasicekParams
from actuary_engine.models.contracts import PolicyContract, ProductType
from actuary_engine.tables.mortality_table import MortalityTable

def run_simulation():
    # Hardcoded parameters matching the benchmark
    discount_rate = 0.05
    num_paths = 10000
    random_seed = 42
    
    # Load the bundled SOA ILT
    mortality_table = MortalityTable.from_soa_ilt()
    
    params = VasicekParams(
        r0=discount_rate,
        kappa=0.001, 
        theta=discount_rate,
        sigma=0.0
    )
    esg = VasicekESG(params=params)
    
    contract = PolicyContract(
        issue_age=30,
        product_type=ProductType.WHOLE_LIFE,
        sum_assured=100000.0
    )
    
    engine = StochasticValuationEngine(table=mortality_table, esg=esg)
    
    print(f"Running Monte Carlo Simulation with {num_paths} paths...")
    # This is the core method we are profiling to identify hotspots
    engine.run_simulation(contract, 0.0, n_scenarios=num_paths, seed=random_seed)

def main():
    prof_file = "profile_output.prof"
    
    print("Starting cProfile...")
    cProfile.run('run_simulation()', prof_file)
    print("Profiling complete.\n")
    
    print("--- Top 10 Hotspots (Sorted by Cumulative Time) ---")
    p = pstats.Stats(prof_file)
    p.strip_dirs().sort_stats('cumtime').print_stats(10)
    
    print("\n--- Initial Profiling Analysis ---")
    print("Analyze the output above. If the hotspot is in the random number generation, ")
    print("the discounting loop, or the mortality lookup, local optimizations apply.")
    print("Suggest an actionable optimization for the top hotspot:")
    print("  - Hotspot in pure Python loops? Suggest vectorizing with NumPy broadcasting.")
    print("  - Hotspot in mortality table lookup? Suggest pre-caching age arrays.")
    print("  - Hotspot in discounting? Suggest using np.einsum for geometric series.")

if __name__ == "__main__":
    main()
