# Actura | Actuarial Valuation & Risk Platform

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)
![Vue.js](https://img.shields.io/badge/Vue.js-3.x-4FC08D.svg?logo=vuedotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

**Actura** is an enterprise-grade actuarial platform that bridges the gap between complex risk mathematics and modern UI/UX. It provides actuaries and risk engineers with a powerful Python-based valuation engine (handling everything from Monte Carlo simulations to IFRS 17 trajectories) paired with a sleek, neo-skeuomorphic Vue 3 dashboard.

## 📸 Platform Previews

### Valuation Dashboard
<img width="1917" height="1078" alt="Screenshot 2026-08-27 220531" src="https://github.com/user-attachments/assets/e414e87c-2bba-493a-a220-7665253687b7" />
*Real-time stochastic projection, tail risk (CVaR) analysis, and comprehensive reserve profiles.*

### Contract Logic Blueprint Builder
<img width="1917" height="1078" alt="Screenshot 2026-08-27 205835" src="https://github.com/user-attachments/assets/f237c254-c12a-4854-bddb-a260ba7050df" />)
*A visual, node-based DAG (Directed Acyclic Graph) editor for designing insurance cash flow blueprints without writing code.*

---

## ✨ Key Features

- 🧩 **Visual Logic Builder:** Drag-and-drop DAG editor to map out premiums, benefits, and decrement models seamlessly.
- 📈 **Stochastic Engine:** Integrated Economic Scenario Generators (ESG) and advanced Monte Carlo simulations.
- 📊 **Risk Analytics:** Built-in calculation for BEL, VaR 95%, CVaR / CTE 95, and quantile fan-charts.
- ⚡ **High-Performance Backend:** Powered by FastAPI for rapid deterministic and stochastic valuations.
- 🐳 **Docker-Ready:** Fully containerized architecture with Nginx reverse proxy for immediate, production-like deployment.

## 🛠️ Tech Stack

**Backend (Actuarial Engine)**
- Python 3.10+
- FastAPI & Uvicorn
- NumPy, Pandas, SciPy (for quantitative modeling)

**Frontend (Dashboard & Blueprint)**
- Vue 3 (Composition API)
- Vite
- Tailwind CSS
- Vue Flow (for the node-based logic builder)
- Apache ECharts (for charting and distributions)

**Infrastructure**
- Docker & Docker Compose
- Nginx (Reverse Proxy & Static File Serving)

---

## 🚀 Quick Start (Docker)

The easiest way to get Actura up and running is via Docker. The provided configuration automatically builds the frontend, sets up the Python API, and configures Nginx routing.

### Prerequisites
- Docker and Docker Compose installed on your machine.

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/rytsia1/actuarial-valuation-engine.git
   cd actuarial-valuation-engine
   ```

2. **Build and spin up the containers**
   ```bash
   docker-compose up --build -d
   ```

3. **Access the Platform**
   - 🖥️ **UI Dashboard:** Open `http://localhost:3000` in your browser.
   - ⚙️ **API Documentation:** Interactive Swagger UI is available at `http://localhost:8000/docs`.

*(Note: API requests from the frontend are automatically routed through Nginx via `/api/` to avoid CORS issues).*

---

## 📂 Project Structure

```text
actuarial-valuation-engine/
├── actuary_engine/        # Python Backend / Valuation Engine
│   ├── api/               # FastAPI routes and schemas
│   ├── models/            # Core actuarial math models
│   ├── pricing/           # Premium and annuity calculators
│   ├── projections/       # Cash flow projection logic
│   ├── stochastic/        # Monte Carlo & ESG kernels
│   ├── tables/            # Mortality and decrement tables (e.g., SOA ILT)
│   └── valuation/         # IFRS 17, Reserves, and Sensitivities
├── frontend/              # Vue 3 Frontend
│   ├── src/               # UI components, Vue Flow, ECharts
│   ├── nginx.conf         # Nginx reverse proxy configuration
│   └── Dockerfile         # Multi-stage frontend build
├── Dockerfile             # Backend Dockerfile
└── docker-compose.yml     # Container orchestration
```

## 🧑‍💻 Manual Development Setup

If you prefer to run the project locally without Docker for development purposes:

**1. Run Backend**

```bash
# Create virtual environment and install dependencies
cd actuary_engine
pip install -r requirements.txt

# Start FastAPI server
uvicorn api.main:app --reload --port 8000
```

**2. Run Frontend**

```bash
cd frontend
npm install

# Start Vite dev server
npm run dev
```

---

*Built with precision for modern risk engineers.*
