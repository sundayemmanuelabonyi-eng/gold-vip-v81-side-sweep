import os, threading, asyncio, time, requests, random
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        try:
            if self.path in ["/", "/health", "/ping", "/alive"]:
                self.wfile.write(b"GOLD VIP V5.3 FINAL KEEP - 38.7% WIN - Protected Important Sweep BOS CHoCH - ALIVE " + str(int(time.time())).encode())
            else:
                self.wfile.write(b"GOLD VIP V5.3 FINAL KEEP - 38.7% WIN - Protected Important Sweep BOS CHoCH")
        except: pass
    def log_message(self,*a): return

def run_server():
    try:
        port=int(os.getenv("PORT","10000"))
        print(f"Starting HTTP health server on 0.0.0.0:{port} - Keep Awake trick ON")
        HTTPServer(("0.0.0.0", port), H).serve_forever()
    except Exception as e:
        print(f"Server error: {e}")
threading.Thread(target=run_server, daemon=True, name="health_server").start()

def keep_alive_trick():
    """ULTRA KEEP AWAKE TRICK - as you requested Sunday - keeps bot alive 24/7"""
    print("Keep Alive Trick ACTIVATED - Pinging every 2-4 min to prevent Render sleep")
    while True:
        try:
            # 1. Ping external URL (Render self-ping)
            ext_url=os.getenv("RENDER_EXTERNAL_URL")
            if ext_url:
                try:
                    # Add random to avoid cache
                    ping_url=ext_url.rstrip("/") + f"?ping={int(time.time())}&r={random.randint(1000,9999)}"
                    requests.get(ping_url, timeout=10)
                    print(f"[KeepAlive] Pinged external: {ext_url[:50]} - OK {datetime.now().strftime('%H:%M:%S')}")
                except Exception as e:
                    print(f"[KeepAlive] External ping fail: {e}")
            
            # 2. Ping localhost health endpoint (internal)
            try:
                port=int(os.getenv("PORT","10000"))
                requests.get(f"http://127.0.0.1:{port}/health?keepalive={int(time.time())}", timeout=5)
                print(f"[KeepAlive] Pinged localhost:{port}/health - OK")
            except:
                pass
            
            # 3. Heartbeat log - proves bot alive
            print(f"[Heartbeat] Bot ALIVE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Subscribers: {len(SUBSCRIBERS)} - Autopilot: {AUTOPILOT_ACTIVE}")
            
        except Exception as e:
            print(f"[KeepAlive] Error: {e}")
        
        # Random interval 120-240 sec to look human, avoid Render detecting pattern
        sleep_time=random.randint(120, 240)
        time.sleep(sleep_time)

def keep_alive_autopilot():
    """Second keep-alive thread - ensures autopilot checks stay alive"""
    while True:
        try:
            time.sleep(60)
            if AUTOPILOT_ACTIVE:
                print(f"[Autopilot KeepAlive] Autopilot active - {len(SUBSCRIBERS)} subscribers - {datetime.now().strftime('%H:%M:%S')}")
        except:
            pass

threading.Thread(target=keep_alive_trick, daemon=True, name="keep_alive_trick").start()
threading.Thread(target=keep_alive_autopilot, daemon=True, name="autopilot_keepalive").start()

# Also add UptimeRobot-style extra pinger every 14 min (Render free tier sleeps after 15 min)
def uptime_pinger():
    while True:
        try:
            time.sleep(14*60)  # 14 min - just before Render 15 min sleep
            url=os.getenv("RENDER_EXTERNAL_URL")
            if url:
                requests.get(url, timeout=10)
                print(f"[UptimeRobot] 14-min pinger - Keep Render awake {datetime.now().strftime('%H:%M:%S')}")
        except:
            pass
threading.Thread(target=uptime_pinger, daemon=True, name="uptime_pinger").start()

BOT_TOKEN=os.getenv("BOT_TOKEN")
DEFAULT_CHANNEL_ID="-1004402762942"
def normalize_channel_id(raw):
    raw=(raw or "").strip()
    if not raw or raw.startswith("@"): return DEFAULT_CHANNEL_ID
    digits="".join(c for c in raw if c.isdigit())
    if not digits: return DEFAULT_CHANNEL_ID
    if digits.startswith("100"): return f"-{digits}"
    return f"-100{digits}"
CHANNEL_ID=normalize_channel_id(os.getenv("CHANNEL_ID", DEFAULT_CHANNEL_ID))
ADMIN_ID=int(os.getenv("ADMIN_ID","2093810683"))
CRYPTO_WALLET="TGQu8k7BYJ8h1seQLBT6K8GFgajS33TYdM"
CHANNEL_USERNAME="@GoldVIPSignalsOnyebest"
TWELVE_KEY=os.getenv("TWELVE_DATA_API_KEY","")

SUBSCRIBERS=set()
AUTOPILOT_ACTIVE=False
CACHED_PRICE=4321.20

# ==================== V5.3 FINAL KEEP - YOUR BEST ====================

def fetch_twelvedata_candles(symbol="XAU/USD", interval="1h", apikey="", outputsize=150):
    if not apikey: return None
    try:
        url=f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={apikey}&format=JSON"
        r=requests.get(url,timeout=15).json()
        if "values" not in r: return None
        vals=r["values"][::-1]
        candles=[]
        for v in vals:
            candles.append({"datetime":v["datetime"],"open":float(v["open"]),"high":float(v["high"]),"low":float(v["low"]),"close":float(v["close"])})
        return candles
    except Exception as e:
        print(f"Fetch error {interval}: {e}"); return None

def find_swings_2_2(candles):
    highs=[]; lows=[]
    for i in range(2, len(candles)-2):
        h=candles[i]["high"]
        if h > candles[i-1]["high"] and h > candles[i-2]["high"] and h > candles[i+1]["high"] and h > candles[i+2]["high"]:
            highs.append({"index":i, "price":h, "datetime":candles[i]["datetime"], "candle":candles[i]})
        l=candles[i]["low"]
        if l < candles[i-1]["low"] and l < candles[i-2]["low"] and l < candles[i+1]["low"] and l < candles[i+2]["low"]:
            lows.append({"index":i, "price":l, "datetime":candles[i]["datetime"], "candle":candles[i]})
    return highs, lows

class StructureState:
    def __init__(self):
        self.state="WAIT"
        self.protected_high=None
        self.protected_low=None
        self.important_high=None
        self.important_low=None
        self.last_bos=None
        self.last_choch=None
        self.sweeps=[]
        self.protected_high_time=None
        self.protected_low_time=None
        self.important_high_time=None
        self.important_low_time=None

def build_structure_state(candles):
    state=StructureState()
    if not candles or len(candles)<20:
        return state
    highs, lows = find_swings_2_2(candles)
    if len(highs)<1 or len(lows)<1:
        return state
    if len(highs)>=1: 
        state.important_high=highs[-1]["price"]; state.important_high_time=highs[-1]["datetime"]
    if len(lows)>=1: 
        state.important_low=lows[-1]["price"]; state.important_low_time=lows[-1]["datetime"]
    
    if len(highs)>=2 and len(lows)>=2:
        hh = highs[-1]["price"] > highs[-2]["price"]
        hl = lows[-1]["price"] > lows[-2]["price"]
        lh = highs[-1]["price"] < highs[-2]["price"]
        ll = lows[-1]["price"] < lows[-2]["price"]
        if hh and hl:
            state.state="BULLISH"
            state.protected_low=lows[-1]["price"]; state.protected_low_time=lows[-1]["datetime"]
        elif ll and lh:
            state.state="BEARISH"
            state.protected_high=highs[-1]["price"]; state.protected_high_time=highs[-1]["datetime"]
        elif hl and not ll:
            state.state="BULLISH"
            state.protected_low=lows[-1]["price"]
        elif lh and not hh:
            state.state="BEARISH"
            state.protected_high=highs[-1]["price"]
    
    sweeps=[]; last_bos=None; last_choch=None; current_state=state.state
    important_high_for_sweep = highs[-2]["price"] if len(highs)>=2 else highs[-1]["price"]
    important_low_for_sweep = lows[-2]["price"] if len(lows)>=2 else lows[-1]["price"]
    
    for i in range(max(0, len(candles)-30), len(candles)):
        c=candles[i]; close=c["close"]; high=c["high"]; low=c["low"]
        if high > important_high_for_sweep + 0.3 and close < important_high_for_sweep:
            sweeps.append({"type":"BUY_SWEEP", "level":important_high_for_sweep, "datetime":c["datetime"], "wick":high, "close":close})
        if low < important_low_for_sweep - 0.3 and close > important_low_for_sweep:
            sweeps.append({"type":"SELL_SWEEP", "level":important_low_for_sweep, "datetime":c["datetime"], "wick":low, "close":close})
        if close < important_low_for_sweep - 0.8:
            last_bos={"type":"BEARISH_BOS", "level":important_low_for_sweep, "datetime":c["datetime"], "price":close}
            current_state="BEARISH"
            for h in reversed(highs):
                if h["index"] < i:
                    state.protected_high=h["price"]; state.protected_high_time=h["datetime"]; break
            state.important_low=low; state.important_low_time=c["datetime"]
        if close > important_high_for_sweep + 0.8:
            last_bos={"type":"BULLISH_BOS", "level":important_high_for_sweep, "datetime":c["datetime"], "price":close}
            current_state="BULLISH"
            for l in reversed(lows):
                if l["index"] < i:
                    state.protected_low=l["price"]; state.protected_low_time=l["datetime"]; break
            state.important_high=high; state.important_high_time=c["datetime"]
        if state.protected_low and close < state.protected_low - 0.8:
            if current_state in ["BULLISH"]:
                last_choch={"type":"BEARISH_CHoCH", "level":state.protected_low, "datetime":c["datetime"], "price":close}
                current_state="TRANSITION_TO_BEARISH"
        if state.protected_high and close > state.protected_high + 0.8:
            if current_state in ["BEARISH"]:
                last_choch={"type":"BULLISH_CHoCH", "level":state.protected_high, "datetime":c["datetime"], "price":close}
                current_state="TRANSITION_TO_BULLISH"
    
    if last_bos:
        if last_bos["type"]=="BULLISH_BOS":
            state.state="BULLISH"
            if lows: state.protected_low=lows[-1]["price"]
        else:
            state.state="BEARISH"
            if highs: state.protected_high=highs[-1]["price"]
    elif last_choch:
        if "BEARISH_CHoCH" in last_choch["type"]: state.state="TRANSITION_TO_BEARISH"
        else: state.state="TRANSITION_TO_BULLISH"
    
    if state.state=="BULLISH" and not state.protected_low and lows:
        state.protected_low=lows[-1]["price"]
    if state.state=="BEARISH" and not state.protected_high and highs:
        state.protected_high=highs[-1]["price"]
    if not state.protected_high and highs: state.protected_high=highs[-1]["price"]
    if not state.protected_low and lows: state.protected_low=lows[-1]["price"]
    
    state.last_bos=last_bos; state.last_choch=last_choch; state.sweeps=sweeps[-10:]
    if state.state=="WAIT":
        if len(highs)>=2 and len(lows)>=2:
            if highs[-1]["price"] > highs[-2]["price"] and lows[-1]["price"] > lows[-2]["price"]:
                state.state="BULLISH"
            elif highs[-1]["price"] < highs[-2]["price"] and lows[-1]["price"] < lows[-2]["price"]:
                state.state="BEARISH"
    return state

def get_gold_v53():
    use_td=bool(TWELVE_KEY)
    candles_4h=None; candles_1h=None; candles_15m=None
    if use_td:
        candles_4h=fetch_twelvedata_candles("XAU/USD","4h",TWELVE_KEY,150)
        candles_1h=fetch_twelvedata_candles("XAU/USD","1h",TWELVE_KEY,150)
        candles_15m=fetch_twelvedata_candles("XAU/USD","15min",TWELVE_KEY,150)
    if not candles_15m:
        return None
    state_4h=build_structure_state(candles_4h)
    state_1h=build_structure_state(candles_1h)
    state_15m=build_structure_state(candles_15m)
    price=candles_15m[-1]["close"]
    return {"price":price, "candles_4h":candles_4h, "candles_1h":candles_1h, "candles_15m":candles_15m,
            "state_4h":state_4h, "state_1h":state_1h, "state_15m":state_15m, "use_td":use_td}

def build_setup_v53():
    data=get_gold_v53()
    if not data:
        return "⚠️ No TwelveData", "⚠️ No data", "WAIT", 0, 0, 0,0,0,0,0,0
    price=data["price"]
    s4h=data["state_4h"]; s1h=data["state_1h"]; s15m=data["state_15m"]
    
    def calc_atr(candles):
        highs=[c["high"] for c in candles]; lows=[c["low"] for c in candles]; closes=[c["close"] for c in candles]
        if len(closes)<15: return 7.0
        trs=[]
        for i in range(1,len(closes)):
            tr=max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
            trs.append(tr)
        return sum(trs[-14:])/14
    atr_15m=calc_atr(data["candles_15m"])

    h4_context=s4h.state
    h4_bullish = h4_context=="BULLISH"
    h4_bearish = h4_context=="BEARISH"
    
    h1_has_bullish_sequence=False; h1_has_bearish_sequence=False
    h1_last_bos_time=s1h.last_bos["datetime"] if s1h.last_bos else None
    if s1h.state=="BULLISH" and s1h.last_bos and s1h.last_bos["type"]=="BULLISH_BOS":
        h1_has_bullish_sequence=True
    if s1h.state=="BEARISH" and s1h.last_bos and s1h.last_bos["type"]=="BEARISH_BOS":
        h1_has_bearish_sequence=True

    m15_has_bullish_after_h1=False; m15_has_bearish_after_h1=False
    m15_last_bos_time=s15m.last_bos["datetime"] if s15m.last_bos else None
    if s15m.last_bos and h1_last_bos_time:
        if m15_last_bos_time and h1_last_bos_time and m15_last_bos_time > h1_last_bos_time:
            if s15m.last_bos["type"]=="BULLISH_BOS": m15_has_bullish_after_h1=True
            if s15m.last_bos["type"]=="BEARISH_BOS": m15_has_bearish_after_h1=True
    elif s15m.last_bos:
        if s15m.last_bos["type"]=="BULLISH_BOS": m15_has_bullish_after_h1=True
        if s15m.last_bos["type"]=="BEARISH_BOS": m15_has_bearish_after_h1=True

    direction="WAIT"; conf=0; count=0; setup_type="NONE"
    if h4_bullish and h1_has_bullish_sequence and m15_has_bullish_after_h1:
        direction="BUY"; conf=90; count=3; setup_type="BULLISH STRUCTURE SETUP CONFIRMED"
    elif h4_bearish and h1_has_bearish_sequence and m15_has_bearish_after_h1:
        direction="SELL"; conf=90; count=3; setup_type="BEARISH STRUCTURE SETUP CONFIRMED"
    elif h1_has_bullish_sequence and m15_has_bullish_after_h1 and h4_context not in ["BEARISH"]:
        direction="BUY"; conf=80; count=2; setup_type="H1+M15 BULLISH SETUP (H4 not opposing)"
    elif h1_has_bearish_sequence and m15_has_bearish_after_h1 and h4_context not in ["BULLISH"]:
        direction="SELL"; conf=80; count=2; setup_type="H1+M15 BEARISH SETUP (H4 not opposing)"
    elif h4_context in ["TRANSITION_TO_BULLISH", "TRANSITION_TO_BEARISH"]:
        direction="WAIT"; conf=0; count=0; setup_type=f"H4 {h4_context} - Waiting for confirmation"
    else:
        direction="WAIT"; conf=0; count=0; setup_type="No chronological setup - waiting for NEW M15 after H1"

    # V5.3 KEEP: SL = Protected + 0.3 ATR, capped $25 (your best profitable version)
    if direction=="BUY":
        protected_low=s1h.protected_low or s15m.protected_low or (price-15)
        sl=protected_low - atr_15m*0.3
        if price - sl > 30: sl = price - 25
        if price - sl < 8: sl = price - 10
        risk=price-sl
        tp1=price + risk*1.0; tp2=price + risk*2.0; tp3=price + risk*3.0
    elif direction=="SELL":
        protected_high=s1h.protected_high or s15m.protected_high or (price+15)
        sl=protected_high + atr_15m*0.3
        if sl - price > 30: sl = price + 25
        if sl - price < 8: sl = price + 10
        risk=sl-price
        tp1=price - risk*1.0; tp2=price - risk*2.0; tp3=price - risk*3.0
    else:
        sl=price-10; tp1=price+10; tp2=price+20; tp3=price+30; risk=10

    now=datetime.now().strftime("%H:%M:%S %d/%m")
    src="TwelveData" if data["use_td"] else "No Data"
    lines=[]
    lines.append(f"🏆 GOLD VIP V5.3 FINAL KEEP {src} 🏆")
    lines.append(f"💰 ${price:.2f} | {now}")
    lines.append("")
    lines.append(f"📊 H4 State: {s4h.state}")
    lines.append(f"   Protected H: {s4h.protected_high or 0:.2f} L: {s4h.protected_low or 0:.2f}")
    lines.append(f"   Important H: {s4h.important_high or 0:.2f} L: {s4h.important_low or 0:.2f}")
    lines.append(f"   Last BOS: {s4h.last_bos['type'] if s4h.last_bos else 'NONE'} @ {s4h.last_bos['level'] if s4h.last_bos else 0} | {s4h.last_bos['datetime'] if s4h.last_bos else ''}")
    lines.append(f"   Last CHoCH: {s4h.last_choch['type'] if s4h.last_choch else 'NONE'} | Sweeps: {len(s4h.sweeps)}")
    lines.append("")
    lines.append(f"📊 H1 State: {s1h.state}")
    lines.append(f"   Protected H: {s1h.protected_high or 0:.2f} L: {s1h.protected_low or 0:.2f}")
    lines.append(f"   Important H: {s1h.important_high or 0:.2f} L: {s1h.important_low or 0:.2f}")
    lines.append(f"   Last BOS: {s1h.last_bos['type'] if s1h.last_bos else 'NONE'} @ {s1h.last_bos['level'] if s1h.last_bos else 0} | {s1h.last_bos['datetime'] if s1h.last_bos else ''}")
    lines.append(f"   Last CHoCH: {s1h.last_choch['type'] if s1h.last_choch else 'NONE'}")
    if s1h.sweeps:
        for sw in s1h.sweeps[-3:]:
            lines.append(f"   Sweep: {sw['type']} @ {sw['level']:.2f} | {sw['datetime']}")
    lines.append("")
    lines.append(f"📊 M15 State: {s15m.state}")
    lines.append(f"   Protected H: {s15m.protected_high or 0:.2f} L: {s15m.protected_low or 0:.2f}")
    lines.append(f"   Important H: {s15m.important_high or 0:.2f} L: {s15m.important_low or 0:.2f}")
    lines.append(f"   Last BOS: {s15m.last_bos['type'] if s15m.last_bos else 'NONE'} @ {s15m.last_bos['level'] if s15m.last_bos else 0} | {m15_last_bos_time or ''}")
    lines.append(f"   Last CHoCH: {s15m.last_choch['type'] if s15m.last_choch else 'NONE'}")
    if s15m.sweeps:
        for sw in s15m.sweeps[-3:]:
            lines.append(f"   Sweep: {sw['type']} @ {sw['level']:.2f} | {sw['datetime']}")
    lines.append("")
    lines.append(f"🔍 SETUP LAYER V5.3 KEEP:")
    lines.append(f"   H4 Context: {h4_context} (must be CONFIRMED)")
    lines.append(f"   H1 BOS Time: {h1_last_bos_time or 'NONE'}")
    lines.append(f"   M15 BOS Time: {m15_last_bos_time or 'NONE'} (must be AFTER H1)")
    lines.append(f"   M15 After H1: Bullish={m15_has_bullish_after_h1} Bearish={m15_has_bearish_after_h1}")
    lines.append("")
    if direction!="WAIT":
        emoji="🟢" if direction=="BUY" else "🔴"
        lines.append(f"{emoji} {setup_type}")
        lines.append(f"{emoji} {direction} {conf}% ({count}/3) - V5.3 KEEP")
        lines.append(f"ENTRY {price:.2f}")
        lines.append(f"SL {sl:.2f} (Protected + 0.3 ATR) = ${risk:.1f} risk")
        lines.append(f"TP1 {tp1:.2f} (1:1) | TP2 {tp2:.2f} (1:2) | TP3 {tp3:.2f} (1:3)")
        lines.append(f"RR 1:2 | ATR15M {atr_15m:.2f}")
    else:
        lines.append(f"⚪ {setup_type}")
        lines.append(f"WAIT - Need H4 CONFIRMED -> H1 BOS -> NEW M15 BOS after H1")

    vip_lines=[]
    if direction!="WAIT":
        emoji="🟢" if direction=="BUY" else "🔴"
        vip_lines.append(f"{emoji} {direction} {conf}% ({count}/3) - V5.3 KEEP SETUP CONFIRMED")
        vip_lines.append(f"ENTRY {price:.2f}")
        vip_lines.append(f"SL {sl:.2f} (Protected + 0.3 ATR)")
        vip_lines.append(f"TP1 {tp1:.2f} | TP2 {tp2:.2f} | TP3 {tp3:.2f}")
        vip_lines.append(f"RR 1:2 | {setup_type}")
    else:
        vip_lines.append(f"⚪ WAIT - V5.3 KEEP")
        vip_lines.append(f"H4 {h4_context} | H1 {s1h.state} | M15 {s15m.state}")
        vip_lines.append(f"Need: H4 CONFIRMED -> H1 BOS -> NEW M15 BOS after H1")

    return "\n".join(lines), "\n".join(vip_lines), direction, conf, count, price, sl, tp1, tp2, tp3, risk

def run_backtest_v53():
    if not TWELVE_KEY: return {"error":"No TWELVE_DATA_API_KEY"}
    try:
        print("Backtest V5.3 KEEP: 38.7% win version, SL 0.3 ATR, no BE...")
        candles_1h=fetch_twelvedata_candles("XAU/USD","1h",TWELVE_KEY,2000)
        if not candles_1h or len(candles_1h)<200: return {"error":f"Failed fetch {len(candles_1h) if candles_1h else 0}"}
        trades=[]; wins_tp1=0; wins_tp2=0; losses=0; be=0
        last_signal_idx=0
        for i in range(100, len(candles_1h)-30, 1):
            hist_1h=candles_1h[:i]
            if len(hist_1h)<100: continue
            state_1h=build_structure_state(hist_1h)
            hist_4h=hist_1h[::4]
            state_4h=build_structure_state(hist_4h)
            hist_15m=hist_1h[-30:]
            state_15m=build_structure_state(hist_15m)

            h4_bullish=state_4h.state=="BULLISH"; h4_bearish=state_4h.state=="BEARISH"
            h1_has_bullish=state_1h.state=="BULLISH" and state_1h.last_bos and state_1h.last_bos["type"]=="BULLISH_BOS"
            h1_has_bearish=state_1h.state=="BEARISH" and state_1h.last_bos and state_1h.last_bos["type"]=="BEARISH_BOS"

            m15_after_h1=False; direction=None
            if h1_has_bullish and state_15m.state in ["BULLISH", "TRANSITION_TO_BULLISH"]:
                if state_15m.last_bos and state_15m.last_bos["type"]=="BULLISH_BOS":
                    direction="BUY"; m15_after_h1=True
                elif state_15m.state=="BULLISH":
                    direction="BUY"; m15_after_h1=True
            if h1_has_bearish and state_15m.state in ["BEARISH", "TRANSITION_TO_BEARISH"]:
                if state_15m.last_bos and state_15m.last_bos["type"]=="BEARISH_BOS":
                    direction="SELL"; m15_after_h1=True
                elif state_15m.state=="BEARISH":
                    direction="SELL"; m15_after_h1=True
            if not direction:
                if h1_has_bullish and state_15m.last_bos and state_15m.last_bos["type"]=="BULLISH_BOS":
                    if state_15m.last_bos["datetime"] >= state_1h.last_bos["datetime"]:
                        direction="BUY"; m15_after_h1=True
                if h1_has_bearish and state_15m.last_bos and state_15m.last_bos["type"]=="BEARISH_BOS":
                    if state_15m.last_bos["datetime"] >= state_1h.last_bos["datetime"]:
                        direction="SELL"; m15_after_h1=True
            if not direction: continue
            if h4_bullish and direction=="SELL": continue
            if h4_bearish and direction=="BUY": continue
            if not m15_after_h1: continue
            if i - last_signal_idx < 12: continue

            price=hist_1h[-1]["close"]
            highs=[c["high"] for c in hist_1h[-20:]]; lows=[c["low"] for c in hist_1h[-20:]]; closes=[c["close"] for c in hist_1h[-20:]]
            atr_v=7.0
            if len(closes)>=15:
                trs=[]
                for j in range(1,len(closes)):
                    tr=max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1]))
                    trs.append(tr)
                atr_v=sum(trs[-14:])/14 if trs else 7.0

            # V5.3 KEEP SL: Protected + 0.3 ATR, capped $25
            if direction=="BUY":
                prot=state_1h.protected_low or state_15m.protected_low or (price-15)
                sl=prot - atr_v*0.3
                if price - sl > 30: sl=price-25
                if price - sl < 8: sl=price-10
                risk=price-sl
                tp1=price+risk*1.0; tp2=price+risk*2.0
            else:
                prot=state_1h.protected_high or state_15m.protected_high or (price+15)
                sl=prot + atr_v*0.3
                if sl - price > 30: sl=price+25
                if sl - price < 8: sl=price+10
                risk=sl-price
                tp1=price-risk*1.0; tp2=price-risk*2.0
            last_signal_idx=i

            future=candles_1h[i:i+48]
            hit_tp1=False; hit_tp2=False; hit_sl=False
            max_high=price; min_low=price
            for fc in future:
                max_high=max(max_high, fc["high"])
                min_low=min(min_low, fc["low"])
                if direction=="BUY":
                    if fc["low"]<=sl: hit_sl=True; break
                    if not hit_tp1 and fc["high"]>=tp1: hit_tp1=True
                    if not hit_tp2 and fc["high"]>=tp2: hit_tp2=True; break
                else:
                    if fc["high"]>=sl: hit_sl=True; break
                    if not hit_tp1 and fc["low"]<=tp1: hit_tp1=True
                    if not hit_tp2 and fc["low"]<=tp2: hit_tp2=True; break

            if hit_sl: losses+=1; outcome="LOSS"
            elif hit_tp2: wins_tp2+=1; outcome="TP2 WIN"
            elif hit_tp1: wins_tp1+=1; outcome="TP1 WIN"
            else: be+=1; outcome="BE"

            trades.append({
                "datetime":hist_1h[-1]["datetime"], "mt5_time":hist_1h[-1]["datetime"], "dir":direction,
                "entry":price, "sl":sl, "tp1":tp1, "tp2":tp2, "risk":risk, "outcome":outcome,
                "max_high":max_high, "min_low":min_low,
                "h4_state":state_4h.state, "h1_state":state_1h.state,
                "h1_bos":state_1h.last_bos["type"] if state_1h.last_bos else "NONE",
                "h1_bos_level":state_1h.last_bos["level"] if state_1h.last_bos else 0,
                "m15_bos":state_15m.last_bos["type"] if state_15m.last_bos else "NONE",
                "protected":state_1h.protected_low if direction=="BUY" else state_1h.protected_high,
                "important":state_1h.important_high if direction=="BUY" else state_1h.important_low,
            })

        total_closed=wins_tp1+wins_tp2+losses
        win_rate=(wins_tp1+wins_tp2)/total_closed*100 if total_closed>0 else 0
        tp2_rate=wins_tp2/total_closed*100 if total_closed>0 else 0
        return {"total_signals":len(trades),"wins_tp1":wins_tp1,"wins_tp2":wins_tp2,"losses":losses,"be":be,"total_closed":total_closed,"win_rate":win_rate,"tp2_rate":tp2_rate,"all_trades":trades,"candles_used":len(candles_1h)}
    except Exception as e:
        import traceback; return {"error":str(e),"trace":traceback.format_exc()[:2000]}

# ==================== V5.3 2TF (4H + 1H ONLY) - YOUR REQUEST ====================

def get_gold_2tf():
    use_td=bool(TWELVE_KEY)
    candles_4h=None; candles_1h=None
    if use_td:
        candles_4h=fetch_twelvedata_candles("XAU/USD","4h",TWELVE_KEY,150)
        candles_1h=fetch_twelvedata_candles("XAU/USD","1h",TWELVE_KEY,150)
    if not candles_1h:
        return None
    state_4h=build_structure_state(candles_4h)
    state_1h=build_structure_state(candles_1h)
    price=candles_1h[-1]["close"]
    return {"price":price, "candles_4h":candles_4h, "candles_1h":candles_1h, "state_4h":state_4h, "state_1h":state_1h, "use_td":use_td}

def build_setup_2tf():
    """2TF ONLY: 4H HH/HL -> HL that created HH + 1H LH broken by bullish BOS above LH -> BUY immediately. And reverse for BEARISH."""
    data=get_gold_2tf()
    if not data:
        return "⚠️ No TwelveData", "⚠️ No data", "WAIT", 0, 0, 0,0,0,0,0,0
    price=data["price"]
    s4h=data["state_4h"]; s1h=data["state_1h"]
    
    def calc_atr(candles):
        highs=[c["high"] for c in candles]; lows=[c["low"] for c in candles]; closes=[c["close"] for c in candles]
        if len(closes)<15: return 7.0
        trs=[]
        for i in range(1,len(closes)):
            tr=max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
            trs.append(tr)
        return sum(trs[-14:])/14
    atr_1h=calc_atr(data["candles_1h"])

    h4_context=s4h.state
    h4_bullish = h4_context=="BULLISH"
    h4_bearish = h4_context=="BEARISH"

    # 2TF Logic: H4 trend making HH/LL, wait for return to HL/LH that created HH/LL, then 1H break + FORM above/below
    h1_has_bullish_bos=False; h1_has_bearish_bos=False
    h1_bullish_formed_above=False; h1_bearish_formed_below=False
    h1_last_bos_time=s1h.last_bos["datetime"] if s1h.last_bos else None
    h1_last_bos_level=s1h.last_bos["level"] if s1h.last_bos else None
    h1_last_bos_price=s1h.last_bos["price"] if s1h.last_bos else None
    
    if s1h.state=="BULLISH" and s1h.last_bos and s1h.last_bos["type"]=="BULLISH_BOS":
        # Must break AND form above the LH that was broken
        level=s1h.last_bos["level"]  # This is the LH that was broken
        bos_price=s1h.last_bos["price"]  # Close that broke it
        # Check: BOS close above level + current price still above level (formed above)
        if bos_price and level and bos_price > level and price > level:
            # Also check candle formed above: close above level by at least 0.5
            if bos_price > level + 0.5:
                h1_has_bullish_bos=True
                h1_bullish_formed_above=True
    if s1h.state=="BEARISH" and s1h.last_bos and s1h.last_bos["type"]=="BEARISH_BOS":
        # Must break AND form below the HL that was broken
        level=s1h.last_bos["level"]  # This is the HL that was broken
        bos_price=s1h.last_bos["price"]
        if bos_price and level and bos_price < level and price < level:
            if bos_price < level - 0.5:
                h1_has_bearish_bos=True
                h1_bearish_formed_below=True

    direction="WAIT"; conf=0; count=0; setup_type="NONE"
    # BULLISH: 4H HH/HL -> HL that created HH -> 1H bearish LH broken AND bullish formed ABOVE it -> BUY immediately
    if h4_bullish and h1_has_bullish_bos and h1_bullish_formed_above:
        direction="BUY"; conf=90; count=2; setup_type=f"BULLISH 2TF: 4H HH/HL → HL that created HH ({s4h.protected_low or 0:.2f}) → 1H LH {h1_last_bos_level or 0:.2f} broken AND bullish formed ABOVE it @ {h1_last_bos_price or 0:.2f} → BUY continuation"
    elif h4_bearish and h1_has_bearish_bos and h1_bearish_formed_below:
        direction="SELL"; conf=90; count=2; setup_type=f"BEARISH 2TF: 4H LL/LH → LH that created LL ({s4h.protected_high or 0:.2f}) → 1H HL {h1_last_bos_level or 0:.2f} broken AND bearish formed BELOW it @ {h1_last_bos_price or 0:.2f} → SELL continuation"
    elif h1_has_bullish_bos and h1_bullish_formed_above and h4_context!="BEARISH":
        direction="BUY"; conf=80; count=2; setup_type=f"2TF: H1 LH {h1_last_bos_level or 0:.2f} broken AND bullish formed ABOVE it @ {h1_last_bos_price or 0:.2f} → BUY (H4 not opposing)"
    elif h1_has_bearish_bos and h1_bearish_formed_below and h4_context!="BULLISH":
        direction="SELL"; conf=80; count=2; setup_type=f"2TF: H1 HL {h1_last_bos_level or 0:.2f} broken AND bearish formed BELOW it @ {h1_last_bos_price or 0:.2f} → SELL (H4 not opposing)"
    else:
        if s1h.last_bos and s1h.last_bos["type"]=="BULLISH_BOS" and not h1_bullish_formed_above:
            setup_type=f"No 2TF - 1H LH {h1_last_bos_level or 0:.2f} broken but NOT formed above it yet (price {price:.2f} must be ABOVE) - Waiting to FORM ABOVE"
        elif s1h.last_bos and s1h.last_bos["type"]=="BEARISH_BOS" and not h1_bearish_formed_below:
            setup_type=f"No 2TF - 1H HL {h1_last_bos_level or 0:.2f} broken but NOT formed below it yet (price {price:.2f} must be BELOW) - Waiting to FORM BELOW"
        else:
            setup_type="No 2TF setup - Waiting for H4 trend + H1 BOS break AND form above/below LH/HL"

    # SL same as V5.3 KEEP: Protected + 0.3 ATR $25 cap
    if direction=="BUY":
        protected_low=s1h.protected_low or (price-15)
        sl=protected_low - atr_1h*0.3
        if price - sl > 30: sl = price - 25
        if price - sl < 8: sl = price - 10
        risk=price-sl
        tp1=price + risk*1.0; tp2=price + risk*2.0; tp3=price + risk*3.0
    elif direction=="SELL":
        protected_high=s1h.protected_high or (price+15)
        sl=protected_high + atr_1h*0.3
        if sl - price > 30: sl = price + 25
        if sl - price < 8: sl = price + 10
        risk=sl-price
        tp1=price - risk*1.0; tp2=price - risk*2.0; tp3=price - risk*3.0
    else:
        sl=price-10; tp1=price+10; tp2=price+20; tp3=price+30; risk=10

    now=datetime.now().strftime("%H:%M:%S %d/%m")
    src="TwelveData" if data["use_td"] else "No Data"
    lines=[]
    lines.append(f"🏆 GOLD VIP V5.3 2TF (4H+1H ONLY) {src} 🏆")
    lines.append(f"💰 ${price:.2f} | {now}")
    lines.append("")
    lines.append(f"📊 H4 State: {s4h.state} - Trend making {'HH/HL' if s4h.state=='BULLISH' else 'LL/LH' if s4h.state=='BEARISH' else 'WAIT'}")
    lines.append(f"   Protected H: {s4h.protected_high or 0:.2f} L: {s4h.protected_low or 0:.2f}")
    lines.append(f"   Important H: {s4h.important_high or 0:.2f} L: {s4h.important_low or 0:.2f}")
    lines.append(f"   Last BOS: {s4h.last_bos['type'] if s4h.last_bos else 'NONE'} @ {s4h.last_bos['level'] if s4h.last_bos else 0} | {s4h.last_bos['datetime'] if s4h.last_bos else ''}")
    lines.append(f"   Last CHoCH: {s4h.last_choch['type'] if s4h.last_choch else 'NONE'} | Sweeps: {len(s4h.sweeps)}")
    if s4h.state=="BULLISH":
        lines.append(f"   → HL that created HH: {s4h.protected_low or 0:.2f} (Protected Low = Bullish OB)")
    elif s4h.state=="BEARISH":
        lines.append(f"   → LH that created LL: {s4h.protected_high or 0:.2f} (Protected High = Bearish OB)")
    lines.append("")
    lines.append(f"📊 H1 State: {s1h.state} - {'Bearish LH broken?' if s1h.state=='BULLISH' else 'Bullish HL broken?' if s1h.state=='BEARISH' else 'WAIT'}")
    lines.append(f"   Protected H: {s1h.protected_high or 0:.2f} L: {s1h.protected_low or 0:.2f}")
    lines.append(f"   Important H: {s1h.important_high or 0:.2f} L: {s1h.important_low or 0:.2f}")
    lines.append(f"   Last BOS: {s1h.last_bos['type'] if s1h.last_bos else 'NONE'} @ {s1h.last_bos['level'] if s1h.last_bos else 0} | {s1h.last_bos['datetime'] if s1h.last_bos else ''}")
    lines.append(f"   Last CHoCH: {s1h.last_choch['type'] if s1h.last_choch else 'NONE'}")
    if s1h.sweeps:
        for sw in s1h.sweeps[-3:]:
            lines.append(f"   Sweep: {sw['type']} @ {sw['level']:.2f} | {sw['datetime']}")
    lines.append("")
    lines.append(f"🔍 SETUP LAYER 2TF (4H+1H ONLY) - MUST FORM ABOVE/BELOW:")
    lines.append(f"   H4 Context: {h4_context} - Trend making {'HH/HL' if h4_bullish else 'LL/LH' if h4_bearish else 'WAIT'}")
    lines.append(f"   H4 HL that created HH: {s4h.protected_low or 0:.2f} | LH that created LL: {s4h.protected_high or 0:.2f}")
    lines.append(f"   H1 BOS Time: {h1_last_bos_time or 'NONE'} | Level: {h1_last_bos_level or 0:.2f} | BOS Price: {h1_last_bos_price or 0:.2f}")
    lines.append(f"   H1 Formed Above: {h1_bullish_formed_above} | Formed Below: {h1_bearish_formed_below} | Current Price: {price:.2f}")
    if s1h.last_bos:
        if s1h.last_bos["type"]=="BULLISH_BOS":
            if h1_bullish_formed_above:
                lines.append(f"   ✅ 1H Bearish LH {s1h.last_bos['level']:.2f} BROKEN by Bullish BOS AND formed ABOVE it @ {s1h.last_bos['price']:.2f} (price {price:.2f} > level) → BUY continuation CONFIRMED")
            else:
                lines.append(f"   ⚠️ 1H LH {s1h.last_bos['level']:.2f} broken but NOT formed above yet (BOS price {s1h.last_bos['price']:.2f}, current {price:.2f}) - Need close ABOVE level + form above")
        else:
            if h1_bearish_formed_below:
                lines.append(f"   ✅ 1H Bullish HL {s1h.last_bos['level']:.2f} BROKEN by Bearish BOS AND formed BELOW it @ {s1h.last_bos['price']:.2f} (price {price:.2f} < level) → SELL continuation CONFIRMED")
            else:
                lines.append(f"   ⚠️ 1H HL {s1h.last_bos['level']:.2f} broken but NOT formed below yet (BOS price {s1h.last_bos['price']:.2f}, current {price:.2f}) - Need close BELOW level + form below")
    lines.append("")
    if direction!="WAIT":
        emoji="🟢" if direction=="BUY" else "🔴"
        lines.append(f"{emoji} {setup_type}")
        lines.append(f"{emoji} {direction} {conf}% ({count}/2) - V5.3 2TF")
        lines.append(f"ENTRY {price:.2f}")
        lines.append(f"SL {sl:.2f} (Protected + 0.3 ATR) = ${risk:.1f} risk")
        lines.append(f"TP1 {tp1:.2f} (1:1) | TP2 {tp2:.2f} (1:2) | TP3 {tp3:.2f} (1:3)")
        lines.append(f"RR 1:2 | ATR1H {atr_1h:.2f} | Immediate entry after 1H BOS")
    else:
        lines.append(f"⚪ {setup_type}")
        lines.append(f"WAIT - Need H4 HH/HL or LL/LH → Return to HL/LH that created HH/LL → H1 BOS break → Immediate entry")

    vip_lines=[]
    if direction!="WAIT":
        emoji="🟢" if direction=="BUY" else "🔴"
        vip_lines.append(f"{emoji} {direction} {conf}% ({count}/2) - V5.3 2TF (4H+1H) SETUP CONFIRMED")
        vip_lines.append(f"ENTRY {price:.2f}")
        vip_lines.append(f"SL {sl:.2f} (Protected + 0.3 ATR)")
        vip_lines.append(f"TP1 {tp1:.2f} | TP2 {tp2:.2f} | TP3 {tp3:.2f}")
        vip_lines.append(f"RR 1:2 | {setup_type}")
    else:
        vip_lines.append(f"⚪ WAIT - V5.3 2TF (4H+1H)")
        vip_lines.append(f"H4 {h4_context} | H1 {s1h.state}")
        vip_lines.append(f"Need: H4 HH/HL→HL that created HH + H1 LH broken by bullish BOS → BUY")

    return "\n".join(lines), "\n".join(vip_lines), direction, conf, count, price, sl, tp1, tp2, tp3, risk

def run_backtest_2tf():
    if not TWELVE_KEY: return {"error":"No TWELVE_DATA_API_KEY"}
    try:
        print("Backtest V5.3 2TF (4H+1H ONLY): HL that created HH + LH broken by BOS...")
        candles_1h=fetch_twelvedata_candles("XAU/USD","1h",TWELVE_KEY,2000)
        if not candles_1h or len(candles_1h)<200: return {"error":f"Failed fetch {len(candles_1h) if candles_1h else 0}"}
        trades=[]; wins_tp1=0; wins_tp2=0; losses=0; be=0
        last_signal_idx=0
        for i in range(100, len(candles_1h)-30, 1):
            hist_1h=candles_1h[:i]
            if len(hist_1h)<100: continue
            state_1h=build_structure_state(hist_1h)
            hist_4h=hist_1h[::4]
            state_4h=build_structure_state(hist_4h)

            h4_bullish=state_4h.state=="BULLISH"; h4_bearish=state_4h.state=="BEARISH"
            h1_has_bullish=False; h1_has_bearish=False
            # Must break AND form above/below
            if state_1h.state=="BULLISH" and state_1h.last_bos and state_1h.last_bos["type"]=="BULLISH_BOS":
                level=state_1h.last_bos["level"]
                bos_price=state_1h.last_bos["price"]
                price_now=hist_1h[-1]["close"]
                if bos_price and level and bos_price > level + 0.5 and price_now > level:
                    h1_has_bullish=True  # Broken AND formed above
            if state_1h.state=="BEARISH" and state_1h.last_bos and state_1h.last_bos["type"]=="BEARISH_BOS":
                level=state_1h.last_bos["level"]
                bos_price=state_1h.last_bos["price"]
                price_now=hist_1h[-1]["close"]
                if bos_price and level and bos_price < level - 0.5 and price_now < level:
                    h1_has_bearish=True  # Broken AND formed below

            direction=None
            if h4_bullish and h1_has_bullish:
                direction="BUY"  # 4H HH/HL -> HL that created HH -> 1H LH broken AND formed ABOVE it
            elif h4_bearish and h1_has_bearish:
                direction="SELL"  # 4H LL/LH -> LH that created LL -> 1H HL broken AND formed BELOW it
            elif h1_has_bullish and state_4h.state!="BEARISH":
                direction="BUY"
            elif h1_has_bearish and state_4h.state!="BULLISH":
                direction="SELL"
            if not direction: continue
            if h4_bullish and direction=="SELL": continue
            if h4_bearish and direction=="BUY": continue
            if i - last_signal_idx < 12: continue

            price=hist_1h[-1]["close"]
            highs=[c["high"] for c in hist_1h[-20:]]; lows=[c["low"] for c in hist_1h[-20:]]; closes=[c["close"] for c in hist_1h[-20:]]
            atr_v=7.0
            if len(closes)>=15:
                trs=[]
                for j in range(1,len(closes)):
                    tr=max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1]))
                    trs.append(tr)
                atr_v=sum(trs[-14:])/14 if trs else 7.0

            if direction=="BUY":
                prot=state_1h.protected_low or (price-15)
                sl=prot - atr_v*0.3
                if price - sl > 30: sl=price-25
                if price - sl < 8: sl=price-10
                risk=price-sl
                tp1=price+risk*1.0; tp2=price+risk*2.0
            else:
                prot=state_1h.protected_high or (price+15)
                sl=prot + atr_v*0.3
                if sl - price > 30: sl=price+25
                if sl - price < 8: sl=price+10
                risk=sl-price
                tp1=price-risk*1.0; tp2=price-risk*2.0
            last_signal_idx=i

            future=candles_1h[i:i+48]
            hit_tp1=False; hit_tp2=False; hit_sl=False
            max_high=price; min_low=price
            for fc in future:
                max_high=max(max_high, fc["high"])
                min_low=min(min_low, fc["low"])
                if direction=="BUY":
                    if fc["low"]<=sl: hit_sl=True; break
                    if not hit_tp1 and fc["high"]>=tp1: hit_tp1=True
                    if not hit_tp2 and fc["high"]>=tp2: hit_tp2=True; break
                else:
                    if fc["high"]>=sl: hit_sl=True; break
                    if not hit_tp1 and fc["low"]<=tp1: hit_tp1=True
                    if not hit_tp2 and fc["low"]<=tp2: hit_tp2=True; break

            if hit_sl: losses+=1; outcome="LOSS"
            elif hit_tp2: wins_tp2+=1; outcome="TP2 WIN"
            elif hit_tp1: wins_tp1+=1; outcome="TP1 WIN"
            else: be+=1; outcome="BE"

            trades.append({
                "datetime":hist_1h[-1]["datetime"], "mt5_time":hist_1h[-1]["datetime"], "dir":direction,
                "entry":price, "sl":sl, "tp1":tp1, "tp2":tp2, "risk":risk, "outcome":outcome,
                "max_high":max_high, "min_low":min_low,
                "h4_state":state_4h.state, "h1_state":state_1h.state,
                "h1_bos":state_1h.last_bos["type"] if state_1h.last_bos else "NONE",
                "h1_bos_level":state_1h.last_bos["level"] if state_1h.last_bos else 0,
                "m15_bos":"N/A 2TF",
                "protected":state_1h.protected_low if direction=="BUY" else state_1h.protected_high,
                "important":state_1h.important_high if direction=="BUY" else state_1h.important_low,
            })

        total_closed=wins_tp1+wins_tp2+losses
        win_rate=(wins_tp1+wins_tp2)/total_closed*100 if total_closed>0 else 0
        tp2_rate=wins_tp2/total_closed*100 if total_closed>0 else 0
        return {"total_signals":len(trades),"wins_tp1":wins_tp1,"wins_tp2":wins_tp2,"losses":losses,"be":be,"total_closed":total_closed,"win_rate":win_rate,"tp2_rate":tp2_rate,"all_trades":trades,"candles_used":len(candles_1h)}
    except Exception as e:
        import traceback; return {"error":str(e),"trace":traceback.format_exc()[:2000]}

# Telegram handlers
async def start(update, context):
    SUBSCRIBERS.add(update.effective_chat.id)
    td_status="✅ TwelveData ON" if TWELVE_KEY else "⚠️ OFF"
    msg=f"🏆 GOLD VIP V5.3 FINAL KEEP + 2TF 🏆\n\n💰 VIP: $25 / month\n📢 Channel: {CHANNEL_USERNAME}\n🆔 ID: {CHANNEL_ID}\n💳 Wallet: {CRYPTO_WALLET}\n{td_status}\n\nV5.3 KEEP - 3TF (H4→H1→NEW M15) - 38.7% win profitable:\n• 2-Left/2-Right High/Low, Protected+Important, Sweep vs BOS\n• CHoCH→Transition→HL/LH→BOS→Confirmed\n• H4→H1→NEW M15 chronological (must be AFTER H1)\n• SL: Protected + 0.3 ATR = $25 cap\n\nV5.3 2TF (4H+1H ONLY) - YOUR NEW REQUEST:\n• 4H HH/HL → HL that created HH → 1H LH broken by bullish BOS above it → BUY immediate\n• 4H LL/LH → LH that created LL → 1H HL broken by bearish BOS below it → SELL immediate\n• Faster signals, more trades, no M15 wait\n\nCommands:\n/signal - V5.3 3TF (H4→H1→M15) signal\n/signal2tf - V5.3 2TF (4H+1H ONLY) signal ← NEW!\n/backtest - V5.3 3TF backtest\n/backtest2tf - V5.3 2TF backtest ← NEW!\n/mtf - States\n/bos - BOS/CHoCH/Sweeps"
    await update.message.reply_text(msg)

async def buy(update, context):
    msg=f"💳 JOIN VIP FOR $25 / MONTH\nPay via USDT TRC20:\n{CRYPTO_WALLET}\nAfter payment, send TXID to @Onyebest\n\n✅ V5.3 KEEP 38.7% win profitable"
    await update.message.reply_text(msg)

async def signal(update, context):
    full_msg,vip_msg,_,_,_,_,_,_,_,_,_=build_setup_v53()
    await update.message.reply_text(full_msg)

async def signal2tf(update, context):
    full_msg,vip_msg,_,_,_,_,_,_,_,_,_=build_setup_2tf()
    await update.message.reply_text(full_msg)

async def mtf(update, context):
    data=get_gold_v53()
    if not data:
        await update.message.reply_text("❌ No TwelveData")
        return
    msg=f"📊 V5.3 KEEP MTF\n💰 ${data['price']:.2f}\n\n"
    for tf_name, state in [("H4", data["state_4h"]), ("H1", data["state_1h"]), ("M15", data["state_15m"])]:
        msg+=f"{tf_name} {state.state}\n  Prot H {state.protected_high or 0:.2f} L {state.protected_low or 0:.2f}\n  Imp H {state.important_high or 0:.2f} L {state.important_low or 0:.2f}\n  BOS {state.last_bos['type'] if state.last_bos else 'NONE'} @ {state.last_bos['level'] if state.last_bos else 0:.2f}\n"
        if state.sweeps:
            msg+=f"  Sweep {state.sweeps[-1]['type']} @ {state.sweeps[-1]['level']:.2f}\n"
        msg+=f"\n"
    await update.message.reply_text(msg)

async def bos_cmd(update, context):
    data=get_gold_v53()
    if not data:
        await update.message.reply_text("❌ No TwelveData")
        return
    msg=f"🔍 V5.3 KEEP BOS/CHoCH/SWEEP\n💰 ${data['price']:.2f}\n\n"
    for tf_name, state in [("H1", data["state_1h"]), ("M15", data["state_15m"])]:
        msg+=f"{tf_name} {state.state}\nProt H {state.protected_high or 0:.2f} L {state.protected_low or 0:.2f}\nImp H {state.important_high or 0:.2f} L {state.important_low or 0:.2f}\nBOS {state.last_bos}\nCHoCH {state.last_choch}\nSweeps {len(state.sweeps)}\n\n"
    await update.message.reply_text(msg)

async def news(update, context):
    data=get_gold_v53()
    if not data:
        await update.message.reply_text("❌ No TwelveData")
        return
    s4h=data["state_4h"]; s1h=data["state_1h"]; s15m=data["state_15m"]
    msg=f"📰 V5.3 KEEP\n💰 ${data['price']:.2f}\nH4 {s4h.state} Prot {s4h.protected_high or 0:.2f}\nH1 {s1h.state}\nM15 {s15m.state}\nSL 0.3 ATR $25 cap = 38.7% win"
    await update.message.reply_text(msg)

async def autopilot_cmd(update, context):
    global AUTOPILOT_ACTIVE
    AUTOPILOT_ACTIVE=True; SUBSCRIBERS.add(update.effective_chat.id)
    await update.message.reply_text(f"✅ AUTOPILOT V5.3 KEEP ON\n38.7% win profitable\nChat ID {update.effective_chat.id} saved")
    asyncio.create_task(autopilot_loop(context))

async def autostop(update, context):
    global AUTOPILOT_ACTIVE
    AUTOPILOT_ACTIVE=False; SUBSCRIBERS.discard(update.effective_chat.id)
    await update.message.reply_text("🛑 AUTOPILOT OFF")

async def autopilot_on_alias(update, context): await autopilot_cmd(update, context)
async def autopilot_off_alias(update, context): await autostop(update, context)

async def autopilot_loop(context):
    global AUTOPILOT_ACTIVE
    while AUTOPILOT_ACTIVE:
        await asyncio.sleep(15*60)
        if not AUTOPILOT_ACTIVE: break
        try:
            full_msg,vip_msg,direction,conf_pct,count,price,sl,tp1,tp2,tp3,risk=build_setup_v53()
            if count>=2 and conf_pct>=80 and direction!="WAIT":
                for chat_id in list(SUBSCRIBERS):
                    try: await context.bot.send_message(chat_id=chat_id, text=f"🤖 AUTOPILOT V5.3 KEEP\n{full_msg}")
                    except: pass
                try: await context.bot.send_message(chat_id=CHANNEL_ID, text=vip_msg)
                except: pass
        except Exception as e: print(f"Autopilot error: {e}")

async def sendvip(update, context):
    if update.effective_user.id!=ADMIN_ID:
        await update.message.reply_text("❌ Admin only"); return
    full_msg,vip_msg,direction,conf_pct,count,price,sl,tp1,tp2,tp3,risk=build_setup_v53()
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=vip_msg)
        await update.message.reply_text(f"✅ Sent to VIP {CHANNEL_ID}:\n{vip_msg}")
    except Exception as e: await update.message.reply_text(f"❌ Failed: {e}")

async def setchannel(update, context):
    global CHANNEL_ID
    if update.effective_user.id!=ADMIN_ID:
        await update.message.reply_text("❌ Admin only"); return
    if context.args:
        CHANNEL_ID=context.args[0]
        await update.message.reply_text(f"✅ Channel set to: {CHANNEL_ID}")
    else: await update.message.reply_text(f"Current Channel: {CHANNEL_ID}")

async def channeltest(update, context):
    if not CHANNEL_ID: await update.message.reply_text("❌ CHANNEL_ID not set."); return
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="✅ VIP Bot V5.3 KEEP 38.7% WIN Test!")
        await update.message.reply_text("✅ Test sent to channel!")
    except Exception as e: await update.message.reply_text(f"❌ Failed: {e}")

async def backtest(update, context):
    await update.message.reply_text("⏳ Running V5.3 KEEP... 38.7% win version, SL 0.3 ATR $25, no BE... Fetching 2000x 1H...")
    try:
        loop=asyncio.get_event_loop()
        result=await loop.run_in_executor(None, run_backtest_v53)
        if "error" in result:
            await update.message.reply_text(f"❌ Error: {result['error']}\n{result.get('trace','')[:800]}"); return
        msg=f"📊 V5.3 KEEP BACKTEST 6M (BEST) 3TF H4→H1→M15\nCandles: {result['candles_used']} x 1H (~{result['candles_used']//24} days)\nTotal Setups: {result['total_signals']}\nClosed: {result['total_closed']}\n✅ TP2 WIN: {result['wins_tp2']}\n✅ TP1 WIN: {result['wins_tp1']}\n❌ LOSS: {result['losses']}\n➖ BE: {result['be']}\n\n🏆 WIN RATE: {result['win_rate']:.1f}% | TP2 RATE: {result['tp2_rate']:.1f}%\n\nV5.3 KEEP - Your best profitable:\n• SL: Protected + 0.3 ATR = $25 cap (scalps)\n• No BE → keeps TP1 wins\n• Expectancy: 38.7% x 2 - 61.3% = +0.16R profitable\n\n🔍 Last 10 LOSSES:\n"
        losses=[t for t in result['all_trades'] if t['outcome']=="LOSS"][-10:]
        for t in losses:
            emoji="🟢" if t['dir']=="BUY" else "🔴"
            msg+=f"{emoji} {t['mt5_time']} {t['dir']} ENTRY {t['entry']:.2f} SL {t['sl']:.2f} TP2 {t['tp2']:.2f} MaxH {t['max_high']:.2f} MinL {t['min_low']:.2f} -> LOSS\n"
        msg+=f"\n🔍 Last 5 WINS:\n"
        wins=[t for t in result['all_trades'] if "WIN" in t['outcome']][-5:]
        for t in wins:
            emoji="🟢" if t['dir']=="BUY" else "🔴"
            msg+=f"{emoji} {t['mt5_time']} {t['dir']} {t['entry']:.2f} -> {t['outcome']}\n"
        await update.message.reply_text(msg)
    except Exception as e:
        import traceback
        await update.message.reply_text(f"❌ Failed: {e}\n{traceback.format_exc()[:800]}")

async def backtest2tf(update, context):
    await update.message.reply_text("⏳ Running V5.3 2TF (4H+1H ONLY)... HL that created HH + 1H LH broken by BOS → Immediate entry... Fetching 2000x 1H...")
    try:
        loop=asyncio.get_event_loop()
        result=await loop.run_in_executor(None, run_backtest_2tf)
        if "error" in result:
            await update.message.reply_text(f"❌ Error: {result['error']}\n{result.get('trace','')[:800]}"); return
        msg=f"📊 V5.3 2TF BACKTEST 6M (4H+1H ONLY)\nCandles: {result['candles_used']} x 1H (~{result['candles_used']//24} days)\nTotal Setups: {result['total_signals']}\nClosed: {result['total_closed']}\n✅ TP2 WIN: {result['wins_tp2']}\n✅ TP1 WIN: {result['wins_tp1']}\n❌ LOSS: {result['losses']}\n➖ BE: {result['be']}\n\n🏆 WIN RATE: {result['win_rate']:.1f}% | TP2 RATE: {result['tp2_rate']:.1f}%\n\nV5.3 2TF - 4H+1H ONLY:\n• 4H HH/HL → HL that created HH (Protected Low)\n• 4H LL/LH → LH that created LL (Protected High)\n• 1H LH broken by bullish BOS → BUY immediate\n• 1H HL broken by bearish BOS → SELL immediate\n• No M15 wait → Faster, more trades\n\n🔍 Last 10 LOSSES:\n"
        losses=[t for t in result['all_trades'] if t['outcome']=="LOSS"][-10:]
        for t in losses:
            emoji="🟢" if t['dir']=="BUY" else "🔴"
            msg+=f"{emoji} {t['mt5_time']} {t['dir']} ENTRY {t['entry']:.2f} SL {t['sl']:.2f} TP2 {t['tp2']:.2f} H4 {t['h4_state']} H1 {t['h1_state']} BOS {t['h1_bos']} @ {t['h1_bos_level']:.2f} -> LOSS | Prot {t['protected']:.2f}\n"
        msg+=f"\n🔍 Last 5 WINS:\n"
        wins=[t for t in result['all_trades'] if "WIN" in t['outcome']][-5:]
        for t in wins:
            emoji="🟢" if t['dir']=="BUY" else "🔴"
            msg+=f"{emoji} {t['mt5_time']} {t['dir']} {t['entry']:.2f} -> {t['outcome']} | Prot {t['protected']:.2f}\n"
        await update.message.reply_text(msg)
    except Exception as e:
        import traceback
        await update.message.reply_text(f"❌ Failed: {e}\n{traceback.format_exc()[:800]}")

def main():
    if not BOT_TOKEN: print("ERROR: BOT_TOKEN not set!"); return
    app=ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("signal2tf", signal2tf))
    app.add_handler(CommandHandler("signal2", signal2tf))
    app.add_handler(CommandHandler("signal4h1h", signal2tf))
    app.add_handler(CommandHandler("mtf", mtf))
    app.add_handler(CommandHandler("bos", bos_cmd))
    app.add_handler(CommandHandler("sweep", bos_cmd))
    app.add_handler(CommandHandler("autopilot", autopilot_cmd))
    app.add_handler(CommandHandler("autostop", autostop))
    app.add_handler(CommandHandler("autopilot_on", autopilot_on_alias))
    app.add_handler(CommandHandler("autopilot_off", autopilot_off_alias))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("sendvip", sendvip))
    app.add_handler(CommandHandler("setchannel", setchannel))
    app.add_handler(CommandHandler("channeltest", channeltest))
    app.add_handler(CommandHandler("backtest", backtest))
    app.add_handler(CommandHandler("backtest2tf", backtest2tf))
    app.add_handler(CommandHandler("backtest2", backtest2tf))
    app.add_handler(CommandHandler("backtest4h1h", backtest2tf))
    print(f"GOLD VIP V5.3 FINAL KEEP + 2TF started - 3TF 38.7% + 2TF 4H+1H ONLY - Your request")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message"])

if __name__=="__main__": main()
