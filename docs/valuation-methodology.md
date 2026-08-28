# Valuation Methodology

This document outlines the end-to-end valuation pipeline implemented in the `actuary_engine` codebase. It bridges standard actuarial theory with the explicit code execution paths for both deterministic and stochastic contexts.

## The Core Pipeline

The engine evaluates policies using the following sequential flow:

1. **Premium Calculation**
2. **Cash Flow Projection**
3. **Discounting**
4. **Expected Present Value (EPV)**
5. **Best Estimate Liability (BEL)**

### 1. Premium
* **Formula:** Net Premium = EPV(Benefits) / EPV(Annuity)
* **Code Implementation:** Currently abstracted; models assume a single-premium structure or exogenous premium inputs unless using the `Annuity` class to solve for premiums.

### 2. Cash Flow Projection
* **Formula:** $CF_t = Benefit_t \times Indicator_t - Premium_t \times Indicator_t$
* **Code Implementation:** Handled within specific product models (e.g., `actuary_engine.pricing.insurance.WholeLife`).
* **Input/Output:** Takes age and term constraints. Outputs an array of temporal cash flow vectors across the policy lifetime.

### 3. Discounting
* **Formula:** $v^t = (1 + r)^{-t}$
* **Code Implementation:** Internally computed during EPV aggregations. The engine uses a flat discount rate by default.
* **Input/Output:** Takes the `discount_rate` (e.g., 0.05) and duration array. Outputs a discounting vector.

### 4. Expected Present Value (EPV) - Deterministic
* **Formula:** $A_x = \sum_{t=0}^{\omega - x - 1} v^{t+1} \cdot _tp_x \cdot q_{x+t}$
* **Variable Mapping:**
    * $v$: `discount_factor` (derived from `discount_rate`)
    * $_tp_x$: `survival_probability` (calculated from `MortalityTable`)
    * $q_{x+t}$: `mortality_rate` (queried from `MortalityTable` at age $x+t$)
* **Code Implementation:** `actuary_engine.pricing.insurance.WholeLife.calculate_epv()`
* **Input/Output:** Takes policyholder age and mortality table object. Outputs a single deterministic float representing the EPV.

### 5. Best Estimate Liability (BEL) - Stochastic
* **Formula:** $BEL = \frac{1}{N} \sum_{i=1}^{N} \sum_{t=0}^{\omega - x - 1} CF_{t}^{(i)} \cdot v_{t}^{(i)}$
* **Methodology:** The BEL is the arithmetic average of all discounted cash flows across $N$ simulated Monte Carlo paths.
* **Code Implementation:** `actuary_engine.pricing.stochastic_insurance.StochasticWholeLife.calculate_bel_simulation()`
* **Input/Output:** Takes `num_paths` (e.g., 10,000) and `random_seed`. Outputs a tuple `(mean_bel, paths_array)`.
