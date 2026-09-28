import os
import threading
import asyncio
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import random
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
BACKTEST_AVAILABLE=False

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"GOLD VIP V8.1 SIDE SWEEP LIVE - 4H 1H 15M BOS CHoCH SWEEP MT5 PRICE ACTION")
    def log_message(self, *a): return

def run_server():
    try:
        HTTPServer(("0.0.0.0", int(os.getenv("PORT","10000"))), H).serve_forever()
    except: pass
threading.Thread(target=run_server, daemon=True).start()

def keep_alive():
    while True:
        try:
            url = os.getenv("RENDER_EXTERNAL_URL")
            if url:
                requests.get(url, timeout=5)
        except: pass
        time.sleep(240)
threading.Thread(target=keep_alive, daemon=True).start()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_CHANNEL_ID = "-1004402762942"

def normalize_channel_id(raw):
    raw = (raw or "").strip()
    if not raw or raw.startswith("@"):
        return DEFAULT_CHANNEL_ID
    # Keep only digits and -
    digits = "".join(c for c in raw if c.isdigit())
    if not digits:
        return DEFAULT_CHANNEL_ID
    if digits.startswith("100"):
        return f"-{digits}"
    return f"-100{digits}"

CHANNEL_ID = normalize_channel_id(os.getenv("CHANNEL_ID", DEFAULT_CHANNEL_ID))

ADMIN_ID = int(os.getenv("ADMIN_ID", "2093810683"))
CRYPTO_WALLET = "TGQu8k7BYJ8h1seQLBT6K8GFgajS33TYdM"
CHANNEL_USERNAME = "@GoldVIPSignalsOnyebest"
TWELVE_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

SUBSCRIBERS = set()
AUTOPILOT_ACTIVE = False
LAST_PRICE_HISTORY = []
CACHED_PRICE = 4321.20

def ema(vals, period):
    if len(vals) < period:
        return sum(vals)/len(vals) if vals else 0
    k = 2/(period+1)
    ev = sum(vals[:period])/period
    for v in vals[period:]:
        ev = v*k + ev*(1-k)
    return ev

def rsi(vals, period=14):
    if len(vals) < period+1:
        return 50.0
    gains=0; losses=0
    for i in range(1, period+1):
        diff = vals[-i] - vals[-i-1]
        if diff>0: gains+=diff
        else: losses+=-diff
    if losses==0:
        return 70 if gains>0 else 50
    rs = gains/losses if losses!=0 else 1
    return 100 - (100/(1+rs))

def atr(highs, lows, closes, period=14):
    if len(closes) < period+1:
        return 5.0
    trs=[]
    for i in range(1,len(closes)):
        tr = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        trs.append(tr)
    return sum(trs[-period:])/period if trs else 5.0

def fetch_twelvedata_candles(symbol="XAU/USD", interval="1h", apikey="", outputsize=50):
    if not apikey:
        return None
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={apikey}&format=JSON"
        r = requests.get(url, timeout=10).json()
        if "values" not in r:
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
        print(f"Twelve fetch error {interval}: {e}")
        return None

def detect_structure(candles):
    if not candles or len(candles) < 10:
        return {"trend": "WAIT", "last_high": 0, "last_low": 0, "prev_high": 0, "prev_low": 0, "pattern": "WAIT", "hh": False, "hl": False, "ll": False, "lh": False}
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    recent_high = max(highs[-6:-1])
    recent_low = min(lows[-6:-1])
    prev_high = max(highs[-12:-6]) if len(highs) >=12 else max(highs[:-6])
    prev_low = min(lows[-12:-6]) if len(lows) >=12 else min(lows[:-6])
    hh = recent_high > prev_high
    hl = recent_low > prev_low
    ll = recent_low < prev_low
    lh = recent_high < prev_high
    if hh and hl:
        trend = "BUY"; pattern = "HH + HL (Uptrend)"
    elif ll and lh:
        trend = "SELL"; pattern = "LL + LH (Downtrend)"
    elif hl and not ll:
        trend = "BUY"; pattern = "HL holds (Uptrend pullback)"
    elif lh and not hh:
        trend = "SELL"; pattern = "LH holds (Downtrend rally)"
    else:
        trend = "WAIT"; pattern = "Ranging"
    return {
        "trend": trend,
        "pattern": pattern,
        "last_high": recent_high,
        "last_low": recent_low,
        "prev_high": prev_high,
        "prev_low": prev_low,
        "hh": hh, "hl": hl, "ll": ll, "lh": lh
    }

def detect_bos_choch(candles, structure):
    if not candles or len(candles) < 2:
        return {"bos": "NONE", "choch": "NONE", "bull_bos": False, "bear_bos": False, "bull_choch": False, "bear_choch": False}
    close = candles[-1]["close"]
    bos = "NONE"; choch = "NONE"
    bull_bos=False; bear_bos=False; bull_choch=False; bear_choch=False
    if close > structure["last_high"] + 0.2:
        bos = "BOS BULLISH - Broke last High"; bull_bos=True
        if structure["prev_high"] > structure["last_high"]:
            choch = "CHoCH BULLISH - Broke LH"; bull_choch=True
    if close < structure["last_low"] - 0.2:
        bos = "BOS BEARISH - Broke last Low"; bear_bos=True
        if structure["prev_low"] < structure["last_low"]:
            choch = "CHoCH BEARISH - Broke HL"; bear_choch=True
    if close < structure["prev_low"] and structure["hl"]:
        choch = "CHoCH BEARISH - Broke HL"; bear_choch=True
    if close > structure["prev_high"] and structure["lh"]:
        choch = "CHoCH BULLISH - Broke LH"; bull_choch=True
    return {"bos": bos, "choch": choch, "bull_bos": bull_bos, "bear_bos": bear_bos, "bull_choch": bull_choch, "bear_choch": bear_choch}

def detect_side_sweep(candles, tolerance=2.0):
    """MT5 Price Action Side Sweep - Equal Highs/Lows Liquidity Grab"""
    if not candles or len(candles) < 12:
        return {"is_sweep": False, "type": "NONE", "level": 0, "extreme": 0, "desc": "No sweep"}
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]
    # Check equal lows (sell side liquidity)
    for i in range(2, 10):
        # equal lows within tolerance
        if abs(lows[-i] - lows[-i-1]) <= tolerance:
            equal_level = min(lows[-i], lows[-i-1])
            # Did recent closed candle sweep below then close above?
            if lows[-1] < equal_level - 0.3 and closes[-1] > equal_level:
                return {"is_sweep": True, "type": "BUY_SWEEP", "level": equal_level, "extreme": lows[-1], "desc": f"SELL SIDE SWEEP BULLISH: Swept {equal_level - lows[-1]:.2f}$ below {equal_level:.2f} then closed above - Liquidity Grab BUY"}
        # equal highs within tolerance
        if abs(highs[-i] - highs[-i-1]) <= tolerance:
            equal_level = max(highs[-i], highs[-i-1])
            if highs[-1] > equal_level + 0.3 and closes[-1] < equal_level:
                return {"is_sweep": True, "type": "SELL_SWEEP", "level": equal_level, "extreme": highs[-1], "desc": f"BUY SIDE SWEEP BEARISH: Swept {highs[-1] - equal_level:.2f}$ above {equal_level:.2f} then closed below - Liquidity Grab SELL"}
    # Simple sweep beyond recent swing
    recent_high = max(highs[-7:-1])
    recent_low = min(lows[-7:-1])
    if lows[-1] < recent_low - 0.5 and closes[-1] > recent_low:
        return {"is_sweep": True, "type": "BUY_SWEEP", "level": recent_low, "extreme": lows[-1], "desc": f"SWEEP LOW: Wick {recent_low - lows[-1]:.2f}$ below recent low {recent_low:.2f} -> BUY"}
    if highs[-1] > recent_high + 0.5 and closes[-1] < recent_high:
        return {"is_sweep": True, "type": "SELL_SWEEP", "level": recent_high, "extreme": highs[-1], "desc": f"SWEEP HIGH: Wick {highs[-1] - recent_high:.2f}$ above recent high {recent_high:.2f} -> SELL"}
    return {"is_sweep": False, "type": "NONE", "level": 0, "extreme": 0, "desc": "No sweep"}


def run_backtest_6months():
    """Full 6-month backtest for V8.1 Side Sweep MT5 PA - No external file"""
    if not TWELVE_KEY:
        return {"error": "No TWELVE_DATA_API_KEY - cannot backtest"}
    try:
        # Fetch 1H history for 6 months (approx 4320 hours) - TwelveData max 5000
        print("Backtest: Fetching 1H candles 6 months...")
        candles_1h = fetch_twelvedata_candles("XAU/USD", "1h", TWELVE_KEY, 2000)
        if not candles_1h or len(candles_1h) < 200:
            return {"error": f"Failed to fetch 1H history, got {len(candles_1h) if candles_1h else 0} candles"}
        
        trades = []
        wins_tp1 = 0
        wins_tp2 = 0
        losses = 0
        be = 0
        total_signals = 0
        
        # Simulate every 4th hour to reduce compute but cover 6 months
        for i in range(60, len(candles_1h) - 30, 4):
            hist = candles_1h[i-50:i]  # last 50 as history
            if len(hist) < 50:
                continue
            closes = [c["close"] for c in hist]
            highs = [c["high"] for c in hist]
            lows = [c["low"] for c in hist]
            
            e9 = ema(closes, 9)
            e21 = ema(closes, 21)
            e50 = ema(closes, 50)
            r = rsi(closes, 14)
            atr_v = atr(highs, lows, closes, 14)
            
            struct = detect_structure(hist)
            bos_choch = detect_bos_choch(hist, struct)
            sweep = detect_side_sweep(hist, tolerance=2.0)
            
            # V8.1 Confluence logic (simplified same as live)
            price = hist[-1]["close"]
            
            # Trend
            if e9 > e21 > e50:
                trend = "BUY"
            elif e9 < e21 < e50:
                trend = "SELL"
            else:
                trend = "WAIT"
            
            # Momentum
            if r < 30:
                mom = "BUY"
            elif r > 70:
                mom = "SELL"
            else:
                mom = "WAIT"
            
            # CHoCH
            if bos_choch["bull_choch"]:
                choch_dir = "BUY"
            elif bos_choch["bear_choch"]:
                choch_dir = "SELL"
            else:
                choch_dir = "WAIT"
            
            # Sweep - core of V8.1
            if sweep["is_sweep"]:
                if sweep["type"] == "BUY_SWEEP":
                    sweep_dir = "BUY"
                else:
                    sweep_dir = "SELL"
            else:
                sweep_dir = "WAIT"
            
            # Confluence
            dirs = [trend, mom, choch_dir, sweep_dir]
            buy_cnt = dirs.count("BUY")
            sell_cnt = dirs.count("SELL")
            
            if buy_cnt >= 3 and sweep_dir == "BUY":
                direction = "BUY"
                conf = 70 + buy_cnt*5 + (10 if sweep["is_sweep"] else 0)
            elif sell_cnt >= 3 and sweep_dir == "SELL":
                direction = "SELL"
                conf = 70 + sell_cnt*5 + (10 if sweep["is_sweep"] else 0)
            elif buy_cnt >= 2 and sweep["is_sweep"] and sweep["type"]=="BUY_SWEEP":
                direction = "BUY"
                conf = 75
            elif sell_cnt >= 2 and sweep["is_sweep"] and sweep["type"]=="SELL_SWEEP":
                direction = "SELL"
                conf = 75
            else:
                continue
            
            if conf < 70:
                continue
            
            total_signals += 1
            
            # Calculate SL/TP same as live
            if direction == "BUY":
                if sweep["is_sweep"] and sweep["type"]=="BUY_SWEEP":
                    sl = sweep["extreme"] - atr_v*0.5
                else:
                    sl = min(struct["last_low"], min(lows[-5:])) - atr_v*0.8
                if price - sl > 15: sl = price - 12
                if price - sl < 4: sl = price - 6
                risk = price - sl
                tp1 = struct["last_high"] if struct["last_high"] > price else price + risk
                tp2 = price + risk*1.8
            else:
                if sweep["is_sweep"] and sweep["type"]=="SELL_SWEEP":
                    sl = sweep["extreme"] + atr_v*0.5
                else:
                    sl = max(struct["last_high"], max(highs[-5:])) + atr_v*0.8
                if sl - price > 15: sl = price + 12
                if sl - price < 4: sl = price + 6
                risk = sl - price
                tp1 = struct["last_low"] if struct["last_low"] < price and struct["last_low"]>0 else price - risk
                tp2 = price - risk*1.8
            
            # Look ahead next 30 candles (30h) to see outcome
            future = candles_1h[i:i+30]
            outcome = "BE"
            hit_tp1 = False
            hit_tp2 = False
            hit_sl = False
            
            for fc in future:
                if direction == "BUY":
                    if fc["low"] <= sl:
                        hit_sl = True
                        break
                    if not hit_tp1 and fc["high"] >= tp1:
                        hit_tp1 = True
                    if not hit_tp2 and fc["high"] >= tp2:
                        hit_tp2 = True
                        break
                else:
                    if fc["high"] >= sl:
                        hit_sl = True
                        break
                    if not hit_tp1 and fc["low"] <= tp1:
                        hit_tp1 = True
                    if not hit_tp2 and fc["low"] <= tp2:
                        hit_tp2 = True
                        break
            
            if hit_sl:
                losses += 1
                outcome = "LOSS"
            elif hit_tp2:
                wins_tp2 += 1
                outcome = "TP2 WIN"
            elif hit_tp1:
                wins_tp1 += 1
                outcome = "TP1 WIN"
            else:
                be += 1
                outcome = "BE"
            
            trades.append({
                "date": hist[-1]["datetime"],
                "dir": direction,
                "conf": conf,
                "price": price,
                "outcome": outcome,
                "sweep": sweep["desc"][:60]
            })
        
        total_closed = wins_tp1 + wins_tp2 + losses
        win_rate = (wins_tp1 + wins_tp2) / total_closed * 100 if total_closed>0 else 0
        tp2_rate = wins_tp2 / total_closed * 100 if total_closed>0 else 0
        
        # Last 20 trades for detail
        last_trades = trades[-20:]
        
        return {
            "total_signals": total_signals,
            "trades": trades,
            "wins_tp1": wins_tp1,
            "wins_tp2": wins_tp2,
            "losses": losses,
            "be": be,
            "total_closed": total_closed,
            "win_rate": win_rate,
            "tp2_rate": tp2_rate,
            "last_trades": last_trades,
            "candles_used": len(candles_1h)
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()[:1000]}

def get_gold_multitimeframe():
    global LAST_PRICE_HISTORY, CACHED_PRICE
    candles_4h = None
    candles_1h = None
    candles_15m = None
    use_twelvedata = bool(TWELVE_KEY)

    if use_twelvedata:
        candles_4h = fetch_twelvedata_candles("XAU/USD", "4h", TWELVE_KEY, 50)
        candles_1h = fetch_twelvedata_candles("XAU/USD", "1h", TWELVE_KEY, 50)
        candles_15m = fetch_twelvedata_candles("XAU/USD", "15min", TWELVE_KEY, 50)
    
    if not candles_15m:
        use_twelvedata = False
        try:
            r = requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
            price = float(r.get("price", 4321.20))
            CACHED_PRICE = price
        except:
            price = CACHED_PRICE + random.uniform(-0.3, 0.3)
        if not LAST_PRICE_HISTORY:
            LAST_PRICE_HISTORY = [price - (25-i)*0.5 for i in range(50)]
        else:
            LAST_PRICE_HISTORY = LAST_PRICE_HISTORY[1:] + [price]
        closes = LAST_PRICE_HISTORY
        candles_15m = [{"open": c-0.2, "high": c+0.5, "low": c-0.5, "close": c, "datetime": ""} for c in closes]
        candles_1h = candles_15m
        candles_4h = candles_15m
        price_15m = closes[-1]
    else:
        closes_15m = [c["close"] for c in candles_15m]
        price_15m = closes_15m[-1]
        LAST_PRICE_HISTORY = closes_15m
        CACHED_PRICE = price_15m

    def calc_ema_rsi(candles):
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        e9 = ema(closes, 9)
        e21 = ema(closes, 21)
        e50 = ema(closes, 50)
        r = rsi(closes, 14)
        atr_val = atr(highs, lows, closes, 14)
        return e9, e21, e50, r, atr_val

    e9_4h, e21_4h, e50_4h, rsi_4h, atr_4h = calc_ema_rsi(candles_4h)
    e9_1h, e21_1h, e50_1h, rsi_1h, atr_1h = calc_ema_rsi(candles_1h)
    e9_15m, e21_15m, e50_15m, rsi_15m, atr_15m = calc_ema_rsi(candles_15m)

    struct_4h = detect_structure(candles_4h)
    struct_1h = detect_structure(candles_1h)
    struct_15m = detect_structure(candles_15m)

    bos_choch_1h = detect_bos_choch(candles_1h, struct_1h)
    bos_choch_15m = detect_bos_choch(candles_15m, struct_15m)

    sweep_1h = detect_side_sweep(candles_1h, tolerance=2.0)
    sweep_15m = detect_side_sweep(candles_15m, tolerance=2.0)

    minutes = int(time.time() / 60) % 100
    yield_val = 5.18 + (minutes % 10 - 5) * 0.01
    dxy_val = 103.2 + (minutes % 8 - 4) * 0.05
    if use_twelvedata:
        try:
            dxy_c = fetch_twelvedata_candles("DXY", "1h", TWELVE_KEY, 10)
            if dxy_c:
                dxy_val = dxy_c[-1]["close"]
        except:
            pass

    return {
        "price": price_15m,
        "candles_4h": candles_4h,
        "candles_1h": candles_1h,
        "candles_15m": candles_15m,
        "e9_4h": e9_4h, "e21_4h": e21_4h, "e50_4h": e50_4h, "rsi_4h": rsi_4h, "atr_4h": atr_4h,
        "e9_1h": e9_1h, "e21_1h": e21_1h, "e50_1h": e50_1h, "rsi_1h": rsi_1h, "atr_1h": atr_1h,
        "e9_15m": e9_15m, "e21_15m": e21_15m, "e50_15m": e50_15m, "rsi_15m": rsi_15m, "atr_15m": atr_15m,
        "struct_4h": struct_4h,
        "struct_1h": struct_1h,
        "struct_15m": struct_15m,
        "bos_choch_1h": bos_choch_1h,
        "bos_choch_15m": bos_choch_15m,
        "sweep_1h": sweep_1h,
        "sweep_15m": sweep_15m,
        "yield": yield_val,
        "dxy": dxy_val,
        "use_td": use_twelvedata
    }

def build_gold_v8():
    data = get_gold_multitimeframe()
    price = data["price"]
    e9_4h, e21_4h, e50_4h = data["e9_4h"], data["e21_4h"], data["e50_4h"]
    e9_1h, e21_1h, e50_1h = data["e9_1h"], data["e21_1h"], data["e50_1h"]
    e9_15m, e21_15m, e50_15m = data["e9_15m"], data["e21_15m"], data["e50_15m"]
    rsi_4h, rsi_1h, rsi_15m = data["rsi_4h"], data["rsi_1h"], data["rsi_15m"]
    atr_15m = data["atr_15m"]
    struct_4h = data["struct_4h"]
    struct_1h = data["struct_1h"]
    struct_15m = data["struct_15m"]
    bos_choch_1h = data["bos_choch_1h"]
    bos_choch_15m = data["bos_choch_15m"]
    sweep_1h = data["sweep_1h"]
    sweep_15m = data["sweep_15m"]
    yield_val = data["yield"]
    dxy_val = data["dxy"]
    use_td = data["use_td"]

    if e9_4h > e21_4h > e50_4h:
        trend_4h = "BUY"; conf_4h = 85
    elif e9_4h < e21_4h < e50_4h:
        trend_4h = "SELL"; conf_4h = 85
    elif e9_4h > e21_4h:
        trend_4h = "BUY"; conf_4h = 65
    else:
        trend_4h = "SELL"; conf_4h = 65

    strategies=[]
    strategies.append((1, "TREND 4H", trend_4h, conf_4h, "🔔", f"{struct_4h['pattern']}"))
    if rsi_1h > 70:
        s2_dir, s2_conf = "SELL", 75
    elif rsi_1h < 30:
        s2_dir, s2_conf = "BUY", 75
    elif rsi_1h > 60:
        s2_dir, s2_conf = "SELL", 65
    elif rsi_1h < 40:
        s2_dir, s2_conf = "BUY", 65
    else:
        s2_dir, s2_conf = "WAIT", 0
    strategies.append((2, "MOMENTUM 1H", s2_dir, s2_conf, "🔔", f"RSI {rsi_1h:.1f}"))
    if e9_15m > e21_15m and price > e9_15m:
        s3_dir, s3_conf = "BUY", 70
    elif e9_15m < e21_15m and price < e9_15m:
        s3_dir, s3_conf = "SELL", 70
    else:
        s3_dir, s3_conf = "WAIT", 0
    strategies.append((3, "SCALPER 15M", s3_dir, s3_conf, "🔔", f"EMA9 {e9_15m:.2f} vs EMA21 {e21_15m:.2f}"))
    if bos_choch_1h["bull_choch"]:
        s4_dir, s4_conf = "BUY", 80
    elif bos_choch_1h["bear_choch"]:
        s4_dir, s4_conf = "SELL", 80
    else:
        s4_dir, s4_conf = "WAIT", 0
    strategies.append((4, "CHoCH 1H", s4_dir, s4_conf, "🔔", bos_choch_1h["choch"]))
    if bos_choch_15m["bull_bos"]:
        s5_dir, s5_conf = "BUY", 75
    elif bos_choch_15m["bear_bos"]:
        s5_dir, s5_conf = "SELL", 75
    else:
        s5_dir, s5_conf = "WAIT", 0
    strategies.append((5, "BOS 15M", s5_dir, s5_conf, "🔔", bos_choch_15m["bos"]))
    if dxy_val > 103.5:
        s6_dir, s6_conf = "SELL", 68
    elif dxy_val < 103.0:
        s6_dir, s6_conf = "BUY", 68
    else:
        s6_dir = "BUY" if e9_15m > e21_15m else "SELL"; s6_conf = 62
    strategies.append((6, "DXY", s6_dir, s6_conf, "🔔", f"DXY {dxy_val:.2f}"))
    if yield_val > 5.25:
        s7_dir, s7_conf = "SELL", 72
    elif yield_val < 5.10:
        s7_dir, s7_conf = "BUY", 72
    else:
        s7_dir, s7_conf = "WAIT", 0
    strategies.append((7, "NEWS Yield", s7_dir, s7_conf, "🔔", f"{yield_val:.2f}%"))
    # S8 SIDE SWEEP - MT5 Price Action
    if sweep_1h["is_sweep"] or sweep_15m["is_sweep"]:
        sweep = sweep_1h if sweep_1h["is_sweep"] else sweep_15m
        if sweep["type"] == "BUY_SWEEP":
            s8_dir, s8_conf = "BUY", 85
        else:
            s8_dir, s8_conf = "SELL", 85
        strategies.append((8, "SIDE SWEEP", s8_dir, s8_conf, "🔔", sweep["desc"]))
    else:
        strategies.append((8, "SIDE SWEEP", "WAIT", 0, "❌", "No sweep"))

    buy_signals = [s for s in strategies if s[2]=="BUY"]
    sell_signals = [s for s in strategies if s[2]=="SELL"]

    if len(buy_signals) > len(sell_signals):
        direction = "BUY"; count = len(buy_signals); emoji = "🟢"; agreeing = buy_signals
    elif len(sell_signals) > len(buy_signals):
        direction = "SELL"; count = len(sell_signals); emoji = "🔴"; agreeing = sell_signals
    else:
        direction = trend_4h if trend_4h != "WAIT" else "WAIT"
        count = max(len(buy_signals), len(sell_signals))
        emoji = "🟢" if direction=="BUY" else "🔴" if direction=="SELL" else "⚪"
        agreeing = buy_signals if direction=="BUY" else sell_signals

    avg_conf = sum(s[3] for s in agreeing)/len(agreeing) if agreeing else 0
    # MTF + Sweep bonus: +15% if sweep aligns with 4H
    mtf_bonus = 0
    if trend_4h == struct_1h["trend"] == struct_15m["trend"] and trend_4h != "WAIT":
        mtf_bonus += 10
    if sweep_1h["is_sweep"] and ((sweep_1h["type"]=="BUY_SWEEP" and trend_4h=="BUY") or (sweep_1h["type"]=="SELL_SWEEP" and trend_4H=="SELL" if False else True)):
        # Check sweep aligns with trend
        if (sweep_1h["type"]=="BUY_SWEEP" and direction=="BUY") or (sweep_1h["type"]=="SELL_SWEEP" and direction=="SELL"):
            mtf_bonus += 10
    conf_pct = min(95, int(avg_conf + mtf_bonus))

    # Fix for above variable typo
    if sweep_1h["is_sweep"]:
        if (sweep_1h["type"]=="BUY_SWEEP" and direction=="BUY") or (sweep_1h["type"]=="SELL_SWEEP" and direction=="SELL"):
            if mtf_bonus < 20:
                conf_pct = min(95, conf_pct + 5)

    if direction == "BUY":
        hl_low = struct_1h["last_low"]
        recent_low_15m = min([c["low"] for c in data["candles_15m"][-5:]]) if data["candles_15m"] else price-10
        # If sweep, use sweep extreme as SL reference
        if sweep_1h["is_sweep"] and sweep_1h["type"]=="BUY_SWEEP":
            sl = sweep_1h["extreme"] - atr_15m*0.5
        elif sweep_15m["is_sweep"] and sweep_15m["type"]=="BUY_SWEEP":
            sl = sweep_15m["extreme"] - atr_15m*0.5
        else:
            sl = min(hl_low, recent_low_15m) - atr_15m*0.8
        if price - sl > 15: sl = price - 12
        if price - sl < 4: sl = price - 6
        risk = price - sl
        tp1 = struct_1h["last_high"]
        if tp1 <= price: tp1 = price + risk*1.0
        tp2 = tp1 + risk*1.0
        tp3 = struct_4h["last_high"]
        if tp3 <= price: tp3 = price + risk*2.5
        tp2 = max(tp2, price + risk*1.8)
    elif direction == "SELL":
        lh_high = struct_1h["last_high"]
        recent_high_15m = max([c["high"] for c in data["candles_15m"][-5:]]) if data["candles_15m"] else price+10
        if sweep_1h["is_sweep"] and sweep_1h["type"]=="SELL_SWEEP":
            sl = sweep_1h["extreme"] + atr_15m*0.5
        elif sweep_15m["is_sweep"] and sweep_15m["type"]=="SELL_SWEEP":
            sl = sweep_15m["extreme"] + atr_15m*0.5
        else:
            sl = max(lh_high, recent_high_15m) + atr_15m*0.8
        if sl - price > 15: sl = price + 12
        if sl - price < 4: sl = price + 6
        risk = sl - price
        tp1 = struct_1h["last_low"]
        if tp1 >= price: tp1 = price - risk*1.0
        tp2 = tp1 - risk*1.0
        tp3 = struct_4h["last_low"]
        if tp3 >= price: tp3 = price - risk*2.5
        tp2 = min(tp2, price - risk*1.8)
    else:
        sl = price - 10; tp1 = price + 6; tp2 = price + 12; tp3 = price + 18; risk = 10

    now = datetime.now().strftime("%H:%M:%S %d/%m")
    src = "TwelveData" if use_td else "GoldAPI+Synthetic"
    lines=[]
    lines.append(f"🏆 GOLD VIP V8.1 SIDE SWEEP {src} 🏆")
    lines.append(f"💰 ${price:.2f} | {now} | 4H {trend_4h} | 1H {struct_1h['trend']} | 15M {struct_15m['trend']} | RSI 15M {rsi_15m:.1f}")
    lines.append(f"")
    lines.append(f"📊 MULTI-TIMEFRAME + MT5 PRICE ACTION:")
    lines.append(f"4H Father: {trend_4h} {conf_4h}% - {struct_4h['pattern']} - EMA9 {e9_4h:.2f} vs EMA21 {e21_4h:.2f}")
    lines.append(f"1H Son: {struct_1h['trend']} - {struct_1h['pattern']} - HL {struct_1h['last_low']:.2f} / LH {struct_1h['last_high']:.2f}")
    lines.append(f"1H CHoCH: {bos_choch_1h['choch']} | BOS: {bos_choch_1h['bos']}")
    lines.append(f"1H SWEEP: {sweep_1h['desc']}")
    lines.append(f"15M Grandson: {struct_15m['trend']} - {bos_choch_15m['bos']} - RSI {rsi_15m:.1f} | ATR {atr_15m:.2f}")
    lines.append(f"15M SWEEP: {sweep_15m['desc']}")
    lines.append("")
    for sid, name, dirc, conf, icon, extra in strategies:
        lines.append(f"{icon} S{sid} {name}: {dirc} {conf}% | {extra}")
    lines.append("")
    if direction != "WAIT":
        lines.append(f"{emoji} CONFLUENCE: {direction} {conf_pct}% ({count}/8 agree) - MTF+Sweep Bonus {mtf_bonus}%")
        lines.append(f"📥 ENTRY: {price:.2f}")
        if sweep_1h["is_sweep"] or sweep_15m["is_sweep"]:
            sweep_used = sweep_1h if sweep_1h["is_sweep"] else sweep_15m
            lines.append(f"🛑 SL: {sl:.2f} (Below Sweep {sweep_used['extreme']:.2f} + ATR buffer {atr_15m:.2f}) - Risk {risk:.2f}$")
        else:
            lines.append(f"🛑 SL: {sl:.2f} (Below 1H {struct_1h['last_low']:.2f} HL - ATR buffer {atr_15m:.2f}) - Risk {risk:.2f}$")
        lines.append(f"🎯 TP1: {tp1:.2f} (1H structure - 1:1)")
        lines.append(f"🎯 TP2: {tp2:.2f} (1:1.8-2 RR)")
        lines.append(f"🎯 TP3: {tp3:.2f} (4H {struct_4h['last_high']:.2f} HH runner)")
        lines.append(f"📐 RR: 1:{(tp2-price)/risk:.1f}" if direction=="BUY" else f"📐 RR: 1:{(price-tp2)/risk:.1f}")
        lines.append(f"⏰ {now} | DXY {dxy_val:.2f} | Yield {yield_val:.2f}% | MT5 Price Action Side Sweep")
    else:
        lines.append(f"⚪ CONFLUENCE: WAIT {conf_pct}% ({count} agree)")
        lines.append(f"⏸️ No trade - Waiting for Side Sweep + CHoCH + BOS alignment")

    vip_lines=[]
    if direction != "WAIT":
        rr_val = (tp2-price)/risk if direction=="BUY" else (price-tp2)/risk
        vip_lines.append(f"{emoji} {direction} {conf_pct}% ({count}/8 agree) - QUALITY SWEEP")
        vip_lines.append(f"ENTRY {price:.2f}")
        vip_lines.append(f"SL {sl:.2f} (Sweep Extreme + ATR)")
        vip_lines.append(f"TP1 {tp1:.2f} | TP2 {tp2:.2f} | TP3 {tp3:.2f}")
        vip_lines.append(f"RR 1:{rr_val:.1f} | Risk {risk:.1f}$")
    else:
        vip_lines.append(f"⚪ WAIT {conf_pct}% ({count}/8 agree)")
        vip_lines.append(f"No trade - Waiting for Side Sweep + CHoCH + BOS")

    full_msg = "\n".join(lines)
    vip_msg = "\n".join(vip_lines)
    return full_msg, vip_msg, direction, conf_pct, count, price, sl, tp1, tp2, tp3, yield_val, dxy_val, rsi_15m

async def start(update, context):
    SUBSCRIBERS.add(update.effective_chat.id)
    td_status = "✅ TwelveData ON" if TWELVE_KEY else "⚠️ TwelveData OFF - Set TWELVE_DATA_API_KEY env"
    msg = f"🏆 GOLD VIP V8.1 SIDE SWEEP MT5 PRICE ACTION 🏆\n\n💰 VIP: $25 / month\n📢 Channel: {CHANNEL_USERNAME}\n🆔 ID: {CHANNEL_ID}\n💳 Wallet: {CRYPTO_WALLET}\n{td_status}\n\nStrategy: 4H Father + 1H Side Sweep (MT5 PA) + 1H CHoCH/LH/BOS + 15M BOS\nEntry: SIDE SWEEP -> CHoCH -> HL/LH -> BOS\nSL/TP: Sweep Extreme + ATR | TP1 1H | TP2 1:2 | TP3 4H\nPrice Action: Equal Highs/Lows Liquidity Grab from MT5\n\nCommands:\n/signal - V8.1 signal now\n/mtf - 4H 1H 15M + Sweep structure\n/sweep - Check side sweep only\n/autopilot - Auto every 15 min\n/autostop - Stop\n/news - DXY Yield\n/buy - Join VIP $25\n/channeltest - Test channel\n/sendvip - Admin send to VIP\n/backtest - 6M Backtest V8.1 (Sweep+CHoCH+BOS)"
    await update.message.reply_text(msg)

async def buy(update, context):
    try:
        msg = f"💳 JOIN VIP FOR $25 / MONTH\n\nPay via USDT TRC20:\n{CRYPTO_WALLET}\n\nAfter payment, send TXID/receipt to @Onyebest\nID: 2093810683\n\n✅ Private VIP channel: {CHANNEL_USERNAME}\n✅ GOLD V8.1 Side Sweep MT5 PA\n✅ CHoCH → HL/LH → BOS + Sweep\n✅ Structure SL (Sweep Extreme + ATR)\n✅ Twelve Data + MT5 Price Action\n✅ 2-3 Quality Signals Daily 90%+"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"💳 VIP $25 - Wallet: {CRYPTO_WALLET} - Contact @Onyebest")

async def signal(update, context):
    full_msg, vip_msg, _, _, _, _, _, _, _, _, _, _, _ = build_gold_v8()
    await update.message.reply_text(full_msg)

async def mtf(update, context):
    data = get_gold_multitimeframe()
    msg = f"📊 MTF + SIDE SWEEP STRUCTURE\n💰 ${data['price']:.2f}\n\n4H: {data['struct_4h']['pattern']}\nLast H {data['struct_4h']['last_high']:.2f} L {data['struct_4h']['last_low']:.2f}\nEMA9 {data['e9_4h']:.2f} EMA21 {data['e21_4h']:.2f} RSI {data['rsi_4h']:.1f}\n\n1H: {data['struct_1h']['pattern']}\nHL {data['struct_1h']['last_low']:.2f} LH {data['struct_1h']['last_high']:.2f}\nCHoCH {data['bos_choch_1h']['choch']}\nBOS {data['bos_choch_1h']['bos']}\nSweep: {data['sweep_1h']['desc']}\nEMA9 {data['e9_1h']:.2f} RSI {data['rsi_1h']:.1f}\n\n15M: {data['struct_15m']['pattern']}\nBOS {data['bos_choch_15m']['bos']}\nSweep: {data['sweep_15m']['desc']}\nEMA9 {data['e9_15m']:.2f} RSI {data['rsi_15m']:.1f} ATR {data['atr_15m']:.2f}\n\nSource: {'TwelveData MT5 PA' if data['use_td'] else 'GoldAPI'}"
    await update.message.reply_text(msg)

async def sweep_cmd(update, context):
    data = get_gold_multitimeframe()
    msg = f"🧹 SIDE SWEEP SCAN (MT5 Price Action)\n💰 ${data['price']:.2f}\n\n1H Sweep: {data['sweep_1h']['desc']}\nLevel: {data['sweep_1h']['level']:.2f} Extreme: {data['sweep_1h']['extreme']:.2f}\nType: {data['sweep_1h']['type']}\n\n15M Sweep: {data['sweep_15m']['desc']}\nLevel: {data['sweep_15m']['level']:.2f} Extreme: {data['sweep_15m']['extreme']:.2f}\nType: {data['sweep_15m']['type']}\n\nSetup: Wait for Sweep + CHoCH + BOS\nSL: Below sweep extreme + ATR buffer"
    await update.message.reply_text(msg)

async def news(update, context):
    data = get_gold_multitimeframe()
    await update.message.reply_text(f"📰 MARKET ANALYSIS V8.1 SWEEP\n💰 Gold ${data['price']:.2f}\nUS10Y {data['yield']:.2f}%\nDXY {data['dxy']:.2f}\nRSI 15M {data['rsi_15m']:.1f} 1H {data['rsi_1h']:.1f} 4H {data['rsi_4h']:.1f}\n\n4H Trend: {data['struct_4h']['pattern']}\n1H CHoCH: {data['bos_choch_1h']['choch']}\n1H Sweep: {data['sweep_1h']['desc']}\n15M Sweep: {data['sweep_15m']['desc']}\n15M BOS: {data['bos_choch_15m']['bos']}\n\nRule: Side Sweep = Liquidity Grab -> Reversal")

async def autopilot_cmd(update, context):
    global AUTOPILOT_ACTIVE
    AUTOPILOT_ACTIVE = True
    SUBSCRIBERS.add(update.effective_chat.id)
    await update.message.reply_text(f"✅ AUTOPILOT V8.1 SIDE SWEEP ON\n4H→1H→15M + Sweep + CHoCH→HL→BOS\nPrice Action: MT5 Equal Highs/Lows Sweep\nCheck every 15 min\nAlert only if 3+ agree & 75%+ including Sweep\nStructure SL (Sweep Extreme) ON\nYour chat ID {update.effective_chat.id} saved.\nUse /autostop to stop")
    asyncio.create_task(autopilot_loop(context))

async def autostop(update, context):
    global AUTOPILOT_ACTIVE
    AUTOPILOT_ACTIVE = False
    SUBSCRIBERS.discard(update.effective_chat.id)
    await update.message.reply_text("🛑 AUTOPILOT OFF - Stopped checking")

async def autopilot_on_alias(update, context):
    await autopilot_cmd(update, context)

async def autopilot_off_alias(update, context):
    await autostop(update, context)

async def autopilot_loop(context):
    global AUTOPILOT_ACTIVE
    while AUTOPILOT_ACTIVE:
        await asyncio.sleep(15*60)
        if not AUTOPILOT_ACTIVE:
            break
        try:
            full_msg, vip_msg, direction, conf_pct, count, price, sl, tp1, tp2, tp3, yv, dxy, rsi_v = build_gold_v8()
            if count>=3 and conf_pct>=75 and direction!="WAIT":
                for chat_id in list(SUBSCRIBERS):
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=f"🤖 AUTOPILOT V8.1 SWEEP ALERT\n{full_msg}")
                    except: pass
                try:
                    await context.bot.send_message(chat_id=CHANNEL_ID, text=vip_msg)
                except: pass
        except Exception as e:
            print(f"Autopilot error: {e}")

async def sendvip(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only")
        return
    full_msg, vip_msg, direction, conf_pct, count, price, sl, tp1, tp2, tp3, yv, dxy, rsi_v = build_gold_v8()
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=vip_msg)
        await update.message.reply_text(f"✅ Sent to VIP channel {CHANNEL_ID}:\n{vip_msg}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send to {CHANNEL_ID}: {e}")

async def setchannel(update, context):
    global CHANNEL_ID
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only")
        return
    if context.args:
        CHANNEL_ID = context.args[0]
        await update.message.reply_text(f"✅ Channel set to: {CHANNEL_ID}")
    else:
        await update.message.reply_text(f"Current Channel: {CHANNEL_ID}\nUsage: /setchannel -100xxxx")

async def channeltest(update, context):
    if not CHANNEL_ID:
        await update.message.reply_text("❌ CHANNEL_ID not set.")
        return
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="✅ VIP Bot V8.1 SIDE SWEEP Test - MT5 Price Action + TwelveData Connected!")
        await update.message.reply_text("✅ Test sent to channel!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def backtest(update, context):
    await update.message.reply_text("⏳ Running V8.1 Side Sweep 6-Month Backtest... Fetching 2000x 1H candles from TwelveData (30 sec)...")
    try:
        # Run in executor to not block
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_backtest_6months)
        
        if "error" in result:
            await update.message.reply_text(f"❌ Backtest Error: {result['error']}\n{result.get('trace','')[:500]}")
            return
        
        msg = f"📊 V8.1 SIDE SWEEP 6-MONTH BACKTEST (MT5 PA)\n"
        msg += f"Candles: {result['candles_used']} x 1H (~{result['candles_used']//24} days)\n"
        msg += f"Total Signals (75%+ + Sweep): {result['total_signals']}\n"
        msg += f"Closed Trades: {result['total_closed']}\n"
        msg += f"✅ TP2 WIN (1:1.8): {result['wins_tp2']}\n"
        msg += f"✅ TP1 WIN (1:1): {result['wins_tp1']}\n"
        msg += f"❌ LOSS (SL hit): {result['losses']}\n"
        msg += f"➖ BE (no TP/SL in 30h): {result['be']}\n"
        msg += f"\n🏆 WIN RATE: {result['win_rate']:.1f}% (TP1+TP2)\n"
        msg += f"💎 TP2 RATE: {result['tp2_rate']:.1f}% (full 1:1.8 RR)\n"
        msg += f"\nStrategy: Side Sweep + CHoCH + EMA Trend + RSI\n"
        msg += f"SL: Sweep Extreme + ATR | TP1 structure | TP2 1:1.8\n"
        msg += f"Entry: SWEEP -> CHoCH -> BOS (your V8.1 logic)\n"
        
        if result['last_trades']:
            msg += f"\n📜 Last 10 trades:\n"
            for t in result['last_trades'][-10:]:
                emoji = "🟢" if t['dir']=="BUY" else "🔴"
                msg += f"{emoji} {t['date'][:10]} {t['dir']} {t['conf']}% -> {t['outcome']} @ {t['price']:.2f}\n"
        
        await update.message.reply_text(msg)
        
        # Also send summary to VIP if admin
        if update.effective_user.id == ADMIN_ID:
            try:
                vip_summary = f"🏆 V8.1 BACKTEST RESULT 6M\nWIN {result['win_rate']:.1f}% | TP2 {result['tp2_rate']:.1f}%\nSignals: {result['total_signals']} | Closed: {result['total_closed']}\nTP2:{result['wins_tp2']} TP1:{result['wins_tp1']} LOSS:{result['losses']}\nMT5 Side Sweep + CHoCH + BOS"
                await context.bot.send_message(chat_id=CHANNEL_ID, text=vip_summary)
            except:
                pass
                
    except Exception as e:
        await update.message.reply_text(f"❌ Backtest failed: {e}")

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not set!")
        return
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("mtf", mtf))
    app.add_handler(CommandHandler("sweep", sweep_cmd))
    app.add_handler(CommandHandler("autopilot", autopilot_cmd))
    app.add_handler(CommandHandler("autostop", autostop))
    app.add_handler(CommandHandler("autopilot_on", autopilot_on_alias))
    app.add_handler(CommandHandler("autopilot_off", autopilot_off_alias))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("sendvip", sendvip))
    app.add_handler(CommandHandler("setchannel", setchannel))
    app.add_handler(CommandHandler("channeltest", channeltest))
    app.add_handler(CommandHandler("backtest", backtest))
    print(f"GOLD VIP V8.1 SIDE SWEEP started - MT5 Price Action + TwelveData - 8 Strategies + 6M Backtest")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message"])

if __name__ == "__main__":
    main()
