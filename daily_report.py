from data import fetch_data
from analysis import generate_plan
from notifier import send_telegram
from config import CRYPTO_SYMBOLS, STOCK_SYMBOLS
from ecocal import get_week_ahead_note


def send_daily_report():
    lines = ["*DAILY MARKET REPORT*", ""]
    lines.append("*CRYPTO SCAN*")
    for sym in CRYPTO_SYMBOLS:
        df = fetch_data(sym)
        if df.empty:
            continue
        plan = generate_plan(sym, df)
        signal = "BUY" if plan.trend == "BULLISH" and plan.rsi < 70 else "SELL" if plan.trend == "BEARISH" and plan.rsi > 30 else "HOLD"
        lines.append(f"{sym}: ${plan.price:,.2f} | {plan.trend} | RSI {plan.rsi} | R:R 1:{plan.risk_reward_2} | {signal}")

    lines.append("")
    lines.append("*STOCK SCAN*")
    for sym in STOCK_SYMBOLS[:10]:
        df = fetch_data(sym)
        if df.empty:
            continue
        plan = generate_plan(sym, df)
        signal = "BUY" if plan.trend == "BULLISH" and plan.rsi < 70 else "SELL" if plan.trend == "BEARISH" and plan.rsi > 30 else "HOLD"
        lines.append(f"{sym}: ${plan.price:,.2f} | {plan.trend} | RSI {plan.rsi} | {signal}")

    econ = get_week_ahead_note()
    if econ:
        lines.append("")
        lines.append("*ECONOMIC CALENDAR*")
        lines.append(econ)

    msg = "\n".join(lines)
    if len(msg) > 4000:
        msg = msg[:4000] + "\n\n... (truncated)"

    ok = send_telegram(msg)
    print(f"Daily report sent: {ok}")
    return ok


if __name__ == "__main__":
    send_daily_report()
