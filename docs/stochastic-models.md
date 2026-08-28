# Stochastic Models

This document outlines the stochastic models built into the `actuary_engine`, their discretizations, and their underlying assumptions.

## Vasicek (Interest Rate)

The Vasicek model simulates the evolution of interest rates over time.

* **Stochastic Differential Equation (SDE):** $dr_t = \kappa(\theta - r_t)dt + \sigma dW_t$
* **Discretization:** Euler-Maruyama method.
* **Parameters:** Currently handled as configurable inputs to the SDE engine. Default fallbacks assume:
    * Reversion speed (`kappa`): `0.1`
    * Long-term mean (`theta`): `0.05`
    * Volatility (`sigma`): `0.015`

## Lee-Carter (Mortality)

The Lee-Carter model projects future mortality improvements.

* **Core Equation:** $\log(m_{x,t}) = a_x + b_x \cdot k_t$
* **Constraints:** To ensure uniqueness, the model applies $\sum b_x = 1$ and $\sum k_t = 0$ during historical calibration.
* **Projection:** The time index $k_t$ is projected using a Random Walk with Drift (RWD). The drift is calibrated externally from historical data or provided as a static configuration parameter.

## Dynamic Lapse

Lapse assumptions dynamically adjust policyholder behavior based on economic environments.

* **Model Structure:** The lapse model modifies a baseline static lapse table by applying a multiplier derived from the interest rate differential (e.g., market rate vs. credited rate).
* **Assumptions:** 
    * Base lapse assumptions are derived from standard pricing tables.
    * Ceilings and floors are applied to prevent unrealistic shocks (e.g., maximum lapse rate capped at 10%, minimum at 1%).

## Monte Carlo (Path Generation)

The Monte Carlo engine drives the stochastic BEL calculations.

* **Path Generation:** Paths are generated using vectorized NumPy operations where possible. Inner loops iterate over durations, leveraging broadcasted arrays across `num_paths` to minimize pure Python loop overhead.
* **Variance Reduction:** Currently, **no** variance reduction techniques (e.g., antithetic variates or control variates) are implemented. The engine relies on raw brute-force sampling (e.g., 10,000 paths).
* **Aggregation:** The engine averages the terminal discounted present values of all simulated paths to compute the final Best Estimate Liability (BEL).
