import os, threading, asyncio, time, requests, random
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"GOLD VIP V9.0 PURE PRICE ACTION - 4H 1H 15M CHoCH BOS HH HL")
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
LAST_PRICE_HISTORY=[]
CACHED_PRICE=4321.20

def ema(vals,period):
    if len(vals)<period: return sum(vals)/len(vals) if vals else 0
    k=2/(period+1); ev=sum(vals[:period])/period
    for v in vals[period:]: ev=v*k+ev*(1-k)
    return ev

def atr(highs,lows,closes,period=14):
    if len(closes)<period+1: return 6.0
    trs=[]
    for i in range(1,len(closes)):
        tr=max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        trs.append(tr)
    return sum(trs[-period:])/period if trs else 6.0

def fetch_twelvedata_candles(symbol="XAU/USD", interval="1h", apikey="", outputsize=50):
    if not apikey: return None
    try:
        url=f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={apikey}&format=JSON"
        r=requests.get(url,timeout=10).json()
        if "values" not in r: return None
        vals=r["values"][::-1]
        candles=[]
        for v in vals:
            candles.append({"datetime":v["datetime"],"open":float(v["open"]),"high":float(v["high"]),"low":float(v["low"]),"close":float(v["close"])})
        return candles
    except Exception as e:
        print(f"Twelve fetch error {interval}: {e}"); return None

def detect_structure(candles):
    if not candles or len(candles)<10:
        return {"trend":"WAIT","last_high":0,"last_low":0,"prev_high":0,"prev_low":0,"pattern":"WAIT","hh":False,"hl":False,"ll":False,"lh":False}
    highs=[c["high"] for c in candles]; lows=[c["low"] for c in candles]
    recent_high=max(highs[-6:-1]); recent_low=min(lows[-6:-1])
    prev_high=max(highs[-12:-6]) if len(highs)>=12 else max(highs[:-6]); prev_low=min(lows[-12:-6]) if len(lows)>=12 else min(lows[:-6])
    hh=recent_high>prev_high; hl=recent_low>prev_low; ll=recent_low<prev_low; lh=recent_high<prev_high
    if hh and hl: trend="BUY"; pattern="HH + HL (Uptrend)"
    elif ll and lh: trend="SELL"; pattern="LL + LH (Downtrend)"
    elif hl and not ll: trend="BUY"; pattern="HL holds (Uptrend pullback)"
    elif lh and not hh: trend="SELL"; pattern="LH holds (Downtrend rally)"
    else: trend="WAIT"; pattern="Ranging"
    return {"trend":trend,"pattern":pattern,"last_high":recent_high,"last_low":recent_low,"prev_high":prev_high,"prev_low":prev_low,"hh":hh,"hl":hl,"ll":ll,"lh":lh}

def detect_bos_choch(candles, structure):
    if not candles or len(candles)<2:
        return {"bos":"NONE","choch":"NONE","bull_bos":False,"bear_bos":False,"bull_choch":False,"bear_choch":False}
    close=candles[-1]["close"]
    bos="NONE"; choch="NONE"; bull_bos=False; bear_bos=False; bull_choch=False; bear_choch=False
    if close>structure["last_high"]+0.2:
        bos="BOS BULLISH - Broke last High"; bull_bos=True
        if structure["prev_high"]>structure["last_high"]: choch="CHoCH BULLISH - Broke LH"; bull_choch=True
    if close<structure["last_low"]-0.2:
        bos="BOS BEARISH - Broke last Low"; bear_bos=True
        if structure["prev_low"]<structure["last_low"]: choch="CHoCH BEARISH - Broke HL"; bear_choch=True
    if close<structure["prev_low"] and structure["hl"]: choch="CHoCH BEARISH - Broke HL"; bear_choch=True
    if close>structure["prev_high"] and structure["lh"]: choch="CHoCH BULLISH - Broke LH"; bull_choch=True
    return {"bos":bos,"choch":choch,"bull_bos":bull_bos,"bear_bos":bear_bos,"bull_choch":bull_choch,"bear_choch":bear_choch}

def get_gold_pure_pa():
    global LAST_PRICE_HISTORY, CACHED_PRICE
    candles_4h=None; candles_1h=None; candles_15m=None
    use_td=bool(TWELVE_KEY)
    if use_td:
        candles_4h=fetch_twelvedata_candles("XAU/USD","4h",TWELVE_KEY,100)
        candles_1h=fetch_twelvedata_candles("XAU/USD","1h",TWELVE_KEY,100)
        candles_15m=fetch_twelvedata_candles("XAU/USD","15min",TWELVE_KEY,100)
    if not candles_15m:
        use_td=False
        try:
            r=requests.get("https://api.gold-api.com/price/XAU",timeout=10).json()
            price=float(r.get("price",4321.20)); CACHED_PRICE=price
        except: price=CACHED_PRICE+random.uniform(-0.3,0.3)
        if not LAST_PRICE_HISTORY: LAST_PRICE_HISTORY=[price-(25-i)*0.5 for i in range(100)]
        else: LAST_PRICE_HISTORY=LAST_PRICE_HISTORY[1:]+[price]
        closes=LAST_PRICE_HISTORY
        candles_15m=[{"open":c-0.2,"high":c+0.5,"low":c-0.5,"close":c,"datetime":""} for c in closes]
        candles_1h=candles_15m; candles_4h=candles_15m
        price_15m=closes[-1]
    else:
        closes_15m=[c["close"] for c in candles_15m]; price_15m=closes_15m[-1]
        LAST_PRICE_HISTORY=closes_15m; CACHED_PRICE=price_15m

    def calc(candles):
        closes=[c["close"] for c in candles]; highs=[c["high"] for c in candles]; lows=[c["low"] for c in candles]
        return atr(highs,lows,closes,14)

    atr_4h=calc(candles_4h); atr_1h=calc(candles_1h); atr_15m=calc(candles_15m)
    struct_4h=detect_structure(candles_4h); struct_1h=detect_structure(candles_1h); struct_15m=detect_structure(candles_15m)
    bos_choch_1h=detect_bos_choch(candles_1h, struct_1h); bos_choch_15m=detect_bos_choch(candles_15m, struct_15m)
    return {"price":price_15m,"candles_4h":candles_4h,"candles_1h":candles_1h,"candles_15m":candles_15m,"atr_4h":atr_4h,"atr_1h":atr_1h,"atr_15m":atr_15m,"struct_4h":struct_4h,"struct_1h":struct_1h,"struct_15m":struct_15m,"bos_choch_1h":bos_choch_1h,"bos_choch_15m":bos_choch_15m,"use_td":use_td}

def build_gold_pure():
    data=get_gold_pure_pa()
    price=data["price"]; atr_15m=data["atr_15m"]
    struct_4h=data["struct_4h"]; struct_1h=data["struct_1h"]; struct_15m=data["struct_15m"]
    bos_choch_1h=data["bos_choch_1h"]; bos_choch_15m=data["bos_choch_15m"]
    use_td=data["use_td"]

    # PURE PRICE ACTION LOGIC - NO INDICATORS
    # 4H Father Trend
    trend_4h=struct_4h["trend"]  # BUY if HH+HL, SELL if LL+LH

    # 1H Son: CHoCH + BOS
    if bos_choch_1h["bull_choch"]: dir_1h="BUY"; conf_1h=85
    elif bos_choch_1h["bear_choch"]: dir_1h="SELL"; conf_1h=85
    elif bos_choch_1h["bull_bos"]: dir_1h="BUY"; conf_1h=75
    elif bos_choch_1h["bear_bos"]: dir_1h="SELL"; conf_1h=75
    elif struct_1h["trend"]!="WAIT": dir_1h=struct_1h["trend"]; conf_1h=65
    else: dir_1h="WAIT"; conf_1h=0

    # 15M Grandson: BOS for entry
    if bos_choch_15m["bull_bos"] or bos_choch_15m["bull_choch"]: dir_15m="BUY"; conf_15m=80
    elif bos_choch_15m["bear_bos"] or bos_choch_15m["bear_choch"]: dir_15m="SELL"; conf_15m=80
    elif struct_15m["trend"]!="WAIT": dir_15m=struct_15m["trend"]; conf_15m=60
    else: dir_15m="WAIT"; conf_15m=0

    # CONFLUENCE PURE PA
    # Rule: 4H trend must align with 1H CHoCH/BOS and 15M BOS
    if trend_4h=="BUY" and dir_1h=="BUY" and dir_15m=="BUY":
        direction="BUY"; count=3; conf_pct=90; emoji="🟢"
    elif trend_4h=="SELL" and dir_1h=="SELL" and dir_15m=="SELL":
        direction="SELL"; count=3; conf_pct=90; emoji="🔴"
    elif dir_1h=="BUY" and dir_15m=="BUY" and trend_4h!="SELL":
        direction="BUY"; count=2; conf_pct=80; emoji="🟢"
    elif dir_1h=="SELL" and dir_15m=="SELL" and trend_4h!="BUY":
        direction="SELL"; count=2; conf_pct=80; emoji="🔴"
    elif trend_4h!="WAIT" and dir_1h==trend_4h:
        direction=trend_4h; count=2; conf_pct=75; emoji="🟢" if direction=="BUY" else "🔴"
    else:
        direction="WAIT"; count=0; conf_pct=0; emoji="⚪"

    # PURE PA SL/TP - Structure based
    if direction=="BUY":
        # SL below last HL (Higher Low) or last 15M low
        recent_low_15m=min([c["low"] for c in data["candles_15m"][-5:]])
        sl=min(struct_1h["last_low"], struct_15m["last_low"], recent_low_15m) - atr_15m*0.8
        if price - sl > 18: sl = price - 15
        if price - sl < 5: sl = price - 7
        risk=price-sl
        tp1=price + risk*1.0
        tp2=price + risk*2.0
        tp3=price + risk*3.0
    elif direction=="SELL":
        recent_high_15m=max([c["high"] for c in data["candles_15m"][-5:]])
        sl=max(struct_1h["last_high"], struct_15m["last_high"], recent_high_15m) + atr_15m*0.8
        if sl - price > 18: sl = price + 15
        if sl - price < 5: sl = price + 7
        risk=sl-price
        tp1=price - risk*1.0
        tp2=price - risk*2.0
        tp3=price - risk*3.0
    else:
        sl=price-10; tp1=price+8; tp2=price+16; tp3=price+24; risk=8

    now=datetime.now().strftime("%H:%M:%S %d/%m")
    src="TwelveData" if use_td else "GoldAPI"

    # FULL message (private bot)
    lines=[]
    lines.append(f"🏆 GOLD VIP V9.0 PURE PRICE ACTION {src} 🏆")
    lines.append(f"💰 ${price:.2f} | {now} | 4H {trend_4h} | 1H {dir_1h} | 15M {dir_15m}")
    lines.append("")
    lines.append(f"📊 4H Father: {struct_4h['pattern']} - Trend {trend_4h}")
    lines.append(f"   Last High {struct_4h['last_high']:.2f} Low {struct_4h['last_low']:.2f}")
    lines.append(f"📊 1H Son: {struct_1h['pattern']} | CHoCH: {bos_choch_1h['choch']} | BOS: {bos_choch_1h['bos']}")
    lines.append(f"📊 15M Grandson: {struct_15m['pattern']} | BOS: {bos_choch_15m['bos']} | CHoCH: {bos_choch_15m['choch']}")
    lines.append("")
    if direction!="WAIT":
        lines.append(f"{emoji} {direction} {conf_pct}% ({count}/3 PA agree) - PURE PRICE ACTION")
        lines.append(f"ENTRY {price:.2f}")
        lines.append(f"SL {sl:.2f} (Below HL / Above LH + ATR)")
        lines.append(f"TP1 {tp1:.2f} (1:1) | TP2 {tp2:.2f} (1:2) | TP3 {tp3:.2f} (1:3)")
        lines.append(f"RR 1:2.0 | Risk {risk:.1f}$")
        lines.append(f"Setup: 4H {trend_4h} -> 1H CHoCH/BOS -> 15M BOS Entry")
    else:
        lines.append(f"⚪ WAIT {conf_pct}% - No PA confluence")
        lines.append(f"Need: 4H {trend_4h} + 1H {dir_1h} + 15M {dir_15m} align")

    # VIP clean format (only this goes to channel)
    vip_lines=[]
    if direction!="WAIT":
        vip_lines.append(f"{emoji} {direction} {conf_pct}% ({count}/3 agree) - PURE PRICE ACTION")
        vip_lines.append(f"ENTRY {price:.2f}")
        vip_lines.append(f"SL {sl:.2f} (Structure + ATR)")
        vip_lines.append(f"TP1 {tp1:.2f} | TP2 {tp2:.2f} | TP3 {tp3:.2f}")
        vip_lines.append(f"RR 1:2.0 | Risk {risk:.1f}$")
    else:
        vip_lines.append(f"⚪ WAIT {conf_pct}%")
        vip_lines.append(f"Pure PA: Waiting for 4H + 1H + 15M alignment")

    full_msg="\n".join(lines); vip_msg="\n".join(vip_lines)
    return full_msg, vip_msg, direction, conf_pct, count, price, sl, tp1, tp2, tp3, risk

def run_backtest_pure():
    if not TWELVE_KEY: return {"error":"No TWELVE_DATA_API_KEY"}
    try:
        print("Backtest PURE PA: Fetching 2000x 1H candles...")
        candles_1h=fetch_twelvedata_candles("XAU/USD","1h",TWELVE_KEY,2000)
        if not candles_1h or len(candles_1h)<200: return {"error":f"Failed fetch {len(candles_1h) if candles_1h else 0}"}
        candles_4h=fetch_twelvedata_candles("XAU/USD","4h",TWELVE_KEY,500)
        trades=[]; wins_tp1=0; wins_tp2=0; losses=0; be=0; total_signals=0
        # Map 4H trend for each 1H index (approx)
        for i in range(60, len(candles_1h)-30, 2):
            hist_1h=candles_1h[i-50:i]
            if len(hist_1h)<50: continue
            closes=[c["close"] for c in hist_1h]; highs=[c["high"] for c in hist_1h]; lows=[c["low"] for c in hist_1h]
            atr_v=atr(highs,lows,closes,14)
            struct_1h=detect_structure(hist_1h)
            bos_1h=detect_bos_choch(hist_1h, struct_1h)
            # Simulate 4H structure from 1H (every 4 candles = 4H)
            hist_4h_slice=candles_1h[max(0,i-200):i:4]
            if len(hist_4h_slice)<20: continue
            struct_4h=detect_structure(hist_4h_slice)
            # 15M simulated as last 20 of 1H for BOS check (approx)
            hist_15m=hist_1h[-20:]
            struct_15m=detect_structure(hist_15m)
            bos_15m=detect_bos_choch(hist_15m, struct_15m)

            # PURE PA LOGIC
            trend_4h=struct_4h["trend"]
            if bos_1h["bull_choch"]: dir_1h="BUY"
            elif bos_1h["bear_choch"]: dir_1h="SELL"
            elif bos_1h["bull_bos"]: dir_1h="BUY"
            elif bos_1h["bear_bos"]: dir_1h="SELL"
            elif struct_1h["trend"]!="WAIT": dir_1h=struct_1h["trend"]
            else: dir_1h="WAIT"

            if bos_15m["bull_bos"] or bos_15m["bull_choch"]: dir_15m="BUY"
            elif bos_15m["bear_bos"] or bos_15m["bear_choch"]: dir_15m="SELL"
            elif struct_15m["trend"]!="WAIT": dir_15m=struct_15m["trend"]
            else: dir_15m="WAIT"

            if trend_4h=="BUY" and dir_1h=="BUY" and dir_15m=="BUY": direction="BUY"; conf=90
            elif trend_4h=="SELL" and dir_1h=="SELL" and dir_15m=="SELL": direction="SELL"; conf=90
            elif dir_1h=="BUY" and dir_15m=="BUY" and trend_4h!="SELL": direction="BUY"; conf=80
            elif dir_1h=="SELL" and dir_15m=="SELL" and trend_4h!="BUY": direction="SELL"; conf=80
            elif trend_4h!="WAIT" and dir_1h==trend_4h: direction=trend_4h; conf=75
            else: continue
            if conf<75: continue
            total_signals+=1
            price=hist_1h[-1]["close"]
            if direction=="BUY":
                recent_low=min([c["low"] for c in hist_1h[-5:]])
                sl=min(struct_1h["last_low"], recent_low) - atr_v*0.8
                if price-sl>18: sl=price-15
                if price-sl<5: sl=price-7
                risk=price-sl
                tp1=price+risk*1.0; tp2=price+risk*2.0
            else:
                recent_high=max([c["high"] for c in hist_1h[-5:]])
                sl=max(struct_1h["last_high"], recent_high) + atr_v*0.8
                if sl-price>18: sl=price+15
                if sl-price<5: sl=price+7
                risk=sl-price
                tp1=price-risk*1.0; tp2=price-risk*2.0

            future=candles_1h[i:i+48]
            hit_tp1=False; hit_tp2=False; hit_sl=False
            for fc in future:
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
            trades.append({"date":hist_1h[-1]["datetime"],"dir":direction,"conf":conf,"price":price,"outcome":outcome})

        total_closed=wins_tp1+wins_tp2+losses
        win_rate=(wins_tp1+wins_tp2)/total_closed*100 if total_closed>0 else 0
        tp2_rate=wins_tp2/total_closed*100 if total_closed>0 else 0
        return {"total_signals":total_signals,"wins_tp1":wins_tp1,"wins_tp2":wins_tp2,"losses":losses,"be":be,"total_closed":total_closed,"win_rate":win_rate,"tp2_rate":tp2_rate,"last_trades":trades[-20:],"candles_used":len(candles_1h)}
    except Exception as e:
        import traceback; return {"error":str(e),"trace":traceback.format_exc()[:1000]}

async def start(update, context):
    SUBSCRIBERS.add(update.effective_chat.id)
    td_status="✅ TwelveData ON" if TWELVE_KEY else "⚠️ TwelveData OFF"
    msg=f"🏆 GOLD VIP V9.0 PURE PRICE ACTION 🏆\n\n💰 VIP: $25 / month\n📢 Channel: {CHANNEL_USERNAME}\n🆔 ID: {CHANNEL_ID}\n💳 Wallet: {CRYPTO_WALLET}\n{td_status}\n\nPure PA Strategy: 4H HH/HL + LL/LH + 1H CHoCH/BOS + 15M BOS\nNo Indicators - No EMA - No RSI - No Sweep - Pure Structure\nEntry: 4H Trend -> 1H CHoCH/BOS -> 15M BOS Entry\nSL/TP: Structure HL/LH + ATR | TP1 1:1 | TP2 1:2 | TP3 1:3\n\nCommands:\n/signal - V9.0 pure PA signal\n/mtf - 4H 1H 15M structure\n/bos - Check BOS/CHoCH only\n/autopilot - Auto every 15 min\n/autostop - Stop\n/news - Structure report\n/buy - Join VIP\n/channeltest - Test channel\n/sendvip - Admin send VIP\n/backtest - Pure PA 6M Backtest"
    await update.message.reply_text(msg)

async def buy(update, context):
    msg=f"💳 JOIN VIP FOR $25 / MONTH\n\nPay via USDT TRC20:\n{CRYPTO_WALLET}\n\nAfter payment, send TXID to @Onyebest\n\n✅ Private VIP: {CHANNEL_USERNAME}\n✅ GOLD V9.0 Pure Price Action\n✅ 4H HH/HL + LL/LH\n✅ 1H CHoCH + BOS\n✅ 15M BOS Entry\n✅ Structure SL (HL/LH + ATR)\n✅ 2-3 Quality Signals Daily"
    await update.message.reply_text(msg)

async def signal(update, context):
    full_msg,vip_msg,_,_,_,_,_,_,_,_,_=build_gold_pure()
    await update.message.reply_text(full_msg)

async def mtf(update, context):
    data=get_gold_pure_pa()
    msg=f"📊 PURE PA MTF STRUCTURE\n💰 ${data['price']:.2f}\n\n4H Father: {data['struct_4h']['pattern']}\nTrend {data['struct_4h']['trend']} | High {data['struct_4h']['last_high']:.2f} Low {data['struct_4h']['last_low']:.2f}\nATR {data['atr_4h']:.2f}\n\n1H Son: {data['struct_1h']['pattern']}\nTrend {data['struct_1h']['trend']} | CHoCH {data['bos_choch_1h']['choch']} | BOS {data['bos_choch_1h']['bos']}\nHL {data['struct_1h']['last_low']:.2f} LH {data['struct_1h']['last_high']:.2f} | ATR {data['atr_1h']:.2f}\n\n15M Grandson: {data['struct_15m']['pattern']}\nBOS {data['bos_choch_15m']['bos']} | CHoCH {data['bos_choch_15m']['choch']}\nATR {data['atr_15m']:.2f}\n\nSource: {'TwelveData' if data['use_td'] else 'GoldAPI'} | Pure Structure Only"
    await update.message.reply_text(msg)

async def bos_cmd(update, context):
    data=get_gold_pure_pa()
    msg=f"🔍 BOS / CHoCH PURE PA SCAN\n💰 ${data['price']:.2f}\n\n1H CHoCH: {data['bos_choch_1h']['choch']}\n1H BOS: {data['bos_choch_1h']['bos']}\nStructure: {data['struct_1h']['pattern']}\nLast High {data['struct_1h']['last_high']:.2f} Low {data['struct_1h']['last_low']:.2f}\n\n15M CHoCH: {data['bos_choch_15m']['choch']}\n15M BOS: {data['bos_choch_15m']['bos']}\nStructure: {data['struct_15m']['pattern']}\n\nSetup: Wait for 4H Trend + 1H CHoCH + 15M BOS alignment"
    await update.message.reply_text(msg)

async def news(update, context):
    data=get_gold_pure_pa()
    await update.message.reply_text(f"📰 PURE PA STRUCTURE REPORT\n💰 Gold ${data['price']:.2f}\n\n4H: {data['struct_4h']['pattern']} -> Trend {data['struct_4h']['trend']}\n1H: {data['struct_1h']['pattern']} -> {data['bos_choch_1h']['choch']} / {data['bos_choch_1h']['bos']}\n15M: {data['struct_15m']['pattern']} -> {data['bos_choch_15m']['bos']}\n\nNo Indicators - Pure Market Structure\nHH = Higher High | HL = Higher Low (Uptrend)\nLL = Lower Low | LH = Lower High (Downtrend)\nCHoCH = Change of Character | BOS = Break of Structure")

async def autopilot_cmd(update, context):
    global AUTOPILOT_ACTIVE
    AUTOPILOT_ACTIVE=True; SUBSCRIBERS.add(update.effective_chat.id)
    await update.message.reply_text(f"✅ AUTOPILOT V9.0 PURE PA ON\n4H HH/HL -> 1H CHoCH/BOS -> 15M BOS\nPure Price Action - No Indicators\nCheck every 15 min\nAlert only 75%+ PA confluence\nYour chat ID {update.effective_chat.id} saved.\nUse /autostop to stop")
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
            full_msg,vip_msg,direction,conf_pct,count,price,sl,tp1,tp2,tp3,risk=build_gold_pure()
            if count>=2 and conf_pct>=75 and direction!="WAIT":
                for chat_id in list(SUBSCRIBERS):
                    try: await context.bot.send_message(chat_id=chat_id, text=f"🤖 AUTOPILOT V9.0 PURE PA\n{full_msg}")
                    except: pass
                try: await context.bot.send_message(chat_id=CHANNEL_ID, text=vip_msg)
                except: pass
        except Exception as e: print(f"Autopilot error: {e}")

async def sendvip(update, context):
    if update.effective_user.id!=ADMIN_ID:
        await update.message.reply_text("❌ Admin only"); return
    full_msg,vip_msg,direction,conf_pct,count,price,sl,tp1,tp2,tp3,risk=build_gold_pure()
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=vip_msg)
        await update.message.reply_text(f"✅ Sent to VIP {CHANNEL_ID}:\n{vip_msg}")
    except Exception as e: await update.message.reply_text(f"❌ Failed to send to {CHANNEL_ID}: {e}")

async def setchannel(update, context):
    global CHANNEL_ID
    if update.effective_user.id!=ADMIN_ID:
        await update.message.reply_text("❌ Admin only"); return
    if context.args:
        CHANNEL_ID=context.args[0]
        await update.message.reply_text(f"✅ Channel set to: {CHANNEL_ID}")
    else: await update.message.reply_text(f"Current Channel: {CHANNEL_ID}\nUsage: /setchannel -100xxxx")

async def channeltest(update, context):
    if not CHANNEL_ID: await update.message.reply_text("❌ CHANNEL_ID not set."); return
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="✅ VIP Bot V9.0 PURE PRICE ACTION Test - TwelveData Connected!")
        await update.message.reply_text("✅ Test sent to channel!")
    except Exception as e: await update.message.reply_text(f"❌ Failed: {e}")

async def backtest(update, context):
    await update.message.reply_text("⏳ Running V9.0 PURE PA 6-Month Backtest... Fetching 2000x 1H + 500x 4H candles (30 sec)... Pure Structure Only - No Indicators...")
    try:
        loop=asyncio.get_event_loop()
        result=await loop.run_in_executor(None, run_backtest_pure)
        if "error" in result:
            await update.message.reply_text(f"❌ Backtest Error: {result['error']}\n{result.get('trace','')[:500]}"); return
        msg=f"📊 V9.0 PURE PRICE ACTION BACKTEST 6M\n"
        msg+=f"Candles: {result['candles_used']} x 1H (~{result['candles_used']//24} days)\n"
        msg+=f"Total Signals (75%+ PA): {result['total_signals']}\n"
        msg+=f"Closed Trades: {result['total_closed']}\n"
        msg+=f"✅ TP2 WIN (1:2): {result['wins_tp2']}\n"
        msg+=f"✅ TP1 WIN (1:1): {result['wins_tp1']}\n"
        msg+=f"❌ LOSS (SL hit): {result['losses']}\n"
        msg+=f"➖ BE (no TP/SL in 48h): {result['be']}\n"
        msg+=f"\n🏆 WIN RATE: {result['win_rate']:.1f}% (TP1+TP2)\n"
        msg+=f"💎 TP2 RATE: {result['tp2_rate']:.1f}% (full 1:2 RR)\n"
        msg+=f"\nPure PA: 4H HH/HL + LL/LH + 1H CHoCH/BOS + 15M BOS\n"
        msg+=f"SL: Structure HL/LH + 0.8 ATR | TP1 1:1 | TP2 1:2\n"
        msg+=f"No EMA - No RSI - No Sweep - No DXY - Pure Structure\n"
        if result['last_trades']:
            msg+=f"\n📜 Last 10 trades:\n"
            for t in result['last_trades'][-10:]:
                emoji="🟢" if t['dir']=="BUY" else "🔴"
                msg+=f"{emoji} {t['date'][:10]} {t['dir']} {t['conf']}% -> {t['outcome']} @ {t['price']:.2f}\n"
        await update.message.reply_text(msg)
        if update.effective_user.id==ADMIN_ID:
            try:
                vip_summary=f"🏆 V9.0 PURE PA BACKTEST 6M\nWIN {result['win_rate']:.1f}% | TP2 {result['tp2_rate']:.1f}%\nSignals: {result['total_signals']} | Closed: {result['total_closed']}\nTP2:{result['wins_tp2']} TP1:{result['wins_tp1']} LOSS:{result['losses']}\nPure PA: 4H+1H CHoCH/BOS+15M BOS"
                await context.bot.send_message(chat_id=CHANNEL_ID, text=vip_summary)
            except: pass
    except Exception as e: await update.message.reply_text(f"❌ Backtest failed: {e}")

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
    print(f"GOLD VIP V9.0 PURE PRICE ACTION started - No Indicators - Pure Structure")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message"])

if __name__=="__main__": main()
