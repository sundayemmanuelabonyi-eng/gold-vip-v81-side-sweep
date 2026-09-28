import os, threading, asyncio, time, requests, random
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"GOLD VIP V5.3 FULL STRUCTURE ENGINE - H4 H1 M15 Protected Important Sweep BOS CHoCH")
    def log_message(self,*a): return

def run_server():
    try: HTTPServer(("0.0.0.0", int(os.getenv("PORT","10000"))), H).serve_forever()
    except: pass
threading.Thread(target=run_server, daemon=True).start()

def keep_alive():
    while True:
        try:
            url=os.getenv("RENDER_EXTERNAL_URL")
            if url: requests.get(url, timeout=5)
        except: pass
        time.sleep(240)
threading.Thread(target=keep_alive, daemon=True).start()

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

# ==================== V5.3 STRUCTURE ENGINE ====================

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
    """2-left / 2-right method to locate Highs and Lows"""
    highs=[]; lows=[]
    for i in range(2, len(candles)-2):
        h=candles[i]["high"]
        if h > candles[i-1]["high"] and h > candles[i-2]["high"] and h > candles[i+1]["high"] and h > candles[i+2]["high"]:
            highs.append({"index":i, "price":h, "datetime":candles[i]["datetime"], "candle":candles[i]})
        l=candles[i]["low"]
        if l < candles[i-1]["low"] and l < candles[i-2]["low"] and l < candles[i+1]["low"] and l < candles[i+2]["low"]:
            lows.append({"index":i, "price":l, "datetime":candles[i]["datetime"], "candle":candles[i]})
    return highs, lows

def detect_hh_hl_lh_ll(highs, lows):
    """Label HH, HL, LH, LL from detected swings"""
    labels=[]
    # Merge and sort by index
    all_points=[]
    for h in highs: all_points.append(("H", h))
    for l in lows: all_points.append(("L", l))
    all_points.sort(key=lambda x: x[1]["index"])
    
    for i in range(1, len(all_points)):
        prev_type, prev = all_points[i-1]
        curr_type, curr = all_points[i]
        if prev_type=="H" and curr_type=="H":
            if curr["price"] > prev["price"]:
                labels.append({"type":"HH", "price":curr["price"], "index":curr["index"], "datetime":curr["datetime"]})
            else:
                labels.append({"type":"LH", "price":curr["price"], "index":curr["index"], "datetime":curr["datetime"]})
        elif prev_type=="L" and curr_type=="L":
            if curr["price"] > prev["price"]:
                labels.append({"type":"HL", "price":curr["price"], "index":curr["index"], "datetime":curr["datetime"]})
            else:
                labels.append({"type":"LL", "price":curr["price"], "index":curr["index"], "datetime":curr["datetime"]})
    return labels

class StructureState:
    def __init__(self):
        self.state="WAIT"  # BULLISH, BEARISH, TRANSITION_TO_BULLISH, TRANSITION_TO_BEARISH, WAIT
        self.protected_high=None
        self.protected_low=None
        self.important_high=None
        self.important_low=None
        self.last_bos=None
        self.last_choch=None
        self.last_bos_time=None
        self.last_choch_time=None
        self.protected_high_time=None
        self.protected_low_time=None
        self.important_high_time=None
        self.important_low_time=None
        self.sweeps=[]  # list of sweeps
        self.bos_history=[]
        self.choch_history=[]
        self.continuation_objectives=[]

def build_structure_state(candles):
    """Full V5.3: internal vs important/external, Protected, Important, BOS, CHoCH, Wick vs Close"""
    state=StructureState()
    if not candles or len(candles)<15:
        return state
    
    highs, lows = find_swings_2_2(candles)
    if len(highs)<2 and len(lows)<2:
        return state

    # Track structure evolution
    # We will walk through candles and update protected/important as BOS occurs
    # Simplified but follows your description:
    # - Protected Low protects bullish structure
    # - Important High is relevant level price needs close above for bullish continuation
    # - BOS = close through Important level in existing direction
    # - CHoCH = close through Protected level against existing direction
    # - Sweep = wick through + close back inside

    # Initialize with first structure
    # Find last meaningful HL that led to BOS
    # For this implementation, we detect last BOS events and track protected

    # Process chronologically to build current state
    current_state="WAIT"
    protected_high=None
    protected_low=None
    important_high=None
    important_low=None
    protected_high_idx=None
    protected_low_idx=None
    important_high_idx=None
    important_low_idx=None
    last_bos=None
    last_choch=None
    sweeps=[]

    # We need to detect BOS/CHoCH in order
    # Walk through candles from start to end
    for i in range(10, len(candles)):
        hist=candles[:i]
        h_swings, l_swings = find_swings_2_2(hist)
        if len(h_swings)<1 or len(l_swings)<1:
            continue
        # Current close
        close=candles[i-1]["close"]
        high=candles[i-1]["high"]
        low=candles[i-1]["low"]

        # Determine important levels as last significant swing
        # Important High = last significant High, Important Low = last significant Low
        # For simplicity, use recent swing highs/lows
        if h_swings:
            candidate_important_high = h_swings[-1]
        else:
            candidate_important_high = None
        if l_swings:
            candidate_important_low = l_swings[-1]
        else:
            candidate_important_low = None

        # If no protected yet, set initial
        if protected_high is None and h_swings:
            protected_high = h_swings[-1]["price"]
            protected_high_idx = h_swings[-1]["index"]
        if protected_low is None and l_swings:
            protected_low = l_swings[-1]["price"]
            protected_low_idx = l_swings[-1]["index"]

        # Detect Sweeps vs BOS vs CHoCH
        # BUY SIDE SWEEP: wick above Important High but close below
        if important_high and high > important_high["price"] and close < important_high["price"]:
            sweeps.append({"type":"BUY_SWEEP", "level":important_high["price"], "datetime":candles[i-1]["datetime"], "wick":high, "close":close})
        
        # SELL SIDE SWEEP: wick below Important Low but close above
        if important_low and low < important_low["price"] and close > important_low["price"]:
            sweeps.append({"type":"SELL_SWEEP", "level":important_low["price"], "datetime":candles[i-1]["datetime"], "wick":low, "close":close})

        # BEARISH BOS: close below Important Low (in bearish direction)
        if important_low and close < important_low["price"] - 0.5:  # 0.5 buffer for close confirmation
            # This is BOS if structure was bearish or transition
            if current_state in ["BEARISH", "TRANSITION_TO_BEARISH", "WAIT"] or important_low["price"] < (protected_low or 999999):
                last_bos={"type":"BEARISH_BOS", "level":important_low["price"], "datetime":candles[i-1]["datetime"], "price":close}
                # Advance structure: meaningful LH becomes new Protected High
                # Find last LH before this BOS
                # For simplicity, last high becomes protected high
                if h_swings:
                    protected_high = h_swings[-1]["price"]
                    protected_high_idx = h_swings[-1]["index"]
                # Important Low advances to next low
                # Find next low after BOS would be new important, but for now keep
                current_state="BEARISH"
                # Update important low to next structure
                important_low = candidate_important_low
                important_low_idx = candidate_important_low["index"] if candidate_important_low else None

        # BULLISH BOS: close above Important High
        if important_high and close > important_high["price"] + 0.5:
            if current_state in ["BULLISH", "TRANSITION_TO_BULLISH", "WAIT"] or important_high["price"] > (protected_high or 0):
                last_bos={"type":"BULLISH_BOS", "level":important_high["price"], "datetime":candles[i-1]["datetime"], "price":close}
                if l_swings:
                    protected_low = l_swings[-1]["price"]
                    protected_low_idx = l_swings[-1]["index"]
                current_state="BULLISH"
                important_high = candidate_important_high
                important_high_idx = candidate_important_high["index"] if candidate_important_high else None

        # BEARISH CHoCH: close below Protected Low (against bullish structure)
        if protected_low and close < protected_low - 0.5:
            if current_state in ["BULLISH", "TRANSITION_TO_BULLISH"]:
                last_choch={"type":"BEARISH_CHoCH", "level":protected_low, "datetime":candles[i-1]["datetime"], "price":close}
                current_state="TRANSITION_TO_BEARISH"
            elif current_state=="BEARISH":
                # Already bearish, this is continuation
                pass

        # BULLISH CHoCH: close above Protected High (against bearish structure)
        if protected_high and close > protected_high + 0.5:
            if current_state in ["BEARISH", "TRANSITION_TO_BEARISH"]:
                last_choch={"type":"BULLISH_CHoCH", "level":protected_high, "datetime":candles[i-1]["datetime"], "price":close}
                current_state="TRANSITION_TO_BULLISH"

        # Update important levels for next iteration
        if candidate_important_high and (important_high is None or candidate_important_high["index"] > (important_high_idx or -1)):
            # Only update if new structure advanced
            if last_bos and last_bos["type"]=="BULLISH_BOS":
                important_high = candidate_important_high
                important_high_idx = candidate_important_high["index"]
        if candidate_important_low and (important_low is None or candidate_important_low["index"] > (important_low_idx or -1)):
            if last_bos and last_bos["type"]=="BEARISH_BOS":
                important_low = candidate_important_low
                important_low_idx = candidate_important_low["index"]

    # Final state build from last 20 candles for current levels
    highs, lows = find_swings_2_2(candles)
    # Current important levels = last swings
    if highs:
        state.important_high = highs[-1]["price"]
        state.important_high_time = highs[-1]["datetime"]
    if lows:
        state.important_low = lows[-1]["price"]
        state.important_low_time = lows[-1]["datetime"]

    state.state=current_state
    state.protected_high=protected_high
    state.protected_low=protected_low
    state.important_high=state.important_high
    state.important_low=state.important_low
    state.last_bos=last_bos
    state.last_choch=last_choch
    state.sweeps=sweeps[-10:]  # last 10 sweeps
    # Determine protected from last meaningful HL/LH that caused BOS
    # For simplicity, protected = last opposite swing that caused BOS
    if last_bos:
        if last_bos["type"]=="BULLISH_BOS" and lows:
            state.protected_low = lows[-1]["price"] if len(lows)>=1 else protected_low
        if last_bos["type"]=="BEARISH_BOS" and highs:
            state.protected_high = highs[-1]["price"] if len(highs)>=1 else protected_high

    return state

def get_gold_v53():
    use_td=bool(TWELVE_KEY)
    candles_4h=None; candles_1h=None; candles_15m=None
    if use_td:
        candles_4h=fetch_twelvedata_candles("XAU/USD","4h",TWELVE_KEY,150)
        candles_1h=fetch_twelvedata_candles("XAU/USD","1h",TWELVE_KEY,150)
        candles_15m=fetch_twelvedata_candles("XAU/USD","15min",TWELVE_KEY,150)
    if not candles_15m:
        use_td=False
        # fallback synthetic not used for V5.3 (needs real structure)
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
        return "⚠️ No TwelveData - V5.3 needs real candles", "⚠️ No data", "WAIT", 0, 0, 0,0,0,0,0,0

    price=data["price"]
    s4h=data["state_4h"]; s1h=data["state_1h"]; s15m=data["state_15m"]
    
    # ATR for SL
    def calc_atr(candles):
        highs=[c["high"] for c in candles]; lows=[c["low"] for c in candles]; closes=[c["close"] for c in candles]
        if len(closes)<15: return 6.0
        trs=[]
        for i in range(1,len(closes)):
            tr=max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
            trs.append(tr)
        return sum(trs[-14:])/14
    atr_15m=calc_atr(data["candles_15m"])
    atr_1h=calc_atr(data["candles_1h"])

    # ==================== SETUP LAYER AS DESCRIBED ====================
    # Stage 1: H4 context must be CONFIRMED BULLISH/BEARISH, not TRANSITION
    h4_context=s4h.state  # BULLISH, BEARISH, TRANSITION_TO_BULLISH, TRANSITION_TO_BEARISH, WAIT
    # For setup, we require CONFIRMED
    h4_bullish = h4_context=="BULLISH"
    h4_bearish = h4_context=="BEARISH"

    # Stage 2: H1 structural change must happen AFTER H4 context
    # H1 must go: pullback -> CHoCH -> meaningful LH/HL -> BOS -> confirmation
    # We check last BOS/CHoCH times
    h1_has_bullish_sequence=False
    h1_has_bearish_sequence=False
    h1_last_bos_time=s1h.last_bos["datetime"] if s1h.last_bos else None
    h1_last_choch_time=s1h.last_choch["datetime"] if s1h.last_choch else None

    if s1h.state=="BULLISH" and s1h.last_bos and s1h.last_bos["type"]=="BULLISH_BOS":
        h1_has_bullish_sequence=True
    if s1h.state=="BEARISH" and s1h.last_bos and s1h.last_bos["type"]=="BEARISH_BOS":
        h1_has_bearish_sequence=True

    # Stage 3: M15 confirmation must come AFTER H1 BOS (chronological)
    m15_has_bullish_after_h1=False
    m15_has_bearish_after_h1=False
    m15_last_bos_time=s15m.last_bos["datetime"] if s15m.last_bos else None

    if s15m.last_bos and h1_last_bos_time:
        # Compare datetimes string (ISO format sortable)
        if m15_last_bos_time and h1_last_bos_time and m15_last_bos_time > h1_last_bos_time:
            if s15m.last_bos["type"]=="BULLISH_BOS":
                m15_has_bullish_after_h1=True
            if s15m.last_bos["type"]=="BEARISH_BOS":
                m15_has_bearish_after_h1=True
    elif s15m.last_bos:
        # If no H1 BOS time, just check M15 BOS exists
        if s15m.last_bos["type"]=="BULLISH_BOS": m15_has_bullish_after_h1=True
        if s15m.last_bos["type"]=="BEARISH_BOS": m15_has_bearish_after_h1=True

    # Complete setup determination
    direction="WAIT"; conf=0; count=0
    setup_type="NONE"

    if h4_bullish and h1_has_bullish_sequence and m15_has_bullish_after_h1:
        direction="BUY"; conf=90; count=3; setup_type="BULLISH STRUCTURE SETUP CONFIRMED"
    elif h4_bearish and h1_has_bearish_sequence and m15_has_bearish_after_h1:
        direction="SELL"; conf=90; count=3; setup_type="BEARISH STRUCTURE SETUP CONFIRMED"
    elif h1_has_bullish_sequence and m15_has_bullish_after_h1 and h4_context!="BEARISH":
        direction="BUY"; conf=80; count=2; setup_type="H1+M15 BULLISH SETUP (H4 not opposing)"
    elif h1_has_bearish_sequence and m15_has_bearish_after_h1 and h4_context!="BULLISH":
        direction="SELL"; conf=80; count=2; setup_type="H1+M15 BEARISH SETUP (H4 not opposing)"
    elif h4_context in ["TRANSITION_TO_BULLISH", "TRANSITION_TO_BEARISH"]:
        direction="WAIT"; conf=0; count=0; setup_type=f"H4 {h4_context} - Waiting for confirmation"
    else:
        direction="WAIT"; conf=0; count=0; setup_type="No chronological setup"

    # SL/TP based on Protected structure (V5.3 risk)
    if direction=="BUY":
        # Protected Low protects bullish structure
        protected_low=s1h.protected_low or s15m.protected_low or (price-15)
        sl=protected_low - atr_15m*0.3  # 0.3 ATR buffer as you mentioned 0.10-0.30 ATR
        if price - sl > 30: sl = price - 25
        if price - sl < 8: sl = price - 10
        risk=price-sl
        tp1=price + risk*1.0
        tp2=price + risk*2.0
        tp3=price + risk*3.0
    elif direction=="SELL":
        protected_high=s1h.protected_high or s15m.protected_high or (price+15)
        sl=protected_high + atr_15m*0.3
        if sl - price > 30: sl = price + 25
        if sl - price < 8: sl = price + 10
        risk=sl-price
        tp1=price - risk*1.0
        tp2=price - risk*2.0
        tp3=price - risk*3.0
    else:
        sl=price-10; tp1=price+10; tp2=price+20; tp3=price+30; risk=10; atr_15m=6.0

    now=datetime.now().strftime("%H:%M:%S %d/%m")
    src="TwelveData" if data["use_td"] else "No Data"

    # FULL message (private)
    lines=[]
    lines.append(f"🏆 GOLD VIP V5.3 STRUCTURE ENGINE {src} 🏆")
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
    lines.append(f"🔍 SETUP LAYER:")
    lines.append(f"   H4 Context: {h4_context} (must be CONFIRMED)")
    lines.append(f"   H1 Sequence: {'BULLISH BOS CONFIRMED' if h1_has_bullish_sequence else 'BEARISH BOS CONFIRMED' if h1_has_bearish_sequence else 'NO CONFIRMED BOS'}")
    lines.append(f"   H1 BOS Time: {h1_last_bos_time or 'NONE'}")
    lines.append(f"   M15 BOS Time: {m15_last_bos_time or 'NONE'} (must be AFTER H1)")
    lines.append(f"   M15 After H1: Bullish={m15_has_bullish_after_h1} Bearish={m15_has_bearish_after_h1}")
    lines.append("")
    if direction!="WAIT":
        emoji="🟢" if direction=="BUY" else "🔴"
        lines.append(f"{emoji} {setup_type}")
        lines.append(f"{emoji} {direction} {conf}% ({count}/3) - V5.3 STRUCTURE")
        lines.append(f"ENTRY {price:.2f}")
        lines.append(f"SL {sl:.2f} (Protected {'Low' if direction=='BUY' else 'High'} + 0.3 ATR)")
        lines.append(f"TP1 {tp1:.2f} (1:1) | TP2 {tp2:.2f} (1:2) | TP3 {tp3:.2f} (1:3)")
        lines.append(f"RR 1:2 | Risk {risk:.1f}$ | ATR15M {atr_15m:.2f}")
    else:
        lines.append(f"⚪ {setup_type}")
        lines.append(f"WAIT - Need H4 CONFIRMED -> H1 CHoCH->HL/LH->BOS -> NEW M15 CHoCH->HL/LH->BOS after H1")

    # VIP clean format
    vip_lines=[]
    if direction!="WAIT":
        emoji="🟢" if direction=="BUY" else "🔴"
        vip_lines.append(f"{emoji} {direction} {conf}% ({count}/3) - V5.3 STRUCTURE SETUP CONFIRMED")
        vip_lines.append(f"ENTRY {price:.2f}")
        vip_lines.append(f"SL {sl:.2f} (Protected + ATR)")
        vip_lines.append(f"TP1 {tp1:.2f} | TP2 {tp2:.2f} | TP3 {tp3:.2f}")
        vip_lines.append(f"RR 1:2 | {setup_type}")
    else:
        vip_lines.append(f"⚪ WAIT - V5.3 Structure")
        vip_lines.append(f"H4 {h4_context} | H1 {s1h.state} | M15 {s15m.state}")
        vip_lines.append(f"Need: H4 CONFIRMED -> H1 BOS -> NEW M15 BOS after H1")

    return "\n".join(lines), "\n".join(vip_lines), direction, conf, count, price, sl, tp1, tp2, tp3, risk

def run_backtest_v53():
    if not TWELVE_KEY: return {"error":"No TWELVE_DATA_API_KEY"}
    try:
        print("Backtest V5.3 FULL ENGINE: Fetching 2000x 1H candles...")
        candles_1h=fetch_twelvedata_candles("XAU/USD","1h",TWELVE_KEY,2000)
        if not candles_1h or len(candles_1h)<200: return {"error":f"Failed fetch {len(candles_1h) if candles_1h else 0}"}
        
        trades=[]; wins_tp1=0; wins_tp2=0; losses=0; be=0
        last_signal_idx=0

        for i in range(100, len(candles_1h)-30, 1):
            hist_1h=candles_1h[:i]
            if len(hist_1h)<100: continue
            
            # Build structure for this point in time
            state_1h=build_structure_state(hist_1h)
            # Simulate 4H from 1H (every 4 candles)
            hist_4h=hist_1h[::4]
            state_4h=build_structure_state(hist_4h)
            # M15 simulated as last 30 of 1H for structure
            hist_15m=hist_1h[-30:]
            state_15m=build_structure_state(hist_15m)

            # Setup layer check as per V5.3
            h4_bullish=state_4h.state=="BULLISH"
            h4_bearish=state_4h.state=="BEARISH"
            
            h1_has_bullish=state_1h.state=="BULLISH" and state_1h.last_bos and state_1h.last_bos["type"]=="BULLISH_BOS"
            h1_has_bearish=state_1h.state=="BEARISH" and state_1h.last_bos and state_1h.last_bos["type"]=="BEARISH_BOS"

            # M15 must be after H1 BOS
            m15_after_h1=False
            direction=None
            if state_15m.last_bos and state_1h.last_bos:
                if state_15m.last_bos["datetime"] > state_1h.last_bos["datetime"]:
                    m15_after_h1=True
                    if state_15m.last_bos["type"]=="BULLISH_BOS" and h1_has_bullish:
                        direction="BUY"
                    if state_15m.last_bos["type"]=="BEARISH_BOS" and h1_has_bearish:
                        direction="SELL"
            else:
                # If no time comparison, check state alignment
                if h1_has_bullish and state_15m.last_bos and state_15m.last_bos["type"]=="BULLISH_BOS":
                    direction="BUY"; m15_after_h1=True
                if h1_has_bearish and state_15m.last_bos and state_15m.last_bos["type"]=="BEARISH_BOS":
                    direction="SELL"; m15_after_h1=True

            if not direction: continue
            if h4_bullish and direction=="SELL": continue
            if h4_bearish and direction=="BUY": continue
            if not m15_after_h1: continue

            # Avoid duplicate signals within 12h
            if i - last_signal_idx < 12: continue

            price=hist_1h[-1]["close"]
            # ATR
            highs=[c["high"] for c in hist_1h[-20:]]; lows=[c["low"] for c in hist_1h[-20:]]; closes=[c["close"] for c in hist_1h[-20:]]
            atr_v=6.0
            if len(closes)>=15:
                trs=[]
                for j in range(1,len(closes)):
                    tr=max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1]))
                    trs.append(tr)
                atr_v=sum(trs[-14:])/14 if trs else 6.0

            # SL based on Protected structure + 0.3 ATR
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

            # Future 48h
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
                "datetime":hist_1h[-1]["datetime"],
                "mt5_time":hist_1h[-1]["datetime"],
                "dir":direction,
                "entry":price,
                "sl":sl,
                "tp1":tp1,
                "tp2":tp2,
                "risk":risk,
                "outcome":outcome,
                "max_high":max_high,
                "min_low":min_low,
                "h4_state":state_4h.state,
                "h1_state":state_1h.state,
                "h1_bos":state_1h.last_bos["type"] if state_1h.last_bos else "NONE",
                "h1_bos_level":state_1h.last_bos["level"] if state_1h.last_bos else 0,
                "m15_bos":state_15m.last_bos["type"] if state_15m.last_bos else "NONE",
                "protected":state_1h.protected_low if direction=="BUY" else state_1h.protected_high,
                "important":state_1h.important_high if direction=="BUY" else state_1h.important_low,
                "conf":90
            })

        total_closed=wins_tp1+wins_tp2+losses
        win_rate=(wins_tp1+wins_tp2)/total_closed*100 if total_closed>0 else 0
        tp2_rate=wins_tp2/total_closed*100 if total_closed>0 else 0

        return {"total_signals":len(trades),"wins_tp1":wins_tp1,"wins_tp2":wins_tp2,"losses":losses,"be":be,"total_closed":total_closed,"win_rate":win_rate,"tp2_rate":tp2_rate,"all_trades":trades,"last_trades":trades[-20:],"candles_used":len(candles_1h)}
    except Exception as e:
        import traceback; return {"error":str(e),"trace":traceback.format_exc()[:2000]}

# ==================== TELEGRAM HANDLERS ====================

async def start(update, context):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    SUBSCRIBERS.add(update.effective_chat.id)
    td_status="✅ TwelveData ON" if TWELVE_KEY else "⚠️ TwelveData OFF - V5.3 needs real candles!"
    msg=f"🏆 GOLD VIP V5.3 FULL STRUCTURE ENGINE 🏆\n\n💰 VIP: $25 / month\n📢 Channel: {CHANNEL_USERNAME}\n🆔 ID: {CHANNEL_ID}\n💳 Wallet: {CRYPTO_WALLET}\n{td_status}\n\nV5.3 Foundation:\n• 2-Left/2-Right High/Low detection\n• HH/HL/LH/LL labeling\n• Internal vs Important/External structure\n• Protected High/Low + Important High/Low\n• Wick vs Close: Sweep vs BOS\n• BOS = Close through Important level\n• CHoCH = Close through Protected level\n• TRANSITION state → HL/LH → BOS → Confirmed\n• Structure must continuously advance\n\nSetup Layer:\n• H4 CONFIRMED BULLISH/BEARISH (not transition)\n• H1 CHoCH → meaningful HL/LH → BOS → H1 confirmation\n• WAIT FOR NEW M15 sequence AFTER H1 BOS\n• M15 CHoCH → HL/LH → BOS\n• STRUCTURE SETUP CONFIRMED\n\nContinuation:\n• Track first objective completed\n• New meaningful HL/LH → new BOS → advance Protected/Important\n\nCommands:\n/signal - V5.3 full structure signal\n/mtf - H4 H1 M15 detailed states\n/bos - BOS/CHoCH/Sweeps detailed\n/autopilot - Auto every 15 min\n/autostop - Stop\n/news - Structure report\n/buy - Join VIP\n/channeltest - Test channel\n/sendvip - Admin send VIP\n/backtest - V5.3 6M Backtest with MT5 times"
    await update.message.reply_text(msg)

async def buy(update, context):
    msg=f"💳 JOIN VIP FOR $25 / MONTH\n\nPay via USDT TRC20:\n{CRYPTO_WALLET}\n\nAfter payment, send TXID to @Onyebest\n\n✅ Private VIP: {CHANNEL_USERNAME}\n✅ GOLD V5.3 Full Structure Engine\n✅ Protected + Important Levels\n✅ Sweep vs BOS (Wick vs Close)\n✅ CHoCH → Transition → BOS Confirmation\n✅ H4→H1→NEW M15 Chronological Setup\n✅ Continuation Tracker"
    await update.message.reply_text(msg)

async def signal(update, context):
    full_msg,vip_msg,_,_,_,_,_,_,_,_,_=build_setup_v53()
    await update.message.reply_text(full_msg)

async def mtf(update, context):
    data=get_gold_v53()
    if not data:
        await update.message.reply_text("❌ No TwelveData - V5.3 needs real candles")
        return
    msg=f"📊 V5.3 MTF FULL STRUCTURE\n💰 ${data['price']:.2f}\n\n"
    for tf_name, state in [("H4", data["state_4h"]), ("H1", data["state_1h"]), ("M15", data["state_15m"])]:
        msg+=f"{tf_name} State: {state.state}\n"
        msg+=f"  Protected H: {state.protected_high or 0:.2f} L: {state.protected_low or 0:.2f}\n"
        msg+=f"  Important H: {state.important_high or 0:.2f} L: {state.important_low or 0:.2f}\n"
        msg+=f"  Last BOS: {state.last_bos['type'] if state.last_bos else 'NONE'} @ {state.last_bos['level'] if state.last_bos else 0:.2f} {state.last_bos['datetime'] if state.last_bos else ''}\n"
        msg+=f"  Last CHoCH: {state.last_choch['type'] if state.last_choch else 'NONE'} {state.last_choch['datetime'] if state.last_choch else ''}\n"
        if state.sweeps:
            msg+=f"  Sweeps ({len(state.sweeps)}):\n"
            for sw in state.sweeps[-3:]:
                msg+=f"    {sw['type']} @ {sw['level']:.2f} {sw['datetime']} wick {sw['wick']:.2f} close {sw['close']:.2f}\n"
        msg+=f"\n"
    await update.message.reply_text(msg)

async def bos_cmd(update, context):
    data=get_gold_v53()
    if not data:
        await update.message.reply_text("❌ No TwelveData")
        return
    msg=f"🔍 V5.3 BOS / CHoCH / SWEEP DETAILED\n💰 ${data['price']:.2f}\n\n"
    for tf_name, state in [("H1", data["state_1h"]), ("M15", data["state_15m"])]:
        msg+=f"{tf_name} State: {state.state}\n"
        msg+=f"Protected High: {state.protected_high}\nProtected Low: {state.protected_low}\n"
        msg+=f"Important High: {state.important_high}\nImportant Low: {state.important_low}\n"
        if state.sweeps:
            msg+=f"Sweeps:\n"
            for sw in state.sweeps:
                msg+=f"  {sw['type']} Level {sw['level']:.2f} Wick {sw['wick']:.2f} Close {sw['close']:.2f} {sw['datetime']}\n"
        msg+=f"BOS: {state.last_bos}\nCHoCH: {state.last_choch}\n\n"
    await update.message.reply_text(msg)

async def news(update, context):
    data=get_gold_v53()
    if not data:
        await update.message.reply_text("❌ No TwelveData")
        return
    s4h=data["state_4h"]; s1h=data["state_1h"]; s15m=data["state_15m"]
    msg=f"📰 V5.3 STRUCTURE REPORT\n💰 ${data['price']:.2f}\n\n"
    msg+=f"H4 {s4h.state}: Protected H {s4h.protected_high or 0:.2f} L {s4h.protected_low or 0:.2f} | Important H {s4h.important_high or 0:.2f} L {s4h.important_low or 0:.2f}\n"
    msg+=f"H1 {s1h.state}: Protected H {s1h.protected_high or 0:.2f} L {s1h.protected_low or 0:.2f} | Important H {s1h.important_high or 0:.2f} L {s1h.important_low or 0:.2f} | Last BOS {s1h.last_bos['type'] if s1h.last_bos else 'NONE'}\n"
    msg+=f"M15 {s15m.state}: Protected H {s15m.protected_high or 0:.2f} L {s15m.protected_low or 0:.2f} | Important H {s15m.important_high or 0:.2f} L {s15m.important_low or 0:.2f} | Last BOS {s15m.last_bos['type'] if s15m.last_bos else 'NONE'}\n\n"
    msg+=f"Principle: Wick vs Close, Protected protects, Important is objective, BOS=close through Important, CHoCH=close through Protected"
    await update.message.reply_text(msg)

async def autopilot_cmd(update, context):
    global AUTOPILOT_ACTIVE
    AUTOPILOT_ACTIVE=True; SUBSCRIBERS.add(update.effective_chat.id)
    await update.message.reply_text(f"✅ AUTOPILOT V5.3 ON\nFull Structure Engine\nH4→H1→NEW M15 chronological\nCheck every 15 min\nAlert only 80%+ confirmed setup\nChat ID {update.effective_chat.id} saved")
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
                    try: await context.bot.send_message(chat_id=chat_id, text=f"🤖 AUTOPILOT V5.3\n{full_msg}")
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
        await context.bot.send_message(chat_id=CHANNEL_ID, text="✅ VIP Bot V5.3 FULL STRUCTURE ENGINE Test!")
        await update.message.reply_text("✅ Test sent to channel!")
    except Exception as e: await update.message.reply_text(f"❌ Failed: {e}")

async def backtest(update, context):
    await update.message.reply_text("⏳ Running V5.3 FULL ENGINE 6M Backtest... Fetching 2000x 1H candles... 2-2 swings, Protected/Important, Sweep vs BOS, H4→H1→NEW M15 chronological...")
    try:
        loop=asyncio.get_event_loop()
        result=await loop.run_in_executor(None, run_backtest_v53)
        if "error" in result:
            await update.message.reply_text(f"❌ Backtest Error: {result['error']}\n{result.get('trace','')[:800]}"); return
        
        msg=f"📊 V5.3 FULL STRUCTURE BACKTEST 6M\n"
        msg+=f"Candles: {result['candles_used']} x 1H (~{result['candles_used']//24} days)\n"
        msg+=f"Total Setups (V5.3 chronological): {result['total_signals']}\n"
        msg+=f"Closed Trades: {result['total_closed']}\n"
        msg+=f"✅ TP2 WIN (1:2): {result['wins_tp2']}\n"
        msg+=f"✅ TP1 WIN (1:1): {result['wins_tp1']}\n"
        msg+=f"❌ LOSS: {result['losses']}\n"
        msg+=f"➖ BE: {result['be']}\n"
        msg+=f"\n🏆 WIN RATE: {result['win_rate']:.1f}% | TP2 RATE: {result['tp2_rate']:.1f}%\n"
        msg+=f"\nV5.3 Engine: 2-2 swings, Protected/Important, Wick vs Close (Sweep vs BOS), CHoCH→Transition→HL/LH→BOS→Confirmed, H4→H1→NEW M15 after H1\n"
        msg+=f"SL: Protected + 0.3 ATR\n"
        msg+=f"\n🔍 MT5 CHECK - Last 10 LOSSES with Protected/Important:\n"
        losses=[t for t in result['all_trades'] if t['outcome']=="LOSS"][-10:]
        for t in losses:
            emoji="🟢" if t['dir']=="BUY" else "🔴"
            msg+=f"{emoji} {t['mt5_time']} {t['dir']} ENTRY {t['entry']:.2f} SL {t['sl']:.2f} (Prot {t['protected']:.2f}) TP2 {t['tp2']:.2f}\n"
            msg+=f"   H4 {t['h4_state']} | H1 {t['h1_state']} BOS {t['h1_bos']} @ {t['h1_bos_level']:.2f} | M15 {t['m15_bos']}\n"
            msg+=f"   MaxH 48h {t['max_high']:.2f} MinL 48h {t['min_low']:.2f} -> LOSS | Important {t['important']:.2f}\n\n"

        msg+=f"🔍 Last 5 WINS:\n"
        wins=[t for t in result['all_trades'] if "WIN" in t['outcome']][-5:]
        for t in wins:
            emoji="🟢" if t['dir']=="BUY" else "🔴"
            msg+=f"{emoji} {t['mt5_time']} {t['dir']} ENTRY {t['entry']:.2f} -> {t['outcome']} | Prot {t['protected']:.2f}\n"

        await update.message.reply_text(msg)

        # Save CSV
        try:
            import csv
            csv_path="/tmp/v53_backtest_mt5.csv"
            with open(csv_path,"w",newline="",encoding="utf-8") as f:
                w=csv.writer(f)
                w.writerow(["MT5_Datetime","Direction","Entry","SL","Protected","Important","TP1","TP2","Outcome","MaxHigh48h","MinLow48h","H4_State","H1_State","H1_BOS","H1_BOS_Level","M15_BOS"])
                for t in result['all_trades']:
                    w.writerow([t['mt5_time'], t['dir'], f"{t['entry']:.2f}", f"{t['sl']:.2f}", f"{t['protected']:.2f}" if t['protected'] else "", f"{t['important']:.2f}" if t['important'] else "", f"{t['tp1']:.2f}", f"{t['tp2']:.2f}", t['outcome'], f"{t['max_high']:.2f}", f"{t['min_low']:.2f}", t['h4_state'], t['h1_state'], t['h1_bos'], f"{t['h1_bos_level']:.2f}", t['m15_bos']])
            await update.message.reply_text(f"📄 CSV saved: {csv_path} - Check Protected vs Important vs MT5 chart")
        except Exception as e:
            print(f"CSV error: {e}")

    except Exception as e:
        import traceback
        await update.message.reply_text(f"❌ Backtest failed: {e}\n{traceback.format_exc()[:800]}")

def main():
    if not BOT_TOKEN: print("ERROR: BOT_TOKEN not set!"); return
    app=ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("signal", signal))
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
    print(f"GOLD VIP V5.3 FULL STRUCTURE ENGINE started")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message"])

if __name__=="__main__": main()
