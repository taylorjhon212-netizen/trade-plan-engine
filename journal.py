import json
import os
from datetime import datetime

JOURNAL_FILE = "trades.json"


def _load():
    if not os.path.exists(JOURNAL_FILE):
        return []
    try:
        with open(JOURNAL_FILE) as f:
            return json.load(f)
    except:
        return []


def _save(data):
    with open(JOURNAL_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_trade(symbol, entry, sl, tp, size, reason=""):
    trades = _load()
    trades.append({
        "id": len(trades) + 1,
        "symbol": symbol.upper(),
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "size": size,
        "reason": reason,
        "status": "OPEN",
        "pnl": 0,
        "exit_price": None,
        "exit_date": None,
        "open_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    _save(trades)
    return trades[-1]


def close_trade(trade_id, exit_price):
    trades = _load()
    for t in trades:
        if t["id"] == trade_id and t["status"] == "OPEN":
            t["status"] = "CLOSED"
            t["exit_price"] = exit_price
            t["exit_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            t["pnl"] = round((exit_price - t["entry"]) * t["size"], 2)
            _save(trades)
            return t
    return None


def stats():
    trades = _load()
    closed = [t for t in trades if t["status"] == "CLOSED"]
    open_trades = [t for t in trades if t["status"] == "OPEN"]
    winners = [t for t in closed if t["pnl"] > 0]
    losers = [t for t in closed if t["pnl"] <= 0]
    total_pnl = sum(t["pnl"] for t in closed)
    win_rate = len(winners) / len(closed) * 100 if closed else 0
    avg_winner = sum(t["pnl"] for t in winners) / len(winners) if winners else 0
    avg_loser = sum(t["pnl"] for t in losers) / len(losers) if losers else 0

    return {
        "total_trades": len(closed),
        "open_trades": len(open_trades),
        "winners": len(winners),
        "losers": len(losers),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "avg_winner": round(avg_winner, 2),
        "avg_loser": round(avg_loser, 2),
        "profit_factor": round(abs(sum(t["pnl"] for t in winners) / sum(abs(t["pnl"]) for t in losers)), 2) if losers and sum(abs(t["pnl"]) for t in losers) > 0 else 0,
    }


def list_trades(limit=10):
    trades = _load()
    return trades[-limit:]
