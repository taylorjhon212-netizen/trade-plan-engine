import numpy as np
import pandas as pd
import ta


def pattern_success_rate(df: pd.DataFrame, lookback: int = 50) -> dict:
    if df.empty or len(df) < lookback:
        return {}

    close = df["close"].astype(float)
    open_p = df["open"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    results = {}

    rsi_series = ta.momentum.rsi(close, window=14)
    macd = ta.trend.macd(close)
    macd_sig = ta.trend.macd_signal(close)
    ema50 = ta.trend.ema_indicator(close, window=50)
    ema200 = ta.trend.ema_indicator(close, window=200)
    atr = ta.volatility.average_true_range(high, low, close, window=14)

    checks = {
        "RSI_OVERSOLD": {"hits": 0, "up": 0, "down": 0},
        "RSI_OVERBOUGHT": {"hits": 0, "up": 0, "down": 0},
        "MACD_CROSS_UP": {"hits": 0, "up": 0, "down": 0},
        "MACD_CROSS_DOWN": {"hits": 0, "up": 0, "down": 0},
        "PRICE_ABOVE_EMA50": {"hits": 0, "up": 0, "down": 0},
        "PRICE_BELOW_EMA50": {"hits": 0, "up": 0, "down": 0},
        "BOUNCE_FROM_SUPPORT": {"hits": 0, "up": 0, "down": 0},
    }

    for i in range(20, len(close) - 5):
        if pd.isna(rsi_series.iloc[i]) or pd.isna(ema50.iloc[i]):
            continue

        c = float(close.iloc[i])
        r = float(rsi_series.iloc[i])
        m = float(macd.iloc[i]) if not pd.isna(macd.iloc[i]) else 0
        ms = float(macd_sig.iloc[i]) if not pd.isna(macd_sig.iloc[i]) else 0
        e50 = float(ema50.iloc[i]) if not pd.isna(ema50.iloc[i]) else 0
        e200 = float(ema200.iloc[i]) if not pd.isna(ema200.iloc[i]) else 0
        l = float(low.iloc[i])
        a = float(atr.iloc[i]) if not pd.isna(atr.iloc[i]) else c * 0.02

        future_move = float(close.iloc[i + 5]) - c
        up = future_move > a * 0.5
        down = future_move < -a * 0.5

        if r < 30:
            checks["RSI_OVERSOLD"]["hits"] += 1
            if up: checks["RSI_OVERSOLD"]["up"] += 1
            if down: checks["RSI_OVERSOLD"]["down"] += 1

        if r > 70:
            checks["RSI_OVERBOUGHT"]["hits"] += 1
            if up: checks["RSI_OVERBOUGHT"]["up"] += 1
            if down: checks["RSI_OVERBOUGHT"]["down"] += 1

        if not pd.isna(macd.iloc[i]) and not pd.isna(macd_sig.iloc[i]):
            if i > 0 and float(macd.iloc[i - 1]) <= float(macd_sig.iloc[i - 1]) and m > ms:
                checks["MACD_CROSS_UP"]["hits"] += 1
                if up: checks["MACD_CROSS_UP"]["up"] += 1
                if down: checks["MACD_CROSS_DOWN"]["down"] += 1
            elif i > 0 and float(macd.iloc[i - 1]) >= float(macd_sig.iloc[i - 1]) and m < ms:
                checks["MACD_CROSS_DOWN"]["hits"] += 1
                if up: checks["MACD_CROSS_UP"]["up"] += 1
                if down: checks["MACD_CROSS_DOWN"]["down"] += 1

        if e50 and c > e50:
            checks["PRICE_ABOVE_EMA50"]["hits"] += 1
            if up: checks["PRICE_ABOVE_EMA50"]["up"] += 1
            if down: checks["PRICE_ABOVE_EMA50"]["down"] += 1
        elif e50 and c < e50:
            checks["PRICE_BELOW_EMA50"]["hits"] += 1
            if up: checks["PRICE_BELOW_EMA50"]["up"] += 1
            if down: checks["PRICE_BELOW_EMA50"]["down"] += 1

    for key, val in checks.items():
        if val["hits"] >= 3:
            up_prob = round(val["up"] / val["hits"] * 100, 1)
            down_prob = round(val["down"] / val["hits"] * 100, 1)
            results[key] = {"samples": val["hits"], "up_pct": up_prob, "down_pct": down_prob}

    return results


def current_predictions(df: pd.DataFrame) -> list:
    results = pattern_success_rate(df)
    if not results:
        return []

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    rsi = float(ta.momentum.rsi(close, window=14).iloc[-1])
    macd = ta.trend.macd(close)
    macd_sig = ta.trend.macd_signal(close)
    m = float(macd.iloc[-1]) if not macd.empty else 0
    ms = float(macd_sig.iloc[-1]) if not macd_sig.empty else 0
    ema50 = float(ta.trend.ema_indicator(close, window=50).iloc[-1])
    price = float(close.iloc[-1])

    predictions = []

    if rsi < 30 and "RSI_OVERSOLD" in results:
        r = results["RSI_OVERSOLD"]
        predictions.append(f"RSI oversold: {r['up_pct']}% bounced up (last {r['samples']} times)")

    if rsi > 70 and "RSI_OVERBOUGHT" in results:
        r = results["RSI_OVERBOUGHT"]
        predictions.append(f"RSI overbought: {r['down_pct']}% dropped (last {r['samples']} times)")

    if m > ms and "MACD_CROSS_UP" in results:
        r = results["MACD_CROSS_UP"]
        predictions.append(f"MACD bull cross: {r['up_pct']}% led to upside (last {r['samples']} times)")

    if m < ms and "MACD_CROSS_DOWN" in results:
        r = results["MACD_CROSS_DOWN"]
        predictions.append(f"MACD bear cross: {r['down_pct']}% led to drop (last {r['samples']} times)")

    if price > ema50 and "PRICE_ABOVE_EMA50" in results:
        r = results["PRICE_ABOVE_EMA50"]
        predictions.append(f"Above EMA50: {r['up_pct']}% continued up (last {r['samples']} times)")

    if price < ema50 and "PRICE_BELOW_EMA50" in results:
        r = results["PRICE_BELOW_EMA50"]
        predictions.append(f"Below EMA50: {r['down_pct']}% continued down (last {r['samples']} times)")

    return predictions[:3]
