import numpy as np
import pandas as pd
import ta
from data import fetch_data


def run_backtest(symbol: str, initial_balance: float = 10_000, risk_pct: float = 0.02):
    df = fetch_data(symbol, force_interval="4h")
    if df.empty or len(df) < 100:
        return {"error": "Not enough data"}

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    rsi = ta.momentum.rsi(close, window=14)
    ema50 = ta.trend.ema_indicator(close, window=50)
    ema200 = ta.trend.ema_indicator(close, window=200)
    macd = ta.trend.macd(close)
    macd_sig = ta.trend.macd_signal(close)
    atr = ta.volatility.average_true_range(high, low, close, window=14)

    balance = initial_balance
    trades = []
    in_position = False
    entry_price = 0
    entry_idx = 0

    for i in range(60, len(df)):
        if pd.isna(rsi.iloc[i]) or pd.isna(ema50.iloc[i]) or pd.isna(atr.iloc[i]):
            continue

        price = float(close.iloc[i])
        r = float(rsi.iloc[i])
        e50 = float(ema50.iloc[i])
        e200 = float(ema200.iloc[i]) if not pd.isna(ema200.iloc[i]) else 0
        m = float(macd.iloc[i])
        ms = float(macd_sig.iloc[i])
        a = float(atr.iloc[i])

        buy_signal = (
            r < 35
            and price < e50
            and m > ms
        )

        sell_signal = (
            in_position
            and (r > 70 or price < entry_price - a * 2 or price > entry_price + a * 4)
        )

        if not in_position and buy_signal:
            entry_price = price
            entry_idx = i
            sl = price - a * 1.8
            tp = price + a * 2.5
            risk_amt = balance * risk_pct
            size = risk_amt / (price - sl) if (price - sl) > 0 else 0
            in_position = True

        elif in_position and sell_signal:
            pnl = (price - entry_price) * size
            balance += pnl
            trades.append({
                "entry": round(entry_price, 2),
                "exit": round(price, 2),
                "pnl": round(pnl, 2),
                "bars_held": i - entry_idx,
                "return_pct": round(pnl / (entry_price * size) * 100, 2) if size > 0 else 0,
                "exit_reason": "TP/SL" if (price <= entry_price - a * 2 or price >= entry_price + a * 4) else "RSI/MACD",
            })
            in_position = False

    if in_position:
        price = float(close.iloc[-1])
        pnl = (price - entry_price) * size
        balance += pnl
        trades.append({
            "entry": round(entry_price, 2),
            "exit": round(price, 2),
            "pnl": round(pnl, 2),
            "bars_held": len(df) - entry_idx,
            "return_pct": round(pnl / (entry_price * size) * 100, 2) if size > 0 else 0,
            "exit_reason": "END_OF_DATA",
        })

    winners = [t for t in trades if t["pnl"] > 0]
    losers = [t for t in trades if t["pnl"] <= 0]
    total_pnl = balance - initial_balance

    return {
        "symbol": symbol,
        "initial_balance": initial_balance,
        "final_balance": round(balance, 2),
        "total_return": round(total_pnl, 2),
        "return_pct": round(total_pnl / initial_balance * 100, 2),
        "total_trades": len(trades),
        "winners": len(winners),
        "losers": len(losers),
        "win_rate": round(len(winners) / len(trades) * 100, 1) if trades else 0,
        "avg_winner": round(np.mean([t["pnl"] for t in winners]), 2) if winners else 0,
        "avg_loser": round(np.mean([t["pnl"] for t in losers]), 2) if losers else 0,
        "max_drawdown": 0,
    }
