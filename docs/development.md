# Development Guide

This guide explains how to set up Actura for local development without relying purely on the production Docker cluster.

## 🛠 Prerequisites
- **Python 3.10+**
- **Node.js 18+** & NPM
- **PostgreSQL 15+** (You can use Docker to spin up just the DB, or install locally).

## 🗄️ Database Setup
1. Spin up a local Postgres instance:
   ```bash
   docker run --name actura_dev_db -e POSTGRES_USER=actura_user -e POSTGRES_PASSWORD=actura_password -e POSTGRES_DB=actura_db -p 5432:5432 -d postgres:15-alpine
   ```
2. The FastAPI backend will automatically use SQLite (`actura_local.db`) if no Postgres `DATABASE_URL` is provided. If you want to use Postgres locally, export it:
   ```bash
   export DATABASE_URL="postgresql://actura_user:actura_password@localhost:5432/actura_db"
   ```

## 🐍 Backend (FastAPI) Setup
1. Navigate to the engine directory:
   ```bash
   cd actuary_engine
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```
   The backend will now be available at `http://localhost:8000`.

## 🌐 Frontend (Vue 3) Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install NPM dependencies:
   ```bash
   npm install
   ```
3. Create a `.env.local` file (optional, if you need to override the API base URL):
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```
4. Start the Vite dev server:
   ```bash
   npm run dev
   ```
   The frontend will now be available at `http://localhost:5173`. Hot-Module Replacement (HMR) is enabled.

## 🧪 Running Tests
Actura uses `pytest` for the backend validation.
```bash
cd actuary_engine
pytest ../tests/ -v
```

## 📐 Project Structure Guidelines
- **UI Components:** Place inside `frontend/src/components/`. If it's a Vue Flow node, place it in `frontend/src/components/nodes/`.
- **Actuarial Logic:** Add quantitative python code to `actuary_engine/`. Do NOT put mathematical logic in the FastAPI router files (`api/routes/`). Use service classes instead.
- **Styling:** We use Tailwind CSS. Avoid writing raw CSS unless you are overriding Vue Flow internals in `style.css`.
