import ccxt
import time
import pandas as pd
from tabulate import tabulate
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands

api_key = 'd1Idpf0yUwgqKqaaRSN01gGNwGgjJ9i1v49B6JKq0nAwIVxq7vPwfFcF8EpwpFYe'
api_secret = 'hbo78lcMlNp5k4MSaiLFNUtGljbo3YxAJccym34Kg8hCB2tFsfPwYveXnVrkO6Ka'

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot'
    }
})

timeframe = '30m'
limit = 100
amount_usdt = 6


def get_balance():
    balance = exchange.fetch_balance()
    return balance['total']


def get_most_volatile_pair():
    tickers = exchange.fetch_tickers()
    usdt_pairs = {
        symbol: data for symbol, data in tickers.items()
        if symbol.endswith('/USDT') and isinstance(data, dict)
    }

    # Filter hanya pair dengan data valid
    valid_pairs = {
        symbol: data for symbol, data in usdt_pairs.items()
        if data.get('percentage') is not None and data.get('quoteVolume') is not None
    }

    volatile_rank = sorted(valid_pairs.items(), key=lambda x: abs(x[1]['percentage']), reverse=True)
    volume_rank = sorted(valid_pairs.items(), key=lambda x: x[1]['quoteVolume'], reverse=True)

    top_volatile = [x[0] for x in volatile_rank[:10]]
    top_volume = [x[0] for x in volume_rank[:10]]

    for symbol in top_volatile:
        if symbol in top_volume:
            return symbol

    return top_volatile[0]


def get_ohlcv(symbol):
    bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['close'] = pd.to_numeric(df['close'], errors='coerce')

    df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
    macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    bb = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_upper'] = bb.bollinger_hband()
    df['ma50'] = df['close'].rolling(window=50).mean()

    df = df.fillna(0)
    return df


while True:
    try:
        symbol = get_most_volatile_pair()
        df = get_ohlcv(symbol)

        price = float(df['close'].iloc[-1])
        rsi = float(df['rsi'].iloc[-1])
        ma50 = float(df['ma50'].iloc[-1])
        macd = float(df['macd'].iloc[-1])
        signal = float(df['signal'].iloc[-1])
        bb_lower = float(df['bb_lower'].iloc[-1])
        bb_upper = float(df['bb_upper'].iloc[-1])

        print(f"\n\U0001F4C8 INDIKATOR PAIR {symbol}:")
        print(tabulate([
            ['Harga', round(price, 6)],
            ['RSI', round(rsi, 2)],
            ['MA-50', round(ma50, 6)],
            ['MACD', round(macd, 6)],
            ['MACD Signal', round(signal, 6)],
            ['BB Lower', round(bb_lower, 6)],
            ['BB Upper', round(bb_upper, 6)]
        ], headers=['Indikator', 'Nilai']))

        balance = get_balance()
        print("\n\U0001F4CA SALDO SAAT INI:")
        print(tabulate([[k, v] for k, v in balance.items() if k in ['USDT', 'BTC']], headers=['Coin', 'Total']))

        coin = symbol.replace('/USDT', '')

        if rsi < 30 and price < bb_lower and balance['USDT'] >= amount_usdt:
            amount = round(amount_usdt / price, 6)
            print(f"\n\U0001F4B5 Membeli {amount} {coin} karena RSI < 30 dan harga < BB Lower")
            exchange.create_market_buy_order(symbol, amount)

        elif rsi > 70 and macd > signal and price > ma50 and balance.get(coin, 0) > 0:
            print(f"\n\U0001F4B8 Menjual semua {coin} karena RSI > 70, MACD > Signal dan harga > MA50")
            exchange.create_market_sell_order(symbol, balance[coin])

        time.sleep(30)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        time.sleep(30)
