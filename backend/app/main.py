from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from typing import List, Dict, Any
import os

import math
import time

import pandas as pd
import numpy as np
import yfinance as yf
import requests

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

    # Universes: if cap=all, load NIFTY500 (from local CSV or env URL); otherwise fall back to small hardcoded lists
    UNIVERSE = {
        "large": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"],
        "mid":   ["CUMMINSIND.NS", "AIAENG.NS", "PIIND.NS", "AUROPHARMA.NS", "TATAELXSI.NS"],
        "small": ["NEULANDLAB.NS", "LATENTVIEW.NS", "MAPMYINDIA.NS", "KEI.NS", "VINATIORGA.NS"],
    }

    symbols: List[str] = []
    if cap == "all":
        symbols = _load_nifty500_symbols()
        if not symbols:
            # fallback to combined small,mid,large if NIFTY500 not available
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
    cache_ttl = 900 if cap == "all" else 300  # longer cache for large universe
    now_ts = time.time()

    if _CACHE["data"].get(cache_key) and now_ts - _CACHE["data"][cache_key]["ts"] < cache_ttl:
        ranked = _CACHE["data"][cache_key]["items"]
    else:
        ranked = _rank_symbols(symbols, min_bars=30, allow_minimal=True)
        _CACHE["data"][cache_key] = {"items": ranked, "ts": now_ts}

    # Pagination (up to 3 pages of size n)
    n = max(1, min(3, n))
    page = max(1, min(3, page))
    start = (page - 1) * n
    end = start + n
    page_items = ranked[start:end]
    total = len(ranked)

    return {
        "timestamp": now,
        "recommendations": page_items,
        "page": page,
        "page_size": n,
        "cap": cap,
        "total_available": total,
        "disclaimer": "This output is informational only; not financial advice.",
    }


@app.get("/recommendations/one")
def one_recommendation(ticker: str, exchange: str = "NSE"):
    """
    Analyze a single NSE/BSE ticker on demand using the same technical pipeline.
    - ticker: e.g., RELIANCE, TCS, HDFC
    - exchange: NSE | BSE (defaults NSE)
    Accepts symbols that already include Yahoo suffix (.NS/.BO).
    """
    now = datetime.now(timezone.utc).isoformat()
    sym = ticker.strip().upper()
    if not sym:
        return {"timestamp": now, "recommendation": None, "note": "Empty ticker"}

    # If user didn't include suffix, add based on exchange
    if not sym.endswith(".NS") and not sym.endswith(".BO"):
        ex = (exchange or "NSE").upper()
        if ex == "BSE":
            sym = f"{sym}.BO"
        else:
            sym = f"{sym}.NS"

    ranked = _rank_symbols([sym], min_bars=20, allow_minimal=True)
    if ranked:
        return {"timestamp": now, "recommendation": ranked[0], "note": None}

    # If no live data, provide a helpful note (live-only mode)
    # As a last resort, try minimal quote-only snapshot
    minimal = _minimal_from_quote(sym)
    if minimal is not None:
        return {"timestamp": now, "recommendation": minimal, "note": "Quote-only snapshot (limited data)."}
    return {"timestamp": now, "recommendation": None, "note": "No live data available for this symbol at the moment. Try later or check the symbol/exchange."}

def _rank_symbols(symbols: List[str], min_bars: int = 60, allow_minimal: bool = False) -> List[Dict[str, Any]]:
    results = []
    # Use a shared session with a desktop User-Agent to reduce blocks
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    })
    for sym in symbols:
        try:
            df = None
            # Try multiple periods to increase chance of data
            for period in ("2y", "1y", "6mo", "3mo"):
                df = yf.download(sym, period=period, interval="1d", auto_adjust=True, progress=False, threads=False, session=session)
                if df is not None and not df.empty:
                    break
            if df is None or df.empty or len(df) < min_bars:
                if allow_minimal:
                    m = _minimal_from_quote(sym)
                    if m is not None:
                        results.append(m)
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
            elif composite < 55:
                classification = "Avoid"

            # Stop-loss and targets
            stop_loss = round(float(last.c - 1.8 * (atr if atr == atr else 0)), 2)
            target1 = round(float(last.c * 1.12), 2)
            target2 = round(float(last.c * 1.28), 2)

            results.append({
                "ticker": sym.replace(".NS", ""),
                "cap": _cap_for_symbol(sym),
                "composite_score": composite,
                "classification": classification,
                "holding_duration": (
                    "Short (1-30 days)" if classification == "Short-Term Blast" else (
                        "Long (>12 months)" if classification == "Multi-Bagger" else (
                            "N/A" if classification == "Avoid" else "Medium (1-12 months)"
                        )
                    )
                ),
                "confidence": int(max(10, min(90, composite - 25 + trend * 5))),
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


def _minimal_from_quote(sym: str) -> Dict[str, Any] | None:
    try:
        tk = yf.Ticker(sym)
        finfo = getattr(tk, 'fast_info', None)
        price = None
        prev = None
        if finfo:
            price = getattr(finfo, 'last_price', None) or getattr(finfo, 'lastPrice', None) or getattr(finfo, 'last_trade_price', None)
            prev = getattr(finfo, 'previous_close', None) or getattr(finfo, 'previousClose', None)
        if price is None:
            hist = tk.history(period="5d", interval="1d", auto_adjust=True)
            if hist is not None and not hist.empty:
                price = float(hist['Close'].iloc[-1])
                if len(hist) > 1:
                    prev = float(hist['Close'].iloc[-2])
        if price is None:
            return None
        change_pct = 0.0
        if prev is not None and prev != 0:
            change_pct = (price - prev) / prev
        composite = max(10.0, 50.0 + change_pct * 100 * 0.5)  # modestly scale daily change
        composite = round(float(min(100.0, max(0.0, composite))), 1)
        classification = "Avoid" if composite < 55 else ("Neutral" if composite < 70 else "Short-Term Blast")
        stop_loss = round(price * 0.95, 2)
        target1 = round(price * 1.08, 2)
        target2 = round(price * 1.15, 2)
        trend_bonus = 0
        confidence = int(max(10, min(85, 25 + trend_bonus * 5 + (composite - 50))))
        return {
            "ticker": sym.replace(".NS", "").replace(".BO", ""),
            "cap": _cap_for_symbol(sym),
            "composite_score": composite,
            "classification": classification,
            "holding_duration": "N/A" if classification == "Avoid" else "Medium (1-12 months)",
            "confidence": confidence,
            "rationale": "Quote-only snapshot: derived from last/prev close; limited indicators.",
            "stop_loss": stop_loss,
            "target_band": [target1, target2],
            "evidence": ["yfinance:fast_info|history"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return None


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


def _load_nifty500_symbols() -> List[str]:
    """
    Load NIFTY 500 symbols (NSE) and append .NS for Yahoo. Priority:
    1) Environment variable NIFTY500_URL (CSV with a column of tickers without suffix)
    2) Local file backend/app/data/nifty500.csv
    """
    global _UNIVERSE_CACHE
    try:
        _UNIVERSE_CACHE
    except NameError:
        _UNIVERSE_CACHE = {"nifty500": None}

    if _UNIVERSE_CACHE.get("nifty500"):
        return _UNIVERSE_CACHE["nifty500"]

    symbols: List[str] = []
    url = os.getenv("NIFTY500_URL", "").strip()
    try:
        if url:
            import csv, io, requests as _req
            r = _req.get(url, timeout=15)
            r.raise_for_status()
            content = r.text
            reader = csv.reader(io.StringIO(content))
            for row in reader:
                if not row:
                    continue
                raw = row[0].strip().upper()
                if not raw or raw == "SYMBOL":
                    continue
                if raw.endswith(".NS"):
                    symbols.append(raw)
                else:
                    symbols.append(f"{raw}.NS")
    except Exception:
        symbols = []

    if not symbols:
        # try local file
        try:
            import csv
            file_path = os.path.join(os.path.dirname(__file__), "data", "nifty500.csv")
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    raw = row[0].strip().upper()
                    if not raw or raw == "SYMBOL":
                        continue
                    if raw.endswith(".NS"):
                        symbols.append(raw)
                    else:
                        symbols.append(f"{raw}.NS")
        except Exception:
            pass

    # de-dup and keep a reasonable cap to avoid hitting rate limits too hard in a single call
    # pagination will chunk through the cached ranked list
    symbols = list(dict.fromkeys(symbols))
    _UNIVERSE_CACHE["nifty500"] = symbols
    return symbols


def _demo_pool(now_iso: str) -> List[Dict[str, Any]]:
    # Same demo pool as before, with timestamp attached
    base = [
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
    for b in base:
        b["evidence"] = ["demo_link"]
        b["timestamp"] = now_iso
    # order by score desc to be consistent
    base.sort(key=lambda x: x["composite_score"], reverse=True)
    return base
