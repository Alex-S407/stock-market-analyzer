from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import yfinance as yf
import os

app = FastAPI()

# אפשור גישה מכל דפדפן (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INDEX_TICKERS = {
    "SOX": "^SOX",       # מדד השבבים
    "QQQ": "QQQ",        # נאסד"ק 100
    "SPY": "SPY",        # S&P 500
    "TNX": "^TNX",       # אג"ח 10 שנים
    "VIX": "^VIX",       # מדד הפחד
    "DXY": "DX-Y.NYB"    # מדד הדולר
}

def get_trend_and_strength(pct_change: float, is_inverse: bool = False):
    """מחשב מגמה (up/down/range) ועוצמה (1-5) לפי אחוז השינוי היומי"""
    if is_inverse:
        pct_change = -pct_change
        
    if abs(pct_change) < 0.2:
        return "range", 3
    elif pct_change > 0:
        strength = min(5, max(1, int(abs(pct_change) * 2)))
        return "up", strength
    else:
        strength = min(5, max(1, int(abs(pct_change) * 2)))
        return "down", strength

@app.get("/api/analyze/{ticker}")
def analyze_stock(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        company_name = info.get("longName") or info.get("shortName") or ticker.upper()
        sector = info.get("sector", "")
        beta = info.get("beta", 1.1)
        
        # שאיבת נתוני מדדים
        indices_data = []
        
        # התאמת משקלי השפעה לפי סקטור
        is_semi = "semiconductor" in sector.lower() or ticker.upper() in ["NVDA", "INTC", "AMD", "TSM", "AVGO", "MU"]
        is_tech = "technology" in sector.lower() or "tech" in sector.lower()

        weights = {
            "SOX": 40 if is_semi else (15 if is_tech else 5),
            "QQQ": 30 if is_tech else 20,
            "SPY": 20 if not is_tech else 15,
            "TNX": 5,
            "VIX": 5,
            "DXY": 3
        }

        # נורמליזציה של המשקלים ל-100%
        total_weight = sum(weights.values())
        
        index_names_hebrew = {
            "SOX": 'מדד השבבים (SOX)',
            "QQQ": 'נאסד"ק 100 (QQQ)',
            "SPY": 'S&P 500 (SPY)',
            "TNX": 'אג"ח 10Y (TNX)',
            "VIX": 'מדד הפחד (VIX)',
            "DXY": 'מדד הדולר (DXY)'
        }

        for key, symbol in INDEX_TICKERS.items():
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                curr_price = hist['Close'].iloc[-1]
                pct = ((curr_price - prev_close) / prev_close) * 100
            else:
                pct = 0.0

            # VIX ו-TNX משפיעים הפוך על מניות טכנולוגיה
            is_inv = key in ["VIX", "TNX"]
            trend, strength = get_trend_and_strength(pct, is_inverse=is_inv)
            
            calculated_impact = round((weights[key] / total_weight) * 100)

            indices_data.append({
                "name": index_names_hebrew[key],
                "impact": calculated_impact,
                "trend": trend,
                "strength": strength,
                "changePct": round(pct, 2)
            })

        return {
            "ticker": ticker.upper(),
            "companyName": company_name,
            "sector": sector,
            "beta": round(beta, 2),
            "indices": indices_data
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"שגיאה בשאיבת נתונים עבור {ticker}: {str(e)}")

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
