import pandas as pd
import yfinance as yf
from config import CRYPTO_TIMEFRAME, CRYPTO_CANDLE_RESAMPLE, STOCK_PERIOD, STOCK_INTERVAL, YAHOO_SYMBOL_MAP


CRYPTO_SUFFIXES = ("USDT", "USD", "USDC", "BUSD")
KNOWN_CRYPTO = {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "DOT", "AVAX", "LINK", "MATIC", "UNI", "ATOM"}


def detect_asset_type(symbol: str) -> str:
    s = symbol.upper()
    if s.endswith(CRYPTO_SUFFIXES) or s in KNOWN_CRYPTO:
        return "crypto"
    return "stock"


def _to_yahoo_symbol(symbol: str) -> str:
    s = symbol.upper()
    if s in YAHOO_SYMBOL_MAP:
        return YAHOO_SYMBOL_MAP[s]
    if s.endswith("USDT"):
        return s.replace("USDT", "-USD")
    if s.endswith("USDC"):
        return s.replace("USDC", "-USD")
    if s.endswith("BUSD"):
        return s.replace("BUSD", "-USD")
    if not s.endswith("USD") and s in KNOWN_CRYPTO:
        return f"{s}-USD"
    return s


def _resample_to_4h(df: pd.DataFrame) -> pd.DataFrame:
    if "time" not in df.columns:
        return df
    df = df.set_index("time").sort_index()
    ohlc = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    cols = [c for c in ohlc if c in df.columns]
    ohlc_filt = {k: v for k, v in ohlc.items() if k in cols}
    df = df.resample(CRYPTO_CANDLE_RESAMPLE, label="right", closed="right").agg(ohlc_filt).dropna()
    df = df.reset_index()
    return df


RESAMPLE_MAP = {"1d": None, "4h": "4h", "1h": None}


def fetch_data(symbol: str, force_interval: str = None) -> pd.DataFrame:
    asset_type = detect_asset_type(symbol)
    yahoo_sym = _to_yahoo_symbol(symbol)

    try:
        if force_interval == "1d":
            period = "6mo"
            interval = "1d"
            resample = None
        elif force_interval == "1h":
            period = "1mo"
            interval = "1h"
            resample = None
        else:
            if asset_type == "crypto":
                period = "2mo"
                interval = CRYPTO_TIMEFRAME
                resample = CRYPTO_CANDLE_RESAMPLE
            else:
                period = STOCK_PERIOD
                interval = STOCK_INTERVAL
                resample = None

        ticker = yf.Ticker(yahoo_sym)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            return df

        df = df.reset_index()
        cols = {c.lower().replace(" ", "_"): c for c in df.columns}
        df.rename(columns={v: k for k, v in cols.items()}, inplace=True)
        if "date" in df.columns:
            df.rename(columns={"date": "time"}, inplace=True)
        if "datetime" in df.columns:
            df.rename(columns={"datetime": "time"}, inplace=True)

        if resample:
            df = _resample_to_4h(df)

        return df
    except Exception:
        return pd.DataFrame()
