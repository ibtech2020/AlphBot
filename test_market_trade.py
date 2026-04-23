#!/usr/bin/env python3
"""
TEST VERSION - Forces a market buy to test the bot
This will open a PAPER trade immediately for testing
"""

import time
import warnings
import pandas as pd
from config import get_exchange, SYMBOL, POSITION_SIZE_USDT, STOP_LOSS_PCT, TAKE_PROFIT_PCT

warnings.filterwarnings("ignore", category=UserWarning)

exchange = get_exchange()

print("="*60)
print("🧪 TEST MODE: Forcing a market buy to test the bot")
print("="*60)

# Get current market price
ticker = exchange.fetch_ticker(SYMBOL)
current_price = ticker['last']

print(f"\n📊 Current {SYMBOL} price: ${current_price:.2f}")

# Calculate trade levels
amount = POSITION_SIZE_USDT / current_price
stop_loss = current_price * (1 - STOP_LOSS_PCT)
take_profit = current_price * (1 + TAKE_PROFIT_PCT)

print(f"\n🎯 TEST TRADE DETAILS:")
print(f"   Direction: LONG (BUY)")
print(f"   Entry Price: ${current_price:.2f}")
print(f"   Position Size: ${POSITION_SIZE_USDT} USDT ({amount:.6f} {SYMBOL.split('/')[0]})")
print(f"   Stop Loss: ${stop_loss:.2f} (Loss: ${POSITION_SIZE_USDT * STOP_LOSS_PCT:.2f})")
print(f"   Take Profit: ${take_profit:.2f} (Profit: ${POSITION_SIZE_USDT * TAKE_PROFIT_PCT:.2f})")
print(f"   Risk:Reward = 1:{TAKE_PROFIT_PCT/STOP_LOSS_PCT:.0f}")

# ========== PLACE PAPER TRADE ==========
print("\n🔵 PLACING PAPER TRADE...")

# For Alpaca paper trading, we'll simulate the order
# (Alpaca's paper API requires account verification for real orders)

try:
    # Try to place a real paper order (might need account setup)
    order = exchange.create_order(
        symbol=SYMBOL,
        type='market',
        side='buy',
        amount=amount
    )
    print(f"✅ PAPER ORDER PLACED SUCCESSFULLY!")
    print(f"   Order ID: {order.get('id', 'N/A')}")
    print(f"   Status: {order.get('status', 'filled')}")
    
except Exception as e:
    print(f"⚠️ Could not place actual order: {e}")
    print("\n📋 SIMULATING PAPER TRADE INSTEAD...")
    print(f"   ✅ SIMULATED: Bought {amount:.6f} {SYMBOL.split('/')[0]} at ${current_price:.2f}")

# ========== MONITOR THE POSITION ==========
print("\n" + "="*60)
print("📊 MONITORING POSITION - Will track until SL or TP hit")
print("="*60)

position = {
    'entry': current_price,
    'sl': stop_loss,
    'tp': take_profit,
    'amount': amount,
    'side': 'long'
}

try:
    while True:
        # Get current price
        ticker = exchange.fetch_ticker(SYMBOL)
        current_price = ticker['last']
        
        # Calculate current P&L
        if position['side'] == 'long':
            pnl_pct = (current_price - position['entry']) / position['entry'] * 100
            pnl_usdt = pnl_pct * POSITION_SIZE_USDT / 100
        else:
            pnl_pct = (position['entry'] - current_price) / position['entry'] * 100
            pnl_usdt = pnl_pct * POSITION_SIZE_USDT / 100
        
        # Check if stop loss hit
        if current_price <= position['sl']:
            print(f"\n❌ STOP LOSS HIT at ${current_price:.2f}")
            print(f"   Loss: {pnl_pct:.2f}% (${abs(pnl_usdt):.2f} USDT)")
            print(f"   Total: ${POSITION_SIZE_USDT - abs(pnl_usdt):.2f} USDT remaining")
            break
        
        # Check if take profit hit
        elif current_price >= position['tp']:
            print(f"\n✅ TAKE PROFIT HIT at ${current_price:.2f}")
            print(f"   Profit: {pnl_pct:.2f}% (${pnl_usdt:.2f} USDT)")
            print(f"   Total: ${POSITION_SIZE_USDT + pnl_usdt:.2f} USDT")
            break
        
        # Show live status
        emoji = "📈" if pnl_pct > 0 else "📉" if pnl_pct < 0 else "➡️"
        print(f"[{time.strftime('%H:%M:%S')}] ${current_price:.2f} | {emoji} P&L: {pnl_pct:+.2f}% (${pnl_usdt:+.2f}) | SL: ${position['sl']:.2f} | TP: ${position['tp']:.2f}")
        
        time.sleep(10)  # Check every 10 seconds for testing
        
except KeyboardInterrupt:
    print("\n\n🛑 Test stopped by user")
    
print("\n🏁 Test complete!")