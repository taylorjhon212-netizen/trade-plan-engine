import numpy as np
import pandas as pd
import ta
from dataclasses import dataclass, asdict
from patterns import detect_candle_patterns, detect_chart_patterns
from data import fetch_data
from ecocal import get_week_ahead_note
from predictor import current_predictions


@dataclass
class TradePlan:
    symbol: str
    asset_type: str
    price: float
    trend: str
    trend_strength: str
    support_levels: list
    resistance_levels: list
    ema_20: float
    ema_50: float
    ema_200: float
    rsi: float
    macd_line: float
    macd_signal: float
    macd_histogram: float
    atr: float
    atr_pct: float
    volume_ratio: float
    candle_patterns: list
    chart_patterns: list
    multi_tf_signal: list
    bull_case: str
    bear_case: str
    entry_price: float
    stop_loss: float
    sl_pct: float
    take_profit_1: float
    tp1_pct: float
    take_profit_2: float
    tp2_pct: float
    take_profit_3: float
    tp3_pct: float
    risk_reward_1: float
    risk_reward_2: float
    risk_reward_3: float
    recommended_rr: str
    bollinger_upper: float = 0
    bollinger_lower: float = 0
    bollinger_width_pct: float = 0
    bollinger_squeeze: bool = False
    obv: float = 0
    adx: float = 0
    adx_strength: str = ""
    market_note: str = ""
    eco_calendar_note: str = ""
    ai_predictions: list = None
    max_risk_pct: float = 0.02
    position_size_usd: float = 0
    daily_loss_limit: float = 0
    cooldown_seconds: int = 30
    psychology_notes: list = None

    def to_dict(self):
        return asdict(self)


def safe_ema(series: pd.Series, window: int) -> float:
    if len(series) < window:
        return 0.0
    val = ta.trend.ema_indicator(series, window=window)
    if val.empty or pd.isna(val.iloc[-1]):
        return 0.0
    return float(val.iloc[-1])


def find_sr_levels(series: pd.Series, pct_threshold: float = 0.03):
    half = max(5, len(series) // 20)
    highs = series.rolling(window=half, center=True).max()
    lows = series.rolling(window=half, center=True).min()
    peak_vals = series[series == highs].dropna().values
    trough_vals = series[series == lows].dropna().values
    all_vals = np.unique(np.concatenate([peak_vals, trough_vals]))
    if len(all_vals) < 2:
        return [], []
    all_vals = np.sort(all_vals)
    clustered = []
    for v in all_vals:
        if not clustered or abs(v - clustered[-1]) / clustered[-1] > pct_threshold:
            clustered.append(v)
    return clustered


def calc_sl_tp(price: float, atr: float, supports: list, resistances: list):
    sl_atr = price - atr * 1.8
    sl_sr = supports[0] if supports else price * 0.92
    sl_sr = sl_sr * 0.995
    sl = max(sl_atr, sl_sr)
    sl = max(sl, price * 0.88)

    tp1_sr = resistances[0] if resistances else price * 1.05
    tp1_atr = price + atr * 1.0
    tp1 = min(tp1_sr, tp1_atr) if tp1_sr > price + atr * 0.3 else tp1_atr

    tp2_atr = price + atr * 2.2
    tp2_sr = resistances[1] if len(resistances) > 1 else price * 1.10
    tp2 = min(tp2_sr, tp2_atr) if tp2_sr > tp1 else tp2_atr

    tp3_atr = price + atr * 3.5
    tp3_sr = resistances[2] if len(resistances) > 2 else price * 1.15
    tp3 = min(tp3_sr, tp3_atr) if tp3_sr > tp2 else tp3_atr

    return sl, tp1, tp2, tp3


def check_multi_tf(symbol: str) -> list:
    signals = []
    tfs = {"1d": "trend", "4h": "entry", "1h": "precision"}
    for tf, label in tfs.items():
        try:
            df = fetch_data(symbol, force_interval=tf)
            if df.empty or len(df) < 30:
                continue
            close = df["close"].astype(float)
            price = float(close.iloc[-1])
            ema50 = safe_ema(close, 50)
            ema200 = safe_ema(close, 200)
            rsi_v = float(ta.momentum.rsi(close, window=14).iloc[-1])
            trend = "BULLISH" if price > ema50 and price > ema200 else "BEARISH" if price < ema50 else "NEUTRAL"
            direction = "UP" if rsi_v > 50 else "DOWN"
            signals.append((tf, label, trend, round(rsi_v, 1), direction))
        except Exception:
            signals.append((tf, label, "NO_DATA", 0, "-"))
    return signals


def generate_plan(symbol: str, df: pd.DataFrame, multi_tf: bool = True) -> TradePlan:
    asset_type = "crypto" if symbol.upper().endswith(("USDT", "USD", "USDC", "BUSD")) else "stock"
    df = df.copy()
    if len(df) < 30:
        return TradePlan(symbol=symbol, asset_type=asset_type, price=0, trend="NO_DATA",
                         trend_strength="", support_levels=[], resistance_levels=[],
                         ema_20=0, ema_50=0, ema_200=0, rsi=0, macd_line=0, macd_signal=0,
                         macd_histogram=0, atr=0, atr_pct=0, volume_ratio=0,
                         bollinger_upper=0, bollinger_lower=0, bollinger_width_pct=0,
                         bollinger_squeeze=False, obv=0, adx=0, adx_strength="",
                         candle_patterns=[], chart_patterns=[], multi_tf_signal=[],
                         bull_case="", bear_case="", entry_price=0, stop_loss=0, sl_pct=0,
                         take_profit_1=0, tp1_pct=0, take_profit_2=0, tp2_pct=0,
                         take_profit_3=0, tp3_pct=0, risk_reward_1=0, risk_reward_2=0,
                         risk_reward_3=0, recommended_rr="", eco_calendar_note="",
                         ai_predictions=[])

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float)
    price = float(close.iloc[-1])

    ema_20 = safe_ema(close, 20)
    ema_50 = safe_ema(close, 50)
    ema_200 = safe_ema(close, 200)

    rsi_series = ta.momentum.rsi(close, window=14)
    rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

    macd = ta.trend.macd(close)
    macd_sig = ta.trend.macd_signal(close)
    macd_line = float(macd.iloc[-1]) if not macd.empty else 0.0
    macd_signal_val = float(macd_sig.iloc[-1]) if not macd_sig.empty else 0.0
    macd_hist = macd_line - macd_signal_val

    atr_series = ta.volatility.average_true_range(high, low, close, window=14)
    atr = float(atr_series.iloc[-1]) if not atr_series.empty else price * 0.02
    atr_pct = (atr / price * 100) if price else 0.0

    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_upper = float(bb.bollinger_hband().iloc[-1]) if not bb.bollinger_hband().empty else 0
    bb_lower = float(bb.bollinger_lband().iloc[-1]) if not bb.bollinger_lband().empty else 0
    bb_mid = float(bb.bollinger_mavg().iloc[-1]) if not bb.bollinger_mavg().empty else 0
    bb_width = ((bb_upper - bb_lower) / bb_mid * 100) if bb_mid else 0
    bb_squeeze = bb_width < 5.0

    obv_indicator = ta.volume.OnBalanceVolumeIndicator(close, volume)
    obv = float(obv_indicator.on_balance_volume().iloc[-1]) if not obv_indicator.on_balance_volume().empty else 0

    adx_indicator = ta.trend.ADXIndicator(high, low, close, window=14)
    adx = float(adx_indicator.adx().iloc[-1]) if not adx_indicator.adx().empty else 0
    if adx >= 25:
        adx_strength = "Strong"
    elif adx >= 20:
        adx_strength = "Moderate"
    else:
        adx_strength = "Weak"

    vol_ma = volume.rolling(20).mean()
    vol_ratio = float(volume.iloc[-1] / vol_ma.iloc[-1]) if not vol_ma.empty and vol_ma.iloc[-1] > 0 else 1.0

    candle_patterns = detect_candle_patterns(df)
    chart_patterns = detect_chart_patterns(df)

    mtf_signals = []
    if multi_tf and asset_type == "crypto":
        mtf_signals = check_multi_tf(symbol)

    raw_levels = find_sr_levels(close, pct_threshold=0.03)
    supports = sorted([v for v in raw_levels if v < price], reverse=True)[:3]
    resistances = sorted([v for v in raw_levels if v > price])[:3]
    if not supports:
        supports = [round(price * 0.95, 2), round(price * 0.92, 2), round(price * 0.88, 2)]
    if not resistances:
        resistances = [round(price * 1.05, 2), round(price * 1.08, 2), round(price * 1.12, 2)]

    sl, tp1, tp2, tp3 = calc_sl_tp(price, atr, supports, resistances)

    ema_count = sum([price > ema_20, price > ema_50, price > ema_200]) if ema_200 else sum([price > ema_20, price > ema_50])
    if ema_count >= 2:
        trend = "BULLISH"
    elif ema_count == 1:
        trend = "NEUTRAL"
    else:
        trend = "BEARISH"

    if rsi > 65:
        trend_strength = "Strong"
    elif rsi > 55:
        trend_strength = "Moderate"
    elif rsi < 35:
        trend_strength = "Weak"
    else:
        trend_strength = "Neutral"

    sl_pct = ((sl - price) / price) * 100
    tp1_pct = ((tp1 - price) / price) * 100
    tp2_pct = ((tp2 - price) / price) * 100
    tp3_pct = ((tp3 - price) / price) * 100
    risk = abs(price - sl)
    rr1 = abs(tp1 - price) / risk if risk else 0
    rr2 = abs(tp2 - price) / risk if risk else 0
    rr3 = abs(tp3 - price) / risk if risk else 0

    recommended = "TP1"
    if rr3 >= 2.5:
        recommended = "TP3"
    elif rr2 >= 1.5:
        recommended = "TP2"

    pattern_names = [p[0] for p in candle_patterns]
    chart_names = [p[0] for p in chart_patterns]

    vol_note = ""
    if vol_ratio > 1.5:
        vol_note = f"Volume {vol_ratio:.1f}x avg -- high interest"
    elif vol_ratio < 0.5:
        vol_note = f"Volume {vol_ratio:.1f}x avg -- low liquidity"

    bull_case = _bull_case(trend, rsi, macd_line, macd_signal_val, price, ema_50, ema_200, tp1, tp2, tp3, pattern_names, chart_names, vol_ratio)
    bear_case = _bear_case(trend, rsi, macd_line, macd_signal_val, price, ema_50, ema_200, sl, pattern_names, chart_names)

    tf_note = []
    for tf, label, t, r, d in mtf_signals:
        emoji = "UP" if d == "UP" else "DOWN"
        tf_note.append(f"{tf}({label}): {t} RSI:{r} {emoji}")

    psych_notes = [
        "Max risk per trade: 1-2% of portfolio",
        "Set daily loss limit before trading",
        "Wait for confirmation -- don't chase price",
        "If stopped out, wait 1 hour minimum before re-entry",
        "Stick to the plan -- TP/SL are non-negotiable",
    ]
    if pattern_names:
        psych_notes.append(f"Candle patterns active: {', '.join(pattern_names)} -- confirm with higher TF")
    if chart_names:
        psych_notes.append(f"Chart patterns active: {', '.join(chart_names)} -- wait for breakout confirmation")

    return TradePlan(
        symbol=symbol,
        asset_type=asset_type,
        price=round(price, 2),
        trend=trend,
        trend_strength=trend_strength,
        support_levels=[round(s, 2) for s in supports],
        resistance_levels=[round(r, 2) for r in resistances],
        ema_20=round(ema_20, 2) if ema_20 else 0,
        ema_50=round(ema_50, 2) if ema_50 else 0,
        ema_200=round(ema_200, 2) if ema_200 else 0,
        rsi=round(rsi, 1),
        macd_line=round(macd_line, 2),
        macd_signal=round(macd_signal_val, 2),
        macd_histogram=round(macd_hist, 2),
        atr=round(atr, 2),
        atr_pct=round(atr_pct, 2),
        volume_ratio=round(vol_ratio, 2),
        bollinger_upper=round(bb_upper, 2),
        bollinger_lower=round(bb_lower, 2),
        bollinger_width_pct=round(bb_width, 2),
        bollinger_squeeze=bb_squeeze,
        obv=round(obv, 0),
        adx=round(adx, 1),
        adx_strength=adx_strength,
        candle_patterns=pattern_names,
        chart_patterns=chart_names,
        multi_tf_signal=tf_note,
        bull_case=bull_case,
        bear_case=bear_case,
        entry_price=round(price, 2),
        stop_loss=round(sl, 2),
        sl_pct=round(sl_pct, 2),
        take_profit_1=round(tp1, 2),
        tp1_pct=round(tp1_pct, 2),
        take_profit_2=round(tp2, 2),
        tp2_pct=round(tp2_pct, 2),
        take_profit_3=round(tp3, 2),
        tp3_pct=round(tp3_pct, 2),
        risk_reward_1=round(rr1, 2),
        risk_reward_2=round(rr2, 2),
        risk_reward_3=round(rr3, 2),
        recommended_rr=recommended,
        market_note=_market_note(asset_type, symbol),
        eco_calendar_note=get_week_ahead_note(),
        ai_predictions=current_predictions(df),
        psychology_notes=psych_notes,
    )


def _bull_case(trend, rsi, macd, macd_sig, price, ema50, ema200, tp1, tp2, tp3, candles, charts, vol):
    parts = []
    if trend == "BULLISH":
        parts.append("Price is in an uptrend with higher timeframes aligned")
    elif trend == "NEUTRAL":
        parts.append("Price is consolidating; a breakout above resistance would confirm bullish bias")
    if 30 <= rsi <= 70:
        parts.append(f"RSI at {rsi:.1f} -- not overbought, room for upside")
    if rsi < 30:
        parts.append(f"RSI at {rsi:.1f} -- oversold, bounce potential")
    if macd > macd_sig:
        parts.append("MACD above signal line -- bullish momentum")
    if price > ema50 and ema50:
        parts.append("Price above EMA 50 confirming medium-term strength")
    if vol > 1.5:
        parts.append("Volume is above average -- strong interest")
    for p in candles:
        parts.append(f"Candle: {p}")
    for p in charts:
        parts.append(f"Pattern: {p}")
    parts.append(f"Bullish targets: ${tp1:,.2f} -> ${tp2:,.2f} -> ${tp3:,.2f}")
    return ". ".join(parts)


def _bear_case(trend, rsi, macd, macd_sig, price, ema50, ema200, sl, candles, charts):
    parts = []
    if trend == "BEARISH":
        parts.append("Price is in a downtrend across timeframes")
    if rsi > 70:
        parts.append(f"RSI at {rsi:.1f} -- overbought, reversal possible")
    if macd < macd_sig:
        parts.append("MACD below signal line -- bearish momentum")
    if price < ema50 and ema50:
        parts.append("Price below EMA 50 signaling weakness")
    for p in candles:
        if "BEAR" in p or "EVENING" in p or "CROW" in p:
            parts.append(f"Bearish candle: {p}")
    for p in charts:
        if "BEAR" in p or "TOP" in p:
            parts.append(f"Bearish pattern: {p}")
    parts.append(f"Invalidation below ${sl:,.2f} could trigger further downside")
    return ". ".join(parts)


def _market_note(asset_type, symbol):
    if asset_type == "crypto":
        return (
            f"{symbol} is a cryptocurrency. Markets trade 24/7 with higher volatility. "
            f"Multi-TF analysis active (1d trend + 4h entry + 1h precision). "
            f"Monitor BTC dominance for altcoin direction. "
            f"Regulatory news (SEC, CFTC) can cause sudden moves."
        )
    return (
        f"{symbol} is a US stock. Market hours: 9:30-16:00 ET. "
        f"Volatility is lower (ATR% typically 0.5-2%). Monitor SPY for sector direction. "
        f"Earnings reports and macro data (CPI, FOMC) are major catalysts."
    )
