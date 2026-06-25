import json
import os
from datetime import datetime
from data import fetch_data

PORTFOLIO_FILE = "portfolio.json"


def _load():
    if not os.path.exists(PORTFOLIO_FILE):
        default = {"balance": 10000, "trades": [], "trade_id": 0}
        _save(default)
        return default
    try:
        with open(PORTFOLIO_FILE) as f:
            return json.load(f)
    except:
        return {"balance": 10000, "trades": [], "trade_id": 0}


def _save(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=2)


def open_trade(symbol, entry_price, sl, tp, size, reason=""):
    data = _load()
    data["trade_id"] += 1
    data["trades"].append({
        "id": data["trade_id"],
        "symbol": symbol.upper(),
        "entry": entry_price,
        "sl": sl,
        "tp": tp,
        "size": size,
        "reason": reason,
        "open_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "OPEN",
    })
    _save(data)
    return data["trades"][-1]


def close_trade(trade_id):
    data = _load()
    for t in data["trades"]:
        if t["id"] == trade_id and t["status"] == "OPEN":
            df = fetch_data(t["symbol"])
            if df.empty:
                return None, "NO_DATA"
            current_price = float(df["close"].iloc[-1])
            pnl = (current_price - t["entry"]) * t["size"]
            data["balance"] += pnl
            t["status"] = "CLOSED"
            t["exit_price"] = current_price
            t["pnl"] = round(pnl, 2)
            t["close_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            _save(data)
            return t, None
    return None, "NOT_FOUND"


def auto_close_all():
    data = _load()
    closed = []
    for t in data["trades"]:
        if t["status"] == "OPEN":
            df = fetch_data(t["symbol"])
            if df.empty:
                continue
            price = float(df["close"].iloc[-1])
            hit_sl = price <= t["sl"]
            hit_tp = price >= t["tp"]
            if hit_sl or hit_tp:
                pnl = (price - t["entry"]) * t["size"]
                data["balance"] += pnl
                t["status"] = "CLOSED"
                t["exit_price"] = price
                t["pnl"] = round(pnl, 2)
                t["close_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                t["exit_reason"] = "SL" if hit_sl else "TP"
                closed.append(t)
    if closed:
        _save(data)
    return closed


def get_overview():
    data = _load()
    open_trades = [t for t in data["trades"] if t["status"] == "OPEN"]
    closed = [t for t in data["trades"] if t["status"] == "CLOSED"]
    winners = [t for t in closed if t["pnl"] > 0]
    losers = [t for t in closed if t["pnl"] <= 0]

    total_pnl = sum(t["pnl"] for t in closed)
    win_rate = round(len(winners) / len(closed) * 100, 1) if closed else 0

    open_details = []
    for t in open_trades:
        df = fetch_data(t["symbol"])
        if df.empty:
            continue
        price = float(df["close"].iloc[-1])
        unrealized = round((price - t["entry"]) * t["size"], 2)
        pct = round((price - t["entry"]) / t["entry"] * 100, 2)
        distance_to_sl = round((price - t["sl"]) / t["entry"] * 100, 2)
        distance_to_tp = round((t["tp"] - price) / t["entry"] * 100, 2)
        open_details.append({
            "id": t["id"],
            "symbol": t["symbol"],
            "entry": t["entry"],
            "current": round(price, 2),
            "size": t["size"],
            "unrealized_pnl": unrealized,
            "pct": pct,
            "sl": t["sl"],
            "tp": t["tp"],
            "to_sl": distance_to_sl,
            "to_tp": distance_to_tp,
        })

    avg_winner = round(sum(t["pnl"] for t in winners) / len(winners), 2) if winners else 0
    avg_loser = round(sum(t["pnl"] for t in losers) / len(losers), 2) if losers else 0

    return {
        "balance": round(data["balance"], 2),
        "open_trades": len(open_trades),
        "total_trades": len(closed),
        "winners": len(winners),
        "losers": len(losers),
        "win_rate": win_rate,
        "total_pnl": round(total_pnl, 2),
        "avg_winner": avg_winner,
        "avg_loser": avg_loser,
        "open_details": open_details,
    }
