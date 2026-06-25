import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from data import fetch_data
from analysis import generate_plan
from risk import RiskManager
from notifier import send_telegram
from config import CRYPTO_SYMBOLS, STOCK_SYMBOLS
import journal
from backtest import run_backtest
from scanner import scan_opportunities, scan_top_opportunities
import watchlist_import
import portfolio

console = Console()
risk_mgr = RiskManager()


def show_plan(symbol: str):
    with console.status(f"Fetching data for {symbol}..."):
        df = fetch_data(symbol)
    if df.empty:
        console.print(f"[red]No data for {symbol}[/red]")
        return

    plan = generate_plan(symbol, df)
    plan.position_size_usd = risk_mgr.position_size()
    plan.daily_loss_limit = risk_mgr.max_daily_loss

    header = Panel(
        f"[bold white]{plan.symbol}[/bold white]  |  "
        f"${plan.price:,.2f}  |  "
        f"[{'green' if plan.trend == 'BULLISH' else 'red' if plan.trend == 'BEARISH' else 'yellow'}]"
        f"{plan.trend} ({plan.trend_strength})[/]",
        title="TRADE PLAN",
        style="cyan",
    )
    console.print(header)

    console.print("\n[bold underline cyan]1. TECHNICAL ANALYSIS[/]")
    t = Table(show_header=False, box=None)
    t.add_column(style="yellow", width=20)
    t.add_column(style="white")
    t.add_row("Price", f"${plan.price:,.2f}")
    t.add_row("EMA 20", f"${plan.ema_20:,.2f} {'^' if plan.price > plan.ema_20 else 'v'}")
    t.add_row("EMA 50", f"${plan.ema_50:,.2f} {'^' if plan.price > plan.ema_50 else 'v'}")
    if plan.ema_200:
        t.add_row("EMA 200", f"${plan.ema_200:,.2f} {'^' if plan.price > plan.ema_200 else 'v'}")
    t.add_row("RSI (14)", str(plan.rsi))
    t.add_row("MACD Hist", str(plan.macd_histogram))
    t.add_row("ATR", f"${plan.atr:.2f} ({plan.atr_pct}%)")
    t.add_row("Volume", f"{plan.volume_ratio:.1f}x avg")
    console.print(t)

    console.print(f"\n[bold]Support:[/] [green]{', '.join(f'${v:,.2f}' for v in plan.support_levels)}[/]")
    console.print(f"[bold]Resistance:[/] [red]{', '.join(f'${v:,.2f}' for v in plan.resistance_levels)}[/]")

    if plan.candle_patterns:
        console.print(f"\n[bold yellow]Candle Patterns:[/] {', '.join(plan.candle_patterns)}")
    if plan.chart_patterns:
        console.print(f"[bold magenta]Chart Patterns:[/] {', '.join(plan.chart_patterns)}")
    if plan.multi_tf_signal:
        console.print(f"\n[bold cyan]Multi-TF:[/]")
        for s in plan.multi_tf_signal:
            color = "green" if "BULLISH" in s else "red" if "BEARISH" in s else "yellow"
            console.print(f"  [{color}]{s}[/]")

    console.print(f"\n[bold green]Bull:[/] {plan.bull_case}")
    console.print(f"[bold red]Bear:[/] {plan.bear_case}")

    console.print("\n[bold underline cyan]2. RISK / REWARD[/]")
    rr = Table(box=None)
    rr.add_column("Level", style="yellow", width=12)
    rr.add_column("Price", justify="right", width=16)
    rr.add_column("Change", justify="right", width=12)
    rr.add_column("R:R", justify="right", width=8)
    rr.add_row("Entry", f"${plan.entry_price:,.2f}", "-", "-")
    rr.add_row("SL", f"${plan.stop_loss:,.2f}", f"[red]{plan.sl_pct:+.2f}%[/]", "-")
    rr.add_row("TP1", f"${plan.take_profit_1:,.2f}", f"[green]{plan.tp1_pct:+.2f}%[/]", f"1:{plan.risk_reward_1}")
    rr.add_row("TP2", f"${plan.take_profit_2:,.2f}", f"[green]{plan.tp2_pct:+.2f}%[/]", f"1:{plan.risk_reward_2}")
    rr.add_row("TP3", f"${plan.take_profit_3:,.2f}", f"[green]{plan.tp3_pct:+.2f}%[/]", f"1:{plan.risk_reward_3}")
    rr.add_row("[bold]Recommended[/]", f"[bold]{plan.recommended_rr}[/]", "", f"[bold]1:{getattr(plan, f'risk_reward_{plan.recommended_rr[-1]}', '?')}[/]")
    console.print(rr)

    console.print("\n[bold underline cyan]3. MARKET STRUCTURE[/]")
    console.print(plan.market_note)

    if plan.eco_calendar_note:
        console.print(f"\n[bold yellow]Economic Calendar:[/]")
        for line in plan.eco_calendar_note.split("\n"):
            console.print(f"  {line}")

    if plan.ai_predictions:
        console.print(f"\n[bold magenta]AI Pattern Predictions:[/]")
        for p in plan.ai_predictions:
            console.print(f"  * {p}")

    console.print("\n[bold underline cyan]4. PSYCHOLOGY & MONEY MANAGEMENT[/]")
    console.print(f"[bold]Position Size:[/] ${plan.position_size_usd:,.2f} (max {plan.max_risk_pct*100:.0f}% risk)")
    console.print(f"[bold]Daily Loss Limit:[/] ${plan.daily_loss_limit:,.2f}")
    for note in plan.psychology_notes:
        console.print(f"  * {note}")

    console.print()
    _notify_telegram(plan)


def _notify_telegram(plan):
    lines = [f"*{plan.symbol}* ${plan.price:,.2f} | {plan.trend}"]
    lines.append(f"RSI:{plan.rsi} Vol:{plan.volume_ratio:.1f}x")
    if plan.candle_patterns:
        lines.append(f"Mum: {', '.join(plan.candle_patterns)}")
    if plan.chart_patterns:
        lines.append(f"Pattern: {', '.join(plan.chart_patterns)}")
    lines.append(f"SL:${plan.stop_loss:,.2f} TP1:${plan.take_profit_1:,.2f} TP2:${plan.take_profit_2:,.2f}")
    lines.append(f"R:R 1:{plan.risk_reward_1} / 1:{plan.risk_reward_2} / 1:{plan.risk_reward_3}")
    msg = "\n".join(lines)
    if send_telegram(msg):
        console.print("[dim]Telegram sent[/dim]")


def show_scan(asset_type: str):
    symbols = CRYPTO_SYMBOLS if asset_type == "crypto" else STOCK_SYMBOLS
    table = Table(title=f"{asset_type.upper()} SCAN")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("Trend", justify="center")
    table.add_column("RSI", justify="right")
    table.add_column("Vol", justify="right")
    table.add_column("Patterns", justify="center")
    table.add_column("Signal", justify="center")

    with console.status(f"Scanning {len(symbols)} assets..."):
        for sym in symbols:
            df = fetch_data(sym)
            if df.empty:
                table.add_row(sym, "[red]ERR[/]", "-", "-", "-", "-", "[red]ERR[/]")
                continue
            plan = generate_plan(sym, df)
            trend_color = "green" if plan.trend == "BULLISH" else "red" if plan.trend == "BEARISH" else "yellow"
            action = "[green]BUY[/]" if plan.trend == "BULLISH" and plan.rsi < 70 else "[red]SELL[/]" if plan.trend == "BEARISH" and plan.rsi > 30 else "HOLD"
            pats = "*" if plan.candle_patterns or plan.chart_patterns else ""
            table.add_row(
                sym,
                f"${plan.price:,.2f}",
                f"[{trend_color}]{plan.trend}[/]",
                str(plan.rsi),
                f"{plan.volume_ratio:.1f}x",
                pats,
                action,
            )
    console.print(table)


def show_journal(args):
    if args.action == "add":
        t = journal.add_trade(args.symbol, args.entry, args.sl, args.tp, args.size, args.reason or "")
        console.print(f"[green]Trade #{t['id']} opened: {t['symbol']} @ ${t['entry']}[/]")

    elif args.action == "close":
        t = journal.close_trade(args.id, args.exit_price)
        if t:
            color = "green" if t["pnl"] >= 0 else "red"
            console.print(f"[{color}]Trade #{t['id']} closed: PnL ${t['pnl']}[/]")
        else:
            console.print("[red]Trade not found or already closed[/]")

    elif args.action == "stats":
        s = journal.stats()
        console.print("[bold underline cyan]TRADE STATS[/]")
        tt = Table(show_header=False, box=None)
        tt.add_column(style="yellow", width=20)
        tt.add_column(style="white")
        tt.add_row("Total Trades", str(s["total_trades"]))
        tt.add_row("Open", str(s["open_trades"]))
        tt.add_row("Win Rate", f"{s['win_rate']}%")
        tt.add_row("Total PnL", f"${s['total_pnl']}")
        tt.add_row("Avg Winner", f"${s['avg_winner']}")
        tt.add_row("Avg Loser", f"${s['avg_loser']}")
        tt.add_row("Profit Factor", str(s["profit_factor"]))
        console.print(tt)

    elif args.action == "list":
        trades = journal.list_trades(limit=args.limit or 10)
        if not trades:
            console.print("[yellow]No trades yet[/]")
            return
        tt = Table(title="TRADE JOURNAL")
        tt.add_column("ID", justify="right")
        tt.add_column("Symbol")
        tt.add_column("Entry", justify="right")
        tt.add_column("Exit", justify="right")
        tt.add_column("PnL", justify="right")
        tt.add_column("Status")
        for t in reversed(trades):
            color = "green" if t["pnl"] > 0 else "red" if t["pnl"] < 0 else "white"
            tt.add_row(
                str(t["id"]), t["symbol"],
                f"${t['entry']:,.2f}",
                f"${t['exit_price']:,.2f}" if t["exit_price"] else "-",
                f"[{color}]${t['pnl']:,.2f}[/]" if t["pnl"] else "-",
                t["status"],
            )
        console.print(tt)


def show_backtest(symbol):
    with console.status(f"Backtesting {symbol}..."):
        result = run_backtest(symbol)
    if "error" in result:
        console.print(f"[red]{result['error']}[/]")
        return
    console.print(f"[bold underline cyan]BACKTEST: {result['symbol']}[/]")
    t = Table(show_header=False, box=None)
    t.add_column(style="yellow", width=20)
    t.add_column(style="white")
    t.add_row("Starting Balance", f"${result['initial_balance']:,.2f}")
    t.add_row("Final Balance", f"${result['final_balance']:,.2f}")
    t.add_row("Total Return", f"${result['total_return']:,.2f} ({result['return_pct']}%)")
    t.add_row("Total Trades", str(result["total_trades"]))
    t.add_row("Win Rate", f"{result['win_rate']}%")
    t.add_row("Avg Winner", f"${result['avg_winner']}")
    t.add_row("Avg Loser", f"${result['avg_loser']}")
    console.print(t)


def show_opportunities(asset_type: str, top_n: int = 10):
    symbols = CRYPTO_SYMBOLS if asset_type == "crypto" else STOCK_SYMBOLS
    with console.status(f"Scanning {len(symbols)} assets for opportunities..."):
        results = scan_opportunities(symbols, min_score=0)
    if not results:
        console.print("[yellow]No opportunities found[/]")
        return
    table = Table(title=f"TOP {min(top_n, len(results))} OPPORTUNITIES")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Action", justify="center")
    table.add_column("Trend")
    table.add_column("RSI", justify="right")
    table.add_column("R:R", justify="right")
    table.add_column("Reasons")
    for i, r in enumerate(results[:top_n], 1):
        score_color = "green" if r["score"] >= 75 else "yellow" if r["score"] >= 60 else "red"
        action_color = "green" if r["action"] == "BUY" else "red" if r["action"] == "SELL" else "white"
        table.add_row(
            str(i),
            r["symbol"],
            f"${r['price']:,.2f}",
            f"[{score_color}]{r['score']}[/]",
            f"[{action_color}]{r['action']}[/]",
            r["trend"],
            str(r["rsi"]),
            r["rr"],
            ", ".join(r["reasons"]),
        )
    console.print(table)


def show_portfolio():
    portfolio.auto_close_all()
    p = portfolio.get_overview()
    console.print("[bold underline cyan]PORTFOLIO[/]")
    t = Table(show_header=False, box=None)
    t.add_column(style="yellow", width=20)
    t.add_column(style="white")
    t.add_row("Balance", f"${p['balance']:,.2f}")
    t.add_row("Open Trades", str(p["open_trades"]))
    t.add_row("Total Closed", str(p["total_trades"]))
    t.add_row("Win Rate", f"{p['win_rate']}%")
    t.add_row("Total PnL", f"[green]${p['total_pnl']:,.2f}[/]" if p["total_pnl"] >= 0 else f"[red]${p['total_pnl']:,.2f}[/]")
    t.add_row("Avg Winner", f"${p['avg_winner']}")
    t.add_row("Avg Loser", f"${p['avg_loser']}")
    console.print(t)

    if p["open_details"]:
        console.print("\n[bold]OPEN POSITIONS:[/]")
        ot = Table()
        ot.add_column("ID", justify="right")
        ot.add_column("Symbol")
        ot.add_column("Entry", justify="right")
        ot.add_column("Current", justify="right")
        ot.add_column("PnL", justify="right")
        ot.add_column("Chg%", justify="right")
        ot.add_column("To SL%", justify="right")
        ot.add_column("To TP%", justify="right")
        for d in p["open_details"]:
            color = "green" if d["unrealized_pnl"] >= 0 else "red"
            ot.add_row(
                str(d["id"]), d["symbol"],
                f"${d['entry']:,.2f}", f"${d['current']:,.2f}",
                f"[{color}]${d['unrealized_pnl']:,.2f}[/]", f"{d['pct']:+.2f}%",
                f"{d['to_sl']:+.2f}%", f"{d['to_tp']:+.2f}%",
            )
        console.print(ot)


def show_watchlist_import(filepath: str):
    imported = watchlist_import.import_from_file(filepath)
    if not imported:
        console.print(f"[red]No symbols found in {filepath}[/]")
        return
    console.print(f"[green]Imported {len(imported)} symbols:[/]")
    for sym in imported[:20]:
        console.print(f"  [cyan]{sym}[/]")
    if len(imported) > 20:
        console.print(f"  ... and {len(imported) - 20} more")
    console.print("\nTo use this list, copy the symbols into [bold]config.py[/] CRYPTO_SYMBOLS or STOCK_SYMBOLS.")


def show_watchlist():
    console.print("[bold underline cyan]WATCHLIST[/]")
    console.print("Currently watching:")
    for sym in CRYPTO_SYMBOLS:
        console.print(f"  [cyan]{sym}[/]")
    for sym in STOCK_SYMBOLS:
        console.print(f"  [blue]{sym}[/]")
    console.print(f"\n[dim]Import: python cli.py watchlist import path/to/list.txt[/dim]")


def main():
    parser = argparse.ArgumentParser(description="Trade Plan Engine v2")
    sub = parser.add_subparsers(dest="command")

    p_plan = sub.add_parser("plan", help="Generate trade plan")
    p_plan.add_argument("symbol", default="BTCUSDT", nargs="?")

    p_scan = sub.add_parser("scan", help="Scan assets")
    p_scan.add_argument("type", default="crypto", nargs="?", choices=["crypto", "stock"])

    p_opp = sub.add_parser("opportunities", help="Find best trading opportunities")
    p_opp.add_argument("type", default="crypto", nargs="?", choices=["crypto", "stock"])
    p_opp.add_argument("--top", type=int, default=10)

    p_j = sub.add_parser("journal", help="Trade journal")
    p_j.add_argument("action", choices=["add", "close", "stats", "list"])
    p_j.add_argument("--symbol")
    p_j.add_argument("--entry", type=float)
    p_j.add_argument("--sl", type=float)
    p_j.add_argument("--tp", type=float)
    p_j.add_argument("--size", type=float, default=1)
    p_j.add_argument("--reason")
    p_j.add_argument("--id", type=int)
    p_j.add_argument("--exit-price", type=float, dest="exit_price")
    p_j.add_argument("--limit", type=int)

    p_bt = sub.add_parser("backtest", help="Backtest strategy")
    p_bt.add_argument("symbol", default="BTCUSDT", nargs="?")

    p_pf = sub.add_parser("portfolio", help="View paper trading portfolio")

    p_wl = sub.add_parser("watchlist", help="Show or import watchlist")
    p_wl_sub = p_wl.add_subparsers(dest="wl_action")
    p_wl_show = p_wl_sub.add_parser("show", help="Show current watchlist")
    p_wl_import = p_wl_sub.add_parser("import", help="Import watchlist from file")
    p_wl_import.add_argument("filepath", help="Path to text or CSV file")

    args = parser.parse_args()

    if args.command == "plan":
        show_plan(args.symbol.upper())
    elif args.command == "scan":
        show_scan(args.type)
    elif args.command == "opportunities":
        show_opportunities(args.type, args.top)
    elif args.command == "journal":
        show_journal(args)
    elif args.command == "backtest":
        show_backtest(args.symbol.upper())
    elif args.command == "portfolio":
        show_portfolio()
    elif args.command == "watchlist":
        if args.wl_action == "import":
            show_watchlist_import(args.filepath)
        else:
            show_watchlist()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
