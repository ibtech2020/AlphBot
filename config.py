import ccxt

API_KEY = "PKO5AWHBGG7FLZQLWQXHCE6FAJ"
API_SECRET = "8T4SCw6kamSbXb3vubUxbKxULjadqjZpTfyuyAVBmJNV"

SYMBOL = 'BTC/USD'
POSITION_SIZE_USDT = 10
STOP_LOSS_PCT = 0.01
TAKE_PROFIT_PCT = 0.02

def get_exchange():
    exchange = ccxt.alpaca({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True)
    return exchange
