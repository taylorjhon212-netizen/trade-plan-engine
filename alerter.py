from data import fetch_data
from analysis import generate_plan
from notifier import send_telegram
from config import CRYPTO_SYMBOLS, STOCK_SYMBOLS
from ecocal import get_week_ahead_note


def check_alerts():
    alerts = []
    all_symbols = CRYPTO_SYMBOLS + STOCK_SYMBOLS[:20]

    for sym in all_symbols:
        df = fetch_data(sym)
        if df.empty:
            continue
        plan = generate_plan(sym, df)
        if plan.price == 0:
            continue

        reasons = []

        if plan.rsi < 30:
            reasons.append(f"RSI {plan.rsi} oversold")
        elif plan.rsi > 70:
            reasons.append(f"RSI {plan.rsi} overbought")

        if plan.volume_ratio > 1.5:
            reasons.append(f"Vol {plan.volume_ratio:.1f}x")

        if plan.macd_histogram > 0 and plan.macd_line > plan.macd_signal:
            reasons.append("MACD bullish cross")
        elif plan.macd_histogram < 0 and plan.macd_line < plan.macd_signal:
            reasons.append("MACD bearish cross")

        if plan.risk_reward_2 >= 2.0:
            reasons.append(f"R:R 1:{plan.risk_reward_2}")

        for p in plan.candle_patterns:
            reasons.append(f"Candle: {p}")
        for p in plan.chart_patterns:
            reasons.append(f"Chart: {p}")

        if reasons:
            alerts.append((sym, plan, reasons))

    return alerts


def format_alert(alert):
    sym, plan, reasons = alert
    return (
        f"*{sym}* ${plan.price:,.2f} | {plan.trend} | Vol {plan.volume_ratio:.1f}x\n"
        f"Entry: ${plan.entry_price:,.2f} SL: ${plan.stop_loss:,.2f}\n"
        f"TP: ${plan.take_profit_1:,.2f} / ${plan.take_profit_2:,.2f} / ${plan.take_profit_3:,.2f}\n"
        f"RSI:{plan.rsi} R:R 1:{plan.risk_reward_2}\n"
        f"Signals: {', '.join(reasons)}"
    )


def run():
    alerts = check_alerts()
    if not alerts:
        send_telegram("*No signals* -- no actionable alerts found.")
        return

    chunks = []
    current = f"*MARKET ALERTS* ({len(alerts)} signals)\n"

    for alert in alerts:
        text = "\n\n" + format_alert(alert)
        if len(current) + len(text) > 3500:
            chunks.append(current)
            current = "*MARKET ALERTS (cont)*"
        current += text
    chunks.append(current)

    econ = get_week_ahead_note()
    if econ:
        chunks.append(f"\n*ECONOMIC CALENDAR*\n{econ}")

    for chunk in chunks:
        send_telegram(chunk)
    print(f"Sent {len(alerts)} alerts in {len(chunks)} messages")


if __name__ == "__main__":
    run()
