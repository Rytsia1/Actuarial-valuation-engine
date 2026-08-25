# Actuarial Valuation & Risk Engine

A modular, production-ready Python engine for life insurance liability modeling, prospective reserves, and stochastic risk simulation.

## Features

- **Life Table Parsing** — Load SOA Illustrative Life Table or custom CSV mortality tables
- **Commutation Functions** — Fully vectorized Dx, Nx, Cx, Mx computation via NumPy reverse cumsum
- **Insurance Pricing** — Net Single Premiums for term, whole life, endowment, and pure endowment
- **Annuity Pricing** — Whole-life and temporary annuities, due and immediate variants
- **Level Premiums** — Annual net premiums via the equivalence principle, with limited-pay support
- **Survival Curves** — Vectorized tpx/tqx arrays, curtate and complete life expectancy
- **Cash Flow Projections** — Deterministic expected cash flows with equivalence validation

## Architecture

```
actuary_engine/
├── models/              # Pydantic v2 data models
│   ├── assumptions.py   # Interest, mortality, expense, lapse assumptions
│   └── contracts.py     # PolicyContract, ProductType enum
├── tables/              # Life table & commutation
│   ├── mortality_table.py
│   └── commutation.py
├── pricing/             # Insurance & annuity pricing
│   ├── insurance.py     # InsurancePricer (NSPs)
│   ├── annuity.py       # AnnuityPricer (APVs)
│   └── premium.py       # LevelPremiumCalculator
├── curves/              # Survival & discount curves
│   └── survival.py      # SurvivalCurve
├── projections/         # Cash flow engines
│   └── cash_flow.py     # CashFlowProjector
└── data/                # Bundled reference data
    └── soa_ilt.csv      # SOA Illustrative Life Table
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/actuarial-valuation-engine.git
cd actuarial-valuation-engine

# Create virtual environment and install
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -e ".[dev]"
```

### Usage

```python
from actuary_engine import (
    MortalityTable, CommutationFunctions, LevelPremiumCalculator,
    InterestAssumption, PolicyContract, ProductType,
)

# 1. Load mortality table
table = MortalityTable.from_soa_ilt()

# 2. Build commutation functions at 5% interest
interest = InterestAssumption(annual_rate=0.05)
comm = CommutationFunctions(table, interest)

# 3. Price a 20-year endowment for age 30
calc = LevelPremiumCalculator(comm)
result = calc.annual_premium_endowment(x=30, n=20, face=1_000_000)

print(f"Annual Premium: {result.annual_premium:,.2f}")
print(f"NSP:            {result.nsp:,.2f}")
print(f"Annuity Factor: {result.annuity_factor:.4f}")
```

### Run the Demo

```bash
python examples/quickstart.py
```

### Run Tests

```bash
pytest tests/ -v --cov=actuary_engine
```

## Mathematical Foundation

### Commutation Functions

| Symbol | Formula | Description |
|--------|---------|-------------|
| Dx | v^x · lx | Discounted survivors |
| Cx | v^(x+1) · dx | Discounted deaths |
| Nx | Σ Dk (k≥x) | Cumulative Dx |
| Mx | Σ Ck (k≥x) | Cumulative Cx |

### Annual Level Premium (Equivalence Principle)

```
P = NSP / äₓ:n̅|
```

Where NSP = APV(benefits) and äₓ:n̅| = APV(premium annuity-due).

## Roadmap

- [x] **Level 1–2:** Life tables, commutation functions, pricing, premiums
- [ ] **Level 3:** Prospective/retrospective reserves, expense loading, lapse modeling
- [ ] **Level 4:** ESG (Vasicek/Hull-White), stochastic mortality (Lee-Carter), Monte Carlo
- [ ] **API Layer:** FastAPI endpoints for all calculations
- [ ] **Frontend:** Vue 3 + Plotly dashboards (waterfalls, fan charts, tornado sensitivity)

## License

MIT
