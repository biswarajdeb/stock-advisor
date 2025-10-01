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
def top_recommendations(n: int = 3, page: int = 1, cap: str = "all"):
    """
    Demo recommendations endpoint with simple pagination and market-cap filter.
    Query params:
      - n: page size (default 3)
      - page: 1-based page number (default 1)
      - cap: one of small|mid|large|all (default all)
    Returns up to 9 demo items across pages 1..3.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Demo pool with caps
    pool = [
        {"ticker": "TCS", "cap": "large", "composite_score": 88.5, "classification": "Multi-Bagger", "holding_duration": "Long (>12 months)", "confidence": 80, "rationale": "Demo payload: fundamentals strong, trend positive, neutral news.", "stop_loss": 3100.0, "target_band": [3600.0, 4200.0]},
        {"ticker": "RELIANCE", "cap": "large", "composite_score": 76.2, "classification": "Short-Term Blast", "holding_duration": "Short (1-30 days)", "confidence": 68, "rationale": "Demo payload: breakout with volume and positive short-term sentiment.", "stop_loss": 2850.0, "target_band": [3150.0, 3400.0]},
        {"ticker": "HDFC", "cap": "large", "composite_score": 72.0, "classification": "Neutral", "holding_duration": "Medium (1-12 months)", "confidence": 60, "rationale": "Demo payload: mixed signals; watchlist.", "stop_loss": 1500.0, "target_band": [1680.0, 1900.0]},
        {"ticker": "AIAENG", "cap": "mid", "composite_score": 81.2, "classification": "Multi-Bagger", "holding_duration": "Long (>12 months)", "confidence": 74, "rationale": "Demo midcap: strong ROE and steady growth.", "stop_loss": 3400.0, "target_band": [3950.0, 4300.0]},
        {"ticker": "CUMMINSIND", "cap": "mid", "composite_score": 78.9, "classification": "Short-Term Blast", "holding_duration": "Short (1-30 days)", "confidence": 66, "rationale": "Demo midcap: momentum continuation setup.", "stop_loss": 3150.0, "target_band": [3500.0, 3800.0]},
        {"ticker": "PIIND", "cap": "mid", "composite_score": 73.5, "classification": "Neutral", "holding_duration": "Medium (1-12 months)", "confidence": 59, "rationale": "Demo midcap: mixed fundamentals and news.", "stop_loss": 3350.0, "target_band": [3650.0, 3950.0]},
        {"ticker": "MAPMYINDIA", "cap": "small", "composite_score": 79.3, "classification": "Short-Term Blast", "holding_duration": "Short (1-30 days)", "confidence": 65, "rationale": "Demo smallcap: breakout watch with volume.", "stop_loss": 1700.0, "target_band": [1900.0, 2100.0]},
        {"ticker": "LATENTVIEW", "cap": "small", "composite_score": 75.1, "classification": "Neutral", "holding_duration": "Medium (1-12 months)", "confidence": 58, "rationale": "Demo smallcap: base-building phase.", "stop_loss": 450.0, "target_band": [520.0, 590.0]},
        {"ticker": "NEULANDLAB", "cap": "small", "composite_score": 82.0, "classification": "Multi-Bagger", "holding_duration": "Long (>12 months)", "confidence": 76, "rationale": "Demo smallcap: strong earnings momentum.", "stop_loss": 9800.0, "target_band": [11200.0, 12500.0]},
    ]

    cap = cap.lower()
    if cap not in {"small", "mid", "large", "all"}:
        cap = "all"

    filtered = [p for p in pool if cap == "all" or p["cap"] == cap]
    # Sort by composite_score desc for deterministic demo
    filtered.sort(key=lambda x: x["composite_score"], reverse=True)

    # Pagination
    n = max(1, min(3, n))  # constrain page size to 1..3
    page = max(1, min(3, page))  # allow up to 3 pages (9 total)
    start = (page - 1) * n
    end = start + n
    page_items = filtered[start:end]

    # Attach timestamps and evidence
    for item in page_items:
        item["evidence"] = ["demo_link"]
        item["timestamp"] = now

    return {
        "timestamp": now,
        "recommendations": page_items,
        "page": page,
        "page_size": n,
        "cap": cap,
        "total_available": len(filtered),
        "disclaimer": "This output is informational only; not financial advice.",
    }
