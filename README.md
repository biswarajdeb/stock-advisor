# Stock Advisor (Free-Only) — MVP

This is a free-data stock advisor web app:
- Frontend: React (Vite), deployable to Netlify
- Backend: FastAPI, deployable to Render/Railway free tier

## Quick Start

### Frontend (`frontend/`)
1. Install
```
cd frontend
npm install
```
2. Configure API base (optional)
Create `.env` with:
```
VITE_API_BASE=https://your-backend.example.com
```
If not set, it defaults to `http://localhost:8000`.

3. Run dev server
```
npm run dev
```

4. Build
```
npm run build
```
`dist/` is the publish folder (Netlify config provided).

### Backend (`backend/`)
1. Create venv and install deps
```
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run
```
uvicorn app.main:app --reload --port 8000
```

3. Endpoints
- GET `/health`
- GET `/recommendations/top?n=3` (stubbed demo payload)

## Deploy

### Netlify (Frontend)
- Connect repository, set build: `npm run build`, publish: `dist`
- Or use Netlify CLI: `netlify deploy` (requires account)

### Render/Railway (Backend)
- Use `backend/Procfile` and `requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Roadmap
- Add data ingestion (yfinance/RSS/NSE-BSE scrapers)
- Feature engineering & scoring
- Top-3 recommendations UI + alerts (Telegram/Email)
