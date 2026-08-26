# Actuarial Valuation & Risk Engine

A modular, production-ready Python engine for life insurance liability modeling, prospective & retrospective reserves, and stochastic risk simulation.

## Features

- **Life Table Parsing** — Load SOA Illustrative Life Table or custom CSV mortality tables (`qx`, `lx`, `dx`, `tpx`, `tqx`)
- **Commutation Functions** — Fully vectorized `Dx`, `Nx`, `Cx`, `Mx` computation via NumPy reverse cumsum
- **Insurance Pricing** — Net Single Premiums for term, whole life, endowment, and pure endowment
- **Annuity Pricing** — Whole-life and temporary annuities, due and immediate variants
- **Level Premiums** — Annual net premiums via the equivalence principle, with limited-pay support
- **Survival Curves** — Vectorized `tpx`/`tqx` arrays, curtate and complete life expectancy
- **Cash Flow Projections** — Deterministic expected cash flows with equivalence validation
- **Policy Reserves (_t V)** — Prospective and retrospective net premium reserves with automated `_t V_pro ≡ _t V_retro` validation and Fackler recurrence
- **Gross Premium Valuation (GPV / BEL)** — Multi-decrement cash flows with acquisition/maintenance expenses (α, β, γ) and UDD-based lapse/surrender behavior

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
├── valuation/           # Policy reserves & liability engines
│   ├── reserves.py      # ReserveCalculator (prospective, retrospective, recurrence)
│   └── gpv.py           # GrossPremiumValuation (BEL, expenses, multi-decrement)
├── curves/              # Survival & discount curves
│   └── survival.py      # SurvivalCurve
├── projections/         # Cash flow engines
│   └── cash_flow.py     # CashFlowProjector
└── data/                # Bundled reference data
    └── soa_ilt.csv      # SOA Illustrative Life Table
```

## Quick Start

### Installation & Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-repo/actuarial-valuation-engine.git
cd actuarial-valuation-engine

# Create virtual environment and install
python -m venv .venv
```

Activate the virtual environment in your terminal:

**Windows PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

**Windows Command Prompt:**
```cmd
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

Then install the package with development dependencies:
```bash
pip install -e ".[dev]"
```

---

### Run the Demo

Once `.venv` is activated:
```bash
python examples/quickstart.py
```

Or run directly with the virtual environment binary without activating:
```powershell
.\.venv\Scripts\python.exe examples/quickstart.py
```

---

### Run Tests

Once `.venv` is activated:
```bash
pytest tests/ -v --cov=actuary_engine
```

Or run directly with the virtual environment pytest:
```powershell
.\.venv\Scripts\pytest.exe tests/ -v --cov=actuary_engine
```

---

### Python API Usage

```python
from actuary_engine import (
    MortalityTable,
    CommutationFunctions,
    LevelPremiumCalculator,
    ReserveCalculator,
    InterestAssumption,
    PolicyContract,
    ProductType,
)

# 1. Load mortality table & build commutation at 5% interest
table = MortalityTable.from_soa_ilt()
interest = InterestAssumption(annual_rate=0.05)
comm = CommutationFunctions(table, interest)

# 2. Price a 20-year endowment for age 30
calc = LevelPremiumCalculator(comm)
result = calc.annual_premium_endowment(x=30, n=20, face=1_000_000)

print(f"Annual Premium: ${result.annual_premium:,.2f}")
print(f"NSP:            ${result.nsp:,.2f}")
print(f"Annuity Factor:  {result.annuity_factor:.4f}")

# 3. Compute policy reserve trajectory (_t V)
contract = PolicyContract(
    product_type=ProductType.ENDOWMENT,
    issue_age=30,
    term=20,
    sum_assured=1_000_000,
)
res_calc = ReserveCalculator(comm)
res_df = res_calc.reserve_profile(contract, result.annual_premium, method="both")
print(res_df.head())
```

## Mathematical Foundation

### Commutation Functions

| Symbol | Formula | Description |
|--------|---------|-------------|
| $D_x$ | $v^x \cdot l_x$ | Discounted survivors |
| $C_x$ | $v^{x+1} \cdot d_x$ | Discounted deaths |
| $N_x$ | $\sum_{k \ge x} D_k$ | Cumulative $D_x$ |
| $M_x$ | $\sum_{k \ge x} C_k$ | Cumulative $C_x$ |

### Annual Level Premium (Equivalence Principle)

$$P = \frac{\text{NSP}}{\ddot{a}_{x:\overline{n}|}}$$

### Policy Reserves (_t V)

- **Prospective:** ${}_t V = \text{APV}(\text{Future Benefits}) - \text{APV}(\text{Future Premiums})$
- **Retrospective:** ${}_t V = [\text{APV}(\text{Past Premiums}) - \text{APV}(\text{Past Benefits})] \times \frac{D_x}{D_{x+t}}$
- **Invariants:** ${}_0 V = 0$, ${}_n V = 0$ (Term), ${}_n V = S$ (Endowment), ${}_t V_{\text{pro}} \equiv {}_t V_{\text{retro}}$

## Roadmap

- [x] **Level 1–2:** Life tables, commutation functions, pricing, annual level premiums
- [x] **Level 3:** Prospective/retrospective reserves, Fackler recurrence, GPV/BEL, expense loading, lapse modeling
- [ ] **Level 4:** ESG (Vasicek/Hull-White), stochastic mortality (Lee-Carter), Monte Carlo simulation
- [ ] **API Layer:** FastAPI endpoints for all calculation & valuation pipelines
- [ ] **Frontend:** Vue 3 + Plotly dashboards (interactive reserve profiles, sensitivity tornadoes, fan charts)

## License

MIT
