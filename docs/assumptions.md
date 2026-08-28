# Assumptions Data Dictionary

This document details the static and default assumptions embedded in the system. It serves as a single source of truth for regulatory audits and model governance. 

*Note: Code implementation always supersedes actuarial theory if a divergence exists.*

## Economic Assumptions

* **Discount Rate:** The codebase defaults to a **fixed flat rate of 5.0%** (`0.05`) for deterministic pricing and non-stochastic EPV discounting.
    * *Configuration:* Passed directly via the `discount_rate` argument in model constructors (e.g., `WholeLife(..., discount_rate=0.05)`).
    
## Demographic Assumptions

* **Mortality Table:** 
    * *Source Table:* SOA 2001 Initial Level Term (ILT).
    * *File Reference:* `soa_ilt.csv`.
    * *Code Mapping:* The `MortalityTable` class parses this file, mapping the primary age column and the associated $q_x$ mortality rates for calculations.

## Policy Specifications

* **Default Policyholder Parameters:**
    * *Age:* Passed explicitly (standard tests use age `30`).
    * *Policy Term:* Implicit to ultimate age for Whole Life; passed explicitly for Term.
    * *Sum Assured:* Assumed unit (1.0) payout at the end of the year of death unless explicitly scaled.
    * *Configuration:* These are *not* hardcoded in the model internals but must be provided as arguments upon instantiation.

## Behavioral Assumptions

* **Lapse Rates:** 
    * Baseline deterministic pricing assumes a 0% lapse rate unless explicitly modeled via `LapseTable`.
    * Stochastic models utilize dynamic sensitivity bounds (min 1%, max 10%) when the dynamic lapse module is engaged.

## Expense Assumptions

* **Expenses:** Currently, the core engine models **gross/net pure premiums only**. Initial, maintenance, and claim expenses are assumed to be $0.00$ unless custom cashflow modifiers are injected into the pipeline.
