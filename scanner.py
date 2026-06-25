from data import fetch_data
from analysis import generate_plan


def score_opportunity(plan) -> tuple:
    score = 50
    reasons = []

    if plan.trend == "BULLISH":
        score += 15
        reasons.append("bullish trend")
    elif plan.trend == "BEARISH":
        score -= 5

    if 30 <= plan.rsi <= 45:
        score += 10
        reasons.append("RSI oversold bounce zone")
    elif 55 <= plan.rsi <= 70:
        score += 5
        reasons.append("RSI momentum zone")
    elif plan.rsi < 25:
        score += 15
        reasons.append("RSI deeply oversold")

    if plan.macd_histogram > 0 and plan.macd_line > plan.macd_signal:
        score += 10
        reasons.append("MACD bullish cross")
    elif plan.macd_histogram < 0 and plan.macd_line < plan.macd_signal:
        score -= 5

    if plan.risk_reward_2 >= 2.0:
        score += 15
        reasons.append(f"high R:R 1:{plan.risk_reward_2}")
    elif plan.risk_reward_2 >= 1.5:
        score += 5
        reasons.append(f"good R:R 1:{plan.risk_reward_2}")

    if plan.adx >= 25:
        score += 10
        reasons.append(f"strong trend ADX {plan.adx:.1f}")
    elif plan.adx < 15:
        score -= 5
        reasons.append(f"weak trend ADX {plan.adx:.1f}")

    if plan.bollinger_squeeze:
        score += 5
        reasons.append("BB squeeze breakout potential")

    if plan.volume_ratio > 1.5:
        score += 10
        reasons.append("high volume")
    elif plan.volume_ratio < 0.3:
        score -= 5
        reasons.append("low volume warning")

    if plan.candle_patterns:
        for p in plan.candle_patterns:
            if "BULL" in p or "HAMMER" in p or "MORNING" in p:
                score += 8
                reasons.append(f"bullish candle: {p}")
            elif "BEAR" in p or "EVENING" in p or "CROW" in p:
                score -= 5

    if plan.chart_patterns:
        for p in plan.chart_patterns:
            if "CUP" in p or "BOTTOM" in p or "BULL" in p or "TRIANGLE" in p:
                score += 10
                reasons.append(f"chart pattern: {p}")
            elif "TOP" in p or "BEAR" in p or "CROW" in p or "HNS_TOP" in p:
                score -= 5

    up_count = sum(1 for s in plan.multi_tf_signal if "BULLISH" in s)
    down_count = sum(1 for s in plan.multi_tf_signal if "BEARISH" in s)
    if up_count == 3:
        score += 20
        reasons.append("all TFs bullish")
    elif up_count >= 2:
        score += 10
        reasons.append("2/3 TFs bullish")
    elif down_count == 3:
        score -= 10
    elif down_count >= 2:
        score -= 5

    score = max(0, min(100, score))
    return score, reasons


def scan_opportunities(symbols: list, min_score: int = 65):
    results = []
    for sym in symbols:
        df = fetch_data(sym)
        if df.empty:
            continue
        plan = generate_plan(sym, df)
        if plan.price == 0:
            continue
        sc, reasons = score_opportunity(plan)
        action = "BUY" if sc >= 65 and plan.trend == "BULLISH" else "SELL" if sc >= 65 and plan.trend == "BEARISH" else "WATCH"
        results.append({
            "symbol": sym,
            "price": plan.price,
            "score": sc,
            "action": action,
            "trend": plan.trend,
            "rsi": plan.rsi,
            "adx": round(plan.adx, 1),
            "rr": f"1:{plan.risk_reward_2}",
            "patterns": plan.candle_patterns + plan.chart_patterns,
            "reasons": reasons[:3],
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def scan_top_opportunities(symbols: list, top_n: int = 5):
    results = scan_opportunities(symbols, min_score=0)
    return results[:top_n]
