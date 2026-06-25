from scanner import scan_top_opportunities
from notifier import send_telegram
from config import CRYPTO_SYMBOLS


def run():
    top = scan_top_opportunities(CRYPTO_SYMBOLS, top_n=5)
    if not top:
        send_telegram("*No opportunities found*")
        return

    lines = ["*TOP CRYPTO OPPORTUNITIES*", ""]
    for i, r in enumerate(top, 1):
        lines.append(
            f"{i}. *{r['symbol']}* ${r['price']:,.2f} | Score: {r['score']}\n"
            f"   {r['action']} | {r['trend']} | RSI:{r['rsi']} | R:R {r['rr']}\n"
            f"   {', '.join(r['reasons'][:2])}"
        )
    msg = "\n".join(lines)
    send_telegram(msg)
    print("Opportunities sent")


if __name__ == "__main__":
    run()
