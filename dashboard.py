import streamlit as st
from data import fetch_data
from analysis import generate_plan
from risk import RiskManager
from report import format_plan_markdown
from config import CRYPTO_SYMBOLS, STOCK_SYMBOLS
import portfolio as pf

st.set_page_config(page_title="Trade Plan Engine", layout="wide")
st.title("Trade Plan Engine")
st.caption("Automated technical analysis + risk/reward + psychology")

risk_mgr = RiskManager()

tab1, tab2, tab3, tab4 = st.tabs(["Single Asset", "Scanner", "Risk Panel", "Portfolio"])

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        symbol = st.text_input("Symbol", "BTCUSDT").upper()
        asset_type = "crypto" if symbol.endswith(("USDT", "USD", "USDC")) else "stock"
    with col2:
        run = st.button("Generate Plan", type="primary", use_container_width=True)

    if run or "last_symbol" in st.session_state:
        if run:
            st.session_state["last_symbol"] = symbol
        symbol = st.session_state["last_symbol"]
        with st.spinner(f"Analyzing {symbol}..."):
            df = fetch_data(symbol)
        if df.empty:
            st.error(f"No data for {symbol}")
        else:
            plan = generate_plan(symbol, df)
            plan.position_size_usd = risk_mgr.position_size()
            plan.daily_loss_limit = risk_mgr.max_daily_loss

            st.markdown(format_plan_markdown(plan))

with tab2:
    st.subheader("Multi-Asset Scanner")
    col1, col2 = st.columns(2)
    with col1:
        scan_type = st.selectbox("Asset Type", ["crypto", "stock"])
    with col2:
        scan_btn = st.button("Scan", type="primary", use_container_width=True)

    if scan_btn:
        symbols = CRYPTO_SYMBOLS if scan_type == "crypto" else STOCK_SYMBOLS
        results = []
        progress = st.progress(0)
        for i, sym in enumerate(symbols):
            df = fetch_data(sym)
            if not df.empty:
                plan = generate_plan(sym, df)
                results.append({
                    "Symbol": sym,
                    "Price": f"${plan.price:,.2f}",
                    "Trend": plan.trend,
                    "RSI": plan.rsi,
                    "R:R (TP2)": f"1:{plan.risk_reward_2}" if plan.risk_reward_2 else "—",
                })
            progress.progress((i + 1) / len(symbols))

        if results:
            st.dataframe(results, use_container_width=True)

with tab3:
    st.subheader("Risk Manager")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Kill Switch", type="secondary", use_container_width=True):
            risk_mgr.kill("MANUAL")
            st.warning("Trading DISABLED")
    with col2:
        if st.button("Enable Trading", type="primary", use_container_width=True):
            risk_mgr.enable()
            st.success("Trading ENABLED")
    with col3:
        st.metric("Balance", f"${risk_mgr.balance:,.2f}")

    status = risk_mgr.status()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Enabled", "ON" if status["enabled"] else "OFF")
    col2.metric("Daily PnL", f"${status['daily_pnl']:,.2f}")
    col3.metric("Loss Limit", f"${status['daily_loss_limit']:,.2f}")
    col4.metric("Trades Today", status["trades_today"])

with tab4:
    st.subheader("Paper Portfolio")
    pf.auto_close_all()
    ov = pf.get_overview()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Balance", f"${ov['balance']:,.2f}")
    c2.metric("Open Trades", ov["open_trades"])
    c3.metric("Win Rate", f"{ov['win_rate']}%")
    c4.metric("Total PnL", f"${ov['total_pnl']:,.2f}")
    c5.metric("Avg Win/Loss", f"${ov['avg_winner']} / ${ov['avg_loser']}")

    if ov["open_details"]:
        st.subheader("Open Positions")
        import pandas as pd
        st.dataframe(pd.DataFrame(ov["open_details"]), use_container_width=True)
