from fastapi import FastAPI, Query, Request
from data import fetch_data
from analysis import generate_plan
from risk import RiskManager
from report import format_plan_text, format_plan_markdown
from config import CRYPTO_SYMBOLS, STOCK_SYMBOLS
from notifier import send_telegram

app = FastAPI(title="Trade Plan API", version="2.0")
risk_mgr = RiskManager()


@app.get("/plan")
def get_plan(
    symbol: str = Query("BTCUSDT", description="Asset symbol"),
    format: str = Query("json", description="Output format: json, text, markdown"),
):
    df = fetch_data(symbol)
    if df.empty:
        return {"error": f"No data for {symbol}"}
    plan = generate_plan(symbol, df)
    plan.position_size_usd = risk_mgr.position_size()
    plan.daily_loss_limit = risk_mgr.max_daily_loss
    plan.cooldown_seconds = risk_mgr.cooldown

    if format == "text":
        return {"plan": format_plan_text(plan)}
    if format == "markdown":
        return {"plan": format_plan_markdown(plan)}
    return plan.to_dict()


@app.get("/scan")
def scan_assets(type: str = Query("crypto", description="crypto or stock")):
    symbols = CRYPTO_SYMBOLS if type == "crypto" else STOCK_SYMBOLS
    results = []
    for sym in symbols:
        df = fetch_data(sym)
        if df.empty:
            results.append({"symbol": sym, "error": "NO_DATA"})
            continue
        plan = generate_plan(sym, df)
        results.append({
            "symbol": sym,
            "price": plan.price,
            "trend": plan.trend,
            "rsi": plan.rsi,
            "rr2": plan.risk_reward_2,
            "action": "BUY" if plan.trend == "BULLISH" and plan.rsi < 70 else "SELL" if plan.trend == "BEARISH" and plan.rsi > 30 else "HOLD",
        })
    return {"count": len(results), "results": results}


@app.get("/risk/status")
def risk_status():
    return risk_mgr.status()


@app.get("/risk/kill")
def kill_switch():
    risk_mgr.kill("MANUAL")
    return {"status": "KILLED", "trading_enabled": False}


@app.get("/risk/enable")
def enable_trading():
    risk_mgr.enable()
    return {"status": "ENABLED", "trading_enabled": True}


@app.post("/webhook/tradingview")
async def tradingview_webhook(request: Request):
    try:
        body = await request.json()
    except:
        body = {}

    symbol = body.get("symbol", body.get("ticker", "BTCUSDT"))
    action = body.get("action", body.get("side", "BUY"))
    price = body.get("price", body.get("close", 0))

    msg = (
        f"*TradingView Alert*\n"
        f"{symbol} | {action}\n"
        f"Price: ${float(price):,.2f}" if price else f"{symbol} | {action}"
    )
    send_telegram(msg)

    df = fetch_data(symbol)
    if df.empty:
        return {"status": "alert_received", "plan": None}

    plan = generate_plan(symbol, df)
    return {
        "status": "alert_received",
        "symbol": symbol,
        "action": action,
        "signal": plan.trend,
        "rsi": plan.rsi,
        "rr2": plan.risk_reward_2,
    }


@app.get("/")
def root():
    return {
        "service": "Trade Plan Engine v2",
        "endpoints": {
            "/plan": "GET ?symbol=BTCUSDT&format=json|text|markdown",
            "/scan": "GET ?type=crypto|stock",
            "/risk/status": "GET",
            "/risk/kill": "GET",
            "/risk/enable": "GET",
            "/webhook/tradingview": "POST (JSON: symbol, action, price)",
        }
    }
