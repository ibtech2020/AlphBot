#!/usr/bin/env python3
"""
Multi-Crypto Trading Bot for Alpaca Paper Trading (LONG ONLY)
- Trades multiple pairs simultaneously
- EMA crossover + ATR-based 1:2 RRR
- RSI filter, trailing stop, break-even
- Independent position tracking per symbol
"""

import os
import time
import warnings
import random
import datetime
import pandas as pd
import ccxt
from config import get_exchange

warnings.filterwarnings("ignore", category=UserWarning)

# ========== MULTI-CRYPTO CONFIGURATION ==========
TRADING_PAIRS = [
    'BTC/USD',
    'ETH/USD',
    'SOL/USD',
    'DOGE/USD'
]

POSITION_SIZE_USD = 10       # $10 per trade

# ========== STRATEGY PARAMETERS ==========
FAST_EMA_LEN = 9
SLOW_EMA_LEN = 21
ATR_LEN = 14
ATR_MULTIPLIER = 1.0
RISK_REWARD_RATIO = 2.0

# RSI filter (optional)
USE_RSI_FILTER = True
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# Trailing stop (activate after 1% profit)
TRAILING_STOP_ACTIVATION_PCT = 1.0
TRAILING_STOP_DISTANCE_PCT = 0.5

# Break-even stop (move SL to entry after 1% profit)
BREAK_EVEN_ACTIVATION_PCT = 1.0

# API retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2

# Data cache (reduce API calls)
CACHE_DURATION = 60  # seconds
last_fetch_time = {}
cached_ohlcv = {}

# ========== TESTING CONFIGURATION ==========
TESTING_MODE = True       # Set to True for fast testing, False for real trading
TESTING_SPEED = "FAST"    # Options: "INSTANT", "FAST", "MEDIUM", "REAL"

# ========== INITIALIZE EXCHANGE ==========
exchange = get_exchange()

print("🤖 Multi-Crypto Bot Starting (LONG ONLY)")
print(f"Trading pairs: {', '.join(TRADING_PAIRS)}")
print(f"Strategy: EMA({FAST_EMA_LEN}/{SLOW_EMA_LEN}) crossover + ATR(14) 1:2 RRR")
print(f"Position size: ${POSITION_SIZE_USD} per trade")
print(f"Testing Mode: {TESTING_MODE} - Speed: {TESTING_SPEED}")
if USE_RSI_FILTER:
    print(f"RSI filter: ON (oversold {RSI_OVERSOLD}, overbought {RSI_OVERBOUGHT})")
print("="*60)

# ========== HELPER FUNCTIONS ==========

def fetch_ohlcv_cached(symbol, timeframe='5m', limit=100):
    global last_fetch_time, cached_ohlcv
    now = time.time()
    if symbol in cached_ohlcv and (now - last_fetch_time.get(symbol, 0)) < CACHE_DURATION:
        return cached_ohlcv[symbol]
    
    for attempt in range(MAX_RETRIES):
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if ohlcv and len(ohlcv) >= 2:
                cached_ohlcv[symbol] = ohlcv
                last_fetch_time[symbol] = now
                return ohlcv
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                print(f"   ⚠️ Failed to fetch {symbol}: {str(e)[:50]}")
                return cached_ohlcv.get(symbol, None)
    return None

def calculate_ema(df, period):
    return df['close'].ewm(span=period, adjust=False).mean()

def calculate_atr(df, period=14):
    high, low, close = df['high'], df['low'], df['close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1]

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def get_buy_signal(df, current_price, testing_mode, speed):
    """Return (buy_signal) based on EMA crossover/under + optional RSI. No sell signal."""
    if testing_mode:
        if speed == "INSTANT":
            current_second = datetime.datetime.now().second
            return current_second < 7  # only buy signals
        elif speed == "FAST":
            slow_ema = df['ema_slow'].iloc[-1]
            if pd.isna(slow_ema):
                return False
            return current_price > slow_ema
        elif speed == "MEDIUM":
            fast_ema = df['ema_fast'].iloc[-1]
            slow_ema = df['ema_slow'].iloc[-1]
            prev_fast = df['ema_fast'].iloc[-2]
            prev_slow = df['ema_slow'].iloc[-2]
            if pd.isna(fast_ema) or pd.isna(slow_ema) or pd.isna(prev_fast) or pd.isna(prev_slow):
                return False
            buy = (fast_ema > slow_ema) and (prev_fast <= prev_slow)
            return buy
        else:  # RANDOM
            return random.random() < 0.15
    else:
        # REAL TRADING MODE
        fast_ema = df['ema_fast'].iloc[-1]
        slow_ema = df['ema_slow'].iloc[-1]
        prev_fast = df['ema_fast'].iloc[-2]
        prev_slow = df['ema_slow'].iloc[-2]
        if pd.isna(fast_ema) or pd.isna(slow_ema) or pd.isna(prev_fast) or pd.isna(prev_slow):
            return False
        
        buy = (fast_ema > slow_ema) and (prev_fast <= prev_slow)
        
        # Apply RSI filter if enabled
        if USE_RSI_FILTER and buy:
            rsi = calculate_rsi(df['close'], RSI_PERIOD)
            if rsi > RSI_OVERBOUGHT:
                buy = False  # Don't buy if overbought
        return buy

def calculate_trade_levels(price, atr):
    """Calculate SL and TP for long only."""
    sl = price - atr * ATR_MULTIPLIER
    risk = price - sl
    tp = price + risk * RISK_REWARD_RATIO
    return sl, tp

def place_market_order(symbol, side, amount):
    """Place a market order (only 'buy' for entry, 'sell' for exit)."""
    try:
        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=amount
        )
        return order['id']
    except Exception as e:
        print(f"   ❌ Order failed for {symbol}: {e}")
        return None

def update_trailing_stop(position, current_price):
    if position['side'] == 'long':
        profit_pct = (current_price - position['entry']) / position['entry'] * 100
        if profit_pct >= TRAILING_STOP_ACTIVATION_PCT:
            new_sl = current_price * (1 - TRAILING_STOP_DISTANCE_PCT / 100)
            if new_sl > position['sl']:
                position['sl'] = new_sl
                return True
    return False

def update_break_even(position, current_price):
    if position['side'] == 'long':
        profit_pct = (current_price - position['entry']) / position['entry'] * 100
        if profit_pct >= BREAK_EVEN_ACTIVATION_PCT and position['sl'] < position['entry']:
            position['sl'] = position['entry']
            return True
    return False

# ========== MAIN LOOP ==========
def main():
    positions = {}
    iteration = 0
    signal_counts = {symbol: 0 for symbol in TRADING_PAIRS}
    last_valid_dfs = {}

    while True:
        try:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"🔄 Cycle {iteration} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            for symbol in TRADING_PAIRS:
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    current_price = ticker['last']
                    
                    ohlcv = fetch_ohlcv_cached(symbol, timeframe='5m', limit=100)
                    if ohlcv is None:
                        if symbol in last_valid_dfs:
                            df = last_valid_dfs[symbol]
                            print(f"⚠️ {symbol}: Using cached data")
                        else:
                            print(f"⚠️ {symbol}: No data, skipping")
                            continue
                    else:
                        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['ema_fast'] = calculate_ema(df, FAST_EMA_LEN)
                        df['ema_slow'] = calculate_ema(df, SLOW_EMA_LEN)
                        atr = calculate_atr(df, ATR_LEN)
                        last_valid_dfs[symbol] = df.copy()
                    
                    buy_signal = get_buy_signal(df, current_price, TESTING_MODE, TESTING_SPEED)
                    position = positions.get(symbol)
                    
                    if not position and buy_signal:
                        signal_counts[symbol] += 1
                        amount = POSITION_SIZE_USD / current_price
                        sl, tp = calculate_trade_levels(current_price, atr)
                        
                        if amount > 0 and sl < current_price < tp:
                            print(f"\n📈 {symbol} LONG SIGNAL #{signal_counts[symbol]} at ${current_price:.4f}")
                            print(f"   Time: {datetime.datetime.now().strftime('%H:%M:%S')}")
                            print(f"   Entry: ${current_price:.4f}")
                            print(f"   Stop Loss: ${sl:.4f} (Loss: ${(current_price - sl) * amount:.2f})")
                            print(f"   Take Profit: ${tp:.4f} (Profit: ${(tp - current_price) * amount:.2f})")
                            
                            order_id = place_market_order(symbol, 'buy', amount)
                            if order_id:
                                positions[symbol] = {
                                    'side': 'long',
                                    'entry': current_price,
                                    'sl': sl,
                                    'tp': tp,
                                    'amount': amount
                                }
                                print(f"   ✅ Position opened (order {order_id})")
                            else:
                                print("   ⚠️ Entry failed")
                        else:
                            print(f"   ⚠️ {symbol} Invalid SL/TP levels")
                    
                    if symbol in positions:
                        position = positions[symbol]
                        exit_triggered = False
                        
                        if update_trailing_stop(position, current_price):
                            print(f"   📈 {symbol} Trailing stop raised to ${position['sl']:.4f}")
                        if update_break_even(position, current_price):
                            print(f"   🔒 {symbol} Stop moved to break-even at ${position['entry']:.4f}")
                        
                        if current_price <= position['sl']:
                            print(f"\n❌ {symbol} STOP LOSS TRIGGERED at ${current_price:.4f}")
                            exit_triggered = True
                        elif current_price >= position['tp']:
                            print(f"\n✅ {symbol} TAKE PROFIT TRIGGERED at ${current_price:.4f}")
                            exit_triggered = True
                        
                        if exit_triggered:
                            close_order_id = place_market_order(symbol, 'sell', position['amount'])
                            if close_order_id:
                                print(f"   ✅ {symbol} Position closed (order {close_order_id})")
                            else:
                                print(f"   ⚠️ {symbol} Failed to close position")
                            del positions[symbol]
                    
                    status = "🔴 IN POSITION" if symbol in positions else "🟢 WAITING"
                    ema_fast_val = df['ema_fast'].iloc[-1] if not pd.isna(df['ema_fast'].iloc[-1]) else 0
                    ema_slow_val = df['ema_slow'].iloc[-1] if not pd.isna(df['ema_slow'].iloc[-1]) else 0
                    atr_val = atr if not pd.isna(atr) else 0
                    print(f"[{time.strftime('%H:%M:%S')}] {symbol}: ${current_price:.4f} | EMA9: ${ema_fast_val:.0f} | EMA21: ${ema_slow_val:.0f} | ATR: ${atr_val:.2f} | {status} | Signals: {signal_counts[symbol]}")
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"⚠️ Error processing {symbol}: {e}")
                    continue
            
            if TESTING_MODE and TESTING_SPEED == "INSTANT":
                time.sleep(5)
            else:
                time.sleep(60)
            
        except KeyboardInterrupt:
            print(f"\n🛑 Bot stopped")
            print(f"Final signal counts: {signal_counts}")
            break
        except Exception as e:
            print(f"⚠️ Main loop error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()