import cProfile
import pstats
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from actuary_engine.pricing.stochastic_insurance import StochasticWholeLife
from actuary_engine.tables.mortality_table import MortalityTable

def run_simulation():
    # Hardcoded parameters matching the benchmark
    file_path = "soa_ilt.csv"
    discount_rate = 0.05
    num_paths = 10000
    random_seed = 42
    
    # We assume the mortality table can be loaded directly from the csv path
    mortality_table = MortalityTable(file_path)
    model = StochasticWholeLife(
        age=30, 
        discount_rate=discount_rate, 
        mortality_table=mortality_table,
        num_paths=num_paths,
        random_seed=random_seed
    )
    
    print(f"Running Monte Carlo Simulation with {num_paths} paths...")
    # This is the core method we are profiling to identify hotspots
    model.calculate_bel_simulation()

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
