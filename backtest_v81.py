
import os
import requests
from datetime import datetime

TWELVE_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

def fetch_history(symbol="XAU/USD", interval="1h", outputsize=500):
    if not TWELVE_KEY:
        return None
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_KEY}&format=JSON"
        r = requests.get(url, timeout=15).json()
        if "values" not in r:
            print("Twelve error:", r)
            return None
        vals = r["values"][::-1]
        candles=[]
        for v in vals:
            candles.append({
                "datetime": v["datetime"],
                "open": float(v["open"]),
                "high": float(v["high"]),
                "low": float(v["low"]),
                "close": float(v["close"]),
            })
        return candles
    except Exception as e:
        print("Fetch error", e)
        return None

def ema(vals, period):
    if len(vals) < period:
        return sum(vals)/len(vals) if vals else 0
    k = 2/(period+1)
    ev = sum(vals[:period])/period
    for v in vals[period:]:
        ev = v*k + ev*(1-k)
    return ev

def detect_structure_simple(highs, lows):
    if len(highs) < 12:
        return {"trend": "WAIT", "last_high": 0, "last_low": 0, "prev_high": 0, "prev_low": 0, "hh": False, "hl": False, "ll": False, "lh": False}
    recent_high = max(highs[-6:-1])
    recent_low = min(lows[-6:-1])
    prev_high = max(highs[-12:-6])
    prev_low = min(lows[-12:-6])
    hh = recent_high > prev_high
    hl = recent_low > prev_low
    ll = recent_low < prev_low
    lh = recent_high < prev_high
    if hh and hl:
        trend="BUY"
    elif ll and lh:
        trend="SELL"
    elif hl and not ll:
        trend="BUY"
    elif lh and not hh:
        trend="SELL"
    else:
        trend="WAIT"
    return {"trend": trend, "last_high": recent_high, "last_low": recent_low, "prev_high": prev_high, "prev_low": prev_low, "hh": hh, "hl": hl, "ll": ll, "lh": lh}

def detect_sweep_simple(highs, lows, closes, tolerance=2.0):
    if len(highs) < 12:
        return {"is_sweep": False, "type": "NONE", "level": 0, "extreme": 0}
    for i in range(2, 10):
        if abs(lows[-i] - lows[-i-1]) <= tolerance:
            equal_level = min(lows[-i], lows[-i-1])
            if lows[-1] < equal_level - 0.3 and closes[-1] > equal_level:
                return {"is_sweep": True, "type": "BUY_SWEEP", "level": equal_level, "extreme": lows[-1]}
        if abs(highs[-i] - highs[-i-1]) <= tolerance:
            equal_level = max(highs[-i], highs[-i-1])
            if highs[-1] > equal_level + 0.3 and closes[-1] < equal_level:
                return {"is_sweep": True, "type": "SELL_SWEEP", "level": equal_level, "extreme": highs[-1]}
    recent_high = max(highs[-7:-1])
    recent_low = min(highs[-7:-1]) if False else min(lows[-7:-1])
    if lows[-1] < recent_low - 0.5 and closes[-1] > recent_low:
        return {"is_sweep": True, "type": "BUY_SWEEP", "level": recent_low, "extreme": lows[-1]}
    if highs[-1] > recent_high + 0.5 and closes[-1] < recent_high:
        return {"is_sweep": True, "type": "SELL_SWEEP", "level": recent_high, "extreme": highs[-1]}
    return {"is_sweep": False, "type": "NONE", "level": 0, "extreme": 0}

def backtest_gold_v81(candles_1h=None, candles_15m=None, min_conf=75):
    if candles_1h is None:
        candles_1h = fetch_history("XAU/USD", "1h", 500)
    if candles_1h is None or len(candles_1h) < 100:
        return {"error": "No data - set TWELVE_DATA_API_KEY env"}
    
    highs = [c["high"] for c in candles_1h]
    lows = [c["low"] for c in candles_1h]
    closes = [c["close"] for c in candles_1h]
    
    trades=[]
    wins=0
    losses=0
    total_profit=0
    
    # Simulate walk forward
    for idx in range(50, len(candles_1h)-10):
        window_highs = highs[:idx]
        window_lows = lows[:idx]
        window_closes = closes[:idx]
        
        struct = detect_structure_simple(window_highs, window_lows)
        sweep = detect_sweep_simple(window_highs, window_lows, window_closes)
        
        # Simple confluence
        ema9 = ema(window_closes, 9)
        ema21 = ema(window_closes, 21)
        ema50 = ema(window_closes, 50)
        
        direction="WAIT"
        if struct["trend"]=="BUY" and sweep["type"]=="BUY_SWEEP" and ema9 > ema21:
            direction="BUY"
        elif struct["trend"]=="SELL" and sweep["type"]=="SELL_SWEEP" and ema9 < ema21:
            direction="SELL"
        elif struct["hl"] and sweep["type"]=="BUY_SWEEP":
            direction="BUY"
        elif struct["lh"] and sweep["type"]=="SELL_SWEEP":
            direction="SELL"
        
        if direction=="WAIT":
            continue
        
        entry = window_closes[-1]
        if direction=="BUY":
            sl = min(struct["last_low"], sweep["extreme"] if sweep["is_sweep"] else struct["last_low"]) - 3
            risk = entry - sl
            if risk < 4: risk=4
            if risk > 15: risk=15
            sl = entry - risk
            tp1 = entry + risk*1.0
            tp2 = entry + risk*1.8
        else:
            sl = max(struct["last_high"], sweep["extreme"] if sweep["is_sweep"] else struct["last_high"]) + 3
            risk = sl - entry
            if risk < 4: risk=4
            if risk > 15: risk=15
            sl = entry + risk
            tp1 = entry - risk*1.0
            tp2 = entry - risk*1.8
        
        # Check next 10 candles outcome
        future = candles_1h[idx:idx+10]
        result="WAIT"
        profit=0
        for fc in future:
            if direction=="BUY":
                if fc["low"] <= sl:
                    result="LOSS"
                    profit=-risk
                    break
                if fc["high"] >= tp2:
                    result="WIN"
                    profit=risk*1.8
                    break
                if fc["high"] >= tp1:
                    result="WIN_TP1"
                    profit=risk*1.0
                    # continue to try TP2, but count as win
            else:
                if fc["high"] >= sl:
                    result="LOSS"
                    profit=-risk
                    break
                if fc["low"] <= tp2:
                    result="WIN"
                    profit=risk*1.8
                    break
                if fc["low"] <= tp1:
                    result="WIN_TP1"
                    profit=risk*1.0
        
        if result!="WAIT":
            trades.append({
                "idx": idx,
                "datetime": candles_1h[idx]["datetime"],
                "direction": direction,
                "entry": entry,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "result": result,
                "profit": profit,
                "structure": struct["trend"],
                "sweep": sweep["type"]
            })
            total_profit+=profit
            if "WIN" in result:
                wins+=1
            else:
                losses+=1
    
    total = wins+losses
    winrate = (wins/total*100) if total>0 else 0
    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "total_profit_dollars": total_profit,
        "avg_profit_per_trade": total_profit/total if total>0 else 0,
        "trades": trades[-50:]  # last 50 for display
    }

if __name__ == "__main__":
    result = backtest_gold_v81()
    print(result)
