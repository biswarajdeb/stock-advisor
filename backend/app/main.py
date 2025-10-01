from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from typing import List, Dict, Any

import math
import time

import pandas as pd
import numpy as np
import yfinance as yf

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
    Live technical-only MVP using free Yahoo Finance (yfinance):
    - Supports market-cap filter using small hardcoded universes per cap.
    - Computes RSI(14), EMA20, SMA50/200, ATR(14), breakout, volume spike.
    - Returns top by a simple technical composite score.
    """
    now = datetime.now(timezone.utc).isoformat()

    cap = (cap or "all").lower()
    if cap not in {"small", "mid", "large", "all"}:
        cap = "all"

    # Simple universes (Yahoo symbols with .NS)
    UNIVERSE = {
        "large": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"],
        "mid":   ["CUMMINSIND.NS", "AIAENG.NS", "PIIND.NS", "AUROPHARMA.NS", "TATAELXSI.NS"],
        "small": ["NEULANDLAB.NS", "LATENTVIEW.NS", "MAPMYINDIA.NS", "KEI.NS", "VINATIORGA.NS"],
    }

    symbols: List[str] = []
    if cap == "all":
        for v in UNIVERSE.values():
            symbols.extend(v)
    else:
        symbols = UNIVERSE.get(cap, [])

    # In-memory cache (5 min)
    global _CACHE
    try:
        _CACHE
    except NameError:
        _CACHE = {"data": {}, "ts": 0}

    cache_key = f"{cap}"
    cache_ttl = 300  # seconds
    now_ts = time.time()

    if _CACHE["data"].get(cache_key) and now_ts - _CACHE["data"][cache_key]["ts"] < cache_ttl:
        ranked = _CACHE["data"][cache_key]["items"]
    else:
        ranked = _rank_symbols(symbols)
        _CACHE["data"][cache_key] = {"items": ranked, "ts": now_ts}

    # Pagination (up to 3 pages of size n)
    n = max(1, min(3, n))
    page = max(1, min(3, page))
    start = (page - 1) * n
    end = start + n
    page_items = ranked[start:end]

    return {
        "timestamp": now,
        "recommendations": page_items,
        "page": page,
        "page_size": n,
        "cap": cap,
        "total_available": len(ranked),
        "disclaimer": "This output is informational only; not financial advice.",
    }


def _rank_symbols(symbols: List[str]) -> List[Dict[str, Any]]:
    results = []
    for sym in symbols:
        try:
            df = yf.download(sym, period="6mo", interval="1d", auto_adjust=False, progress=False)
            if df is None or df.empty or len(df) < 60:
                continue
            df = df.rename(columns={"Open":"o","High":"h","Low":"l","Close":"c","Volume":"v"}).dropna()

            # Compute indicators
            df["ema20"] = df["c"].ewm(span=20, adjust=False).mean()
            df["sma50"] = df["c"].rolling(50).mean()
            df["sma200"] = df["c"].rolling(200).mean()
            df["rsi14"] = _rsi(df["c"], 14)
            df["tr"] = np.maximum(df["h"] - df["l"], np.maximum((df["h"] - df["c"].shift()).abs(), (df["l"] - df["c"].shift()).abs()))
            df["atr14"] = df["tr"].rolling(14).mean()
            df["vol20"] = df["v"].rolling(20).mean()
            df["vol_spike"] = df["v"] / df["vol20"]
            df["hh50"] = df["h"].rolling(50).max()
            df["breakout50"] = (df["c"] > df["hh50"]).astype(int)

            last = df.iloc[-1]

            # Technical composite (0-100)
            tech = 0.0
            # Trend stacking
            trend = 0
            if last.c > last.ema20: trend += 1
            if last.ema20 > last.sma50: trend += 1
            if pd.notna(last.sma200) and last.sma50 > last.sma200: trend += 1
            tech += (trend / 3.0) * 40  # up to 40

            # RSI: prefer 55-70 band
            rsi = float(last.rsi14) if pd.notna(last.rsi14) else 50.0
            rsi_score = max(0.0, 1.0 - abs(rsi - 62.0) / 38.0) * 25  # up to 25
            tech += rsi_score

            # Breakout and volume
            tech += (10 if last.breakout50 == 1 else 0)
            vol = float(last.vol_spike) if pd.notna(last.vol_spike) and last.vol_spike != np.inf else 1.0
            vol_score = max(0.0, min(1.0, (vol - 1.0) / 1.5)) * 15  # up to 15
            tech += vol_score

            # Volatility sanity: ATR% (lower is more stable)
            atr = float(last.atr14) if pd.notna(last.atr14) else np.nan
            atr_pct = (atr / last.c) if (atr == atr and last.c) else 0.02
            vol_penalty = max(0.0, min(1.0, (0.06 - atr_pct) / 0.06)) * 10  # up to 10
            tech += vol_penalty

            composite = round(min(100.0, max(0.0, tech)), 1)

            # Classification
            classification = "Neutral"
            if composite >= 72 and trend >= 2:
                classification = "Multi-Bagger"
            elif composite >= 70:
                classification = "Short-Term Blast"

            # Stop-loss and targets
            stop_loss = round(float(last.c - 1.8 * (atr if atr == atr else 0)), 2)
            target1 = round(float(last.c * 1.12), 2)
            target2 = round(float(last.c * 1.28), 2)

            results.append({
                "ticker": sym.replace(".NS", ""),
                "cap": _cap_for_symbol(sym),
                "composite_score": composite,
                "classification": classification,
                "holding_duration": "Short (1-30 days)" if classification == "Short-Term Blast" else ("Long (>12 months)" if classification == "Multi-Bagger" else "Medium (1-12 months)"),
                "confidence": int(min(95, max(50, composite - (20 if math.isnan(atr) else 0)))),
                "rationale": "Live technical-only MVP: trend, RSI band, breakout/volume, volatility adjusted.",
                "stop_loss": stop_loss,
                "target_band": [target1, target2],
                "evidence": ["yfinance"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            # Skip symbols that fail to fetch/compute
            continue

    # Sort by score desc and return up to 9
    results.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
    return results[:9]


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _cap_for_symbol(sym: str) -> str:
    if sym in {"RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"}:
        return "large"
    if sym in {"CUMMINSIND.NS", "AIAENG.NS", "PIIND.NS", "AUROPHARMA.NS", "TATAELXSI.NS"}:
        return "mid"
    return "small"
