from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

app = FastAPI(title="Stock Advisor (Free) API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/recommendations/top")
def top_recommendations(n: int = 3):
    # Stubbed sample output compatible with frontend UI
    now = datetime.now(timezone.utc).isoformat()
    sample = [
        {
            "ticker": "TCS",
            "composite_score": 88.5,
            "classification": "Multi-Bagger",
            "holding_duration": "Long (>12 months)",
            "confidence": 80,
            "rationale": "Demo payload: fundamentals strong, trend positive, neutral news.",
            "stop_loss": 3100.0,
            "target_band": [3600.0, 4200.0],
            "evidence": ["demo_link"],
            "timestamp": now,
        },
        {
            "ticker": "RELIANCE",
            "composite_score": 76.2,
            "classification": "Short-Term Blast",
            "holding_duration": "Short (1-30 days)",
            "confidence": 68,
            "rationale": "Demo payload: breakout with volume and positive short-term sentiment.",
            "stop_loss": 2850.0,
            "target_band": [3150.0, 3400.0],
            "evidence": ["demo_link"],
            "timestamp": now,
        },
        {
            "ticker": "HDFC",
            "composite_score": 72.0,
            "classification": "Neutral",
            "holding_duration": "Medium (1-12 months)",
            "confidence": 60,
            "rationale": "Demo payload: mixed signals; watchlist.",
            "stop_loss": 1500.0,
            "target_band": [1680.0, 1900.0],
            "evidence": ["demo_link"],
            "timestamp": now,
        },
    ]
    return {
        "timestamp": now,
        "recommendations": sample[: max(0, min(n, len(sample)))],
        "disclaimer": "This output is informational only; not financial advice.",
    }
