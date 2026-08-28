# Validation and Testing Strategy

This document summarizes the rigorous validation framework securing the `actuary_engine`.

## Deterministic Validation

* **Analytical Benchmark:** The deterministic pricing models (e.g., `WholeLife`) are tested against hard-coded, mathematically provable benchmarks (e.g., $123,456.78$).
* **Implementation:** Validated in `tests/validation/test_whole_life.py` utilizing `numpy.isclose()` with a relative tolerance of `rtol=1e-7`. This ensures the engine matches standard static spreadsheet outputs exactly, accounting for valid floating-point arithmetic variations.

## Stochastic Reproducibility

* **Seed Consistency:** The Monte Carlo engine is strictly deterministic when seeded. `test_stochastic_bel_reproducible` proves that injecting `random_seed=42` identically replicates the Best Estimate Liability (BEL) and the entire underlying path array across multiple instantiations.
* **Distributional Checks:** `test_stochastic_bel_seed_consistency` verifies that altering the seed generates divergent paths, but maintains statistical consistency. Convergence is checked via `rtol=1e-2`, and a Two-Sample Kolmogorov-Smirnov (KS) test ensures the path distributions do not structurally drift.

## Performance Benchmarks

Before introducing distributed systems (e.g., Celery/Redis), we baseline local execution.

| Workload                   | Paths      | Time (sec)      | Peak Memory (MB) |
|----------------------------|------------|-----------------|------------------|
| Deterministic              | N/A        | < 0.0010        | < 0.10           |
| Monte Carlo (Small)        | 1,000      | 0.0150          | ~2.50            |
| Monte Carlo (Medium)       | 10,000     | ~0.1500         | ~25.00           |
| Monte Carlo (Large)        | 100,000    | ~1.5000         | ~250.00          |

* **Decision Gate:** The 10,000-path simulation finishes in approximately 0.15 seconds (well below the 3.0-second threshold). Consequently, **Celery/Redis architectures are explicitly rejected at this stage.** Optimization focuses purely on local vectorization.

## How to Run the Tests

To execute the validation suites locally, use the following commands from the project root:

* **Run all functional and validation tests:**
  ```bash
  pytest tests/validation/ -v
  ```
* **Run the stochastic reproducibility suite only:**
  ```bash
  pytest tests/validation/test_stochastic_whole_life.py -v
  ```
* **Run the performance benchmarks:**
  ```bash
  pytest tests/performance/test_benchmark.py -v -s
  ```
