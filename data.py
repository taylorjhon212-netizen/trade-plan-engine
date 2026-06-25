import pandas as pd
import requests
import yfinance as yf
import jwt as pyjwt
import time as time_mod
from config import CRYPTO_TIMEFRAME, CRYPTO_CANDLE_RESAMPLE, STOCK_PERIOD, STOCK_INTERVAL, CRYPTO_COINGECKO_ID, YAHOO_SYMBOL_MAP, COINBASE_KEY_NAME, COINBASE_PRIVATE_KEY

CRYPTO_SUFFIXES = ("USDT", "USD", "USDC", "BUSD")
KNOWN_CRYPTO = {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "DOT", "AVAX", "LINK", "MATIC", "UNI", "ATOM"}

CG_BASE = "https://api.coingecko.com/api/v3"
CB_BASE = "https://api.coinbase.com/api/v3/brokerage"


def detect_asset_type(symbol: str) -> str:
    s = symbol.upper()
    if s.endswith(CRYPTO_SUFFIXES) or s in KNOWN_CRYPTO:
        return "crypto"
    return "stock"


def _to_cb_symbol(symbol: str) -> str:
    s = symbol.upper()
    for suffix in ["USDT", "USDC", "BUSD", "USD"]:
        if s.endswith(suffix):
            s = s[:-len(suffix)]
            break
    return f"{s}-USD"


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


def _cg_id(symbol: str) -> str:
    s = symbol.upper().replace("USDT", "").replace("USDC", "").replace("BUSD", "").replace("USD", "").strip()
    return CRYPTO_COINGECKO_ID.get(s, s.lower())


def _cb_jwt(uri: str) -> str:
    payload = {
        "iss": "coinbase-cloud",
        "sub": COINBASE_KEY_NAME,
        "iat": int(time_mod.time()),
        "exp": int(time_mod.time()) + 120,
        "uri": uri,
    }
    return pyjwt.encode(payload, COINBASE_PRIVATE_KEY, algorithm="ES256")


def _fetch_coinbase(symbol: str, granularity: str = "ONE_HOUR", limit: int = 300) -> pd.DataFrame:
    if not COINBASE_KEY_NAME or not COINBASE_PRIVATE_KEY:
        return pd.DataFrame()
    cb_sym = _to_cb_symbol(symbol)
    uri = f"/api/v3/brokerage/products/{cb_sym}/candles?granularity={granularity}&limit={limit}"
    url = f"{CB_BASE}/products/{cb_sym}/candles?granularity={granularity}&limit={limit}"
    try:
        token = _cb_jwt(uri)
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if r.status_code != 200:
            return pd.DataFrame()
        data = r.json().get("candles", [])
        if not data:
            return pd.DataFrame()
        rows = []
        for c in data:
            rows.append({
                "time": pd.to_datetime(c["start"]),
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "volume": float(c["volume"]),
            })
        df = pd.DataFrame(rows).sort_values("time").reset_index(drop=True)
        return df
    except Exception:
        return pd.DataFrame()


def _fetch_coingecko(symbol: str, days: int = 30) -> pd.DataFrame:
    cg_id = _cg_id(symbol)
    url = f"{CG_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return pd.DataFrame()
        data = r.json()
        if not data or not isinstance(data, list):
            return pd.DataFrame()
        df = pd.DataFrame(data, columns=["time", "open", "high", "low", "close"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df["volume"] = 0
        return df
    except Exception:
        return pd.DataFrame()


def _fetch_yahoo(symbol: str, period: str, interval: str) -> pd.DataFrame:
    yahoo_sym = _to_yahoo_symbol(symbol)
    try:
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
        return df
    except Exception:
        return pd.DataFrame()


def _resample_to_4h(df: pd.DataFrame) -> pd.DataFrame:
    if "time" not in df.columns:
        return df
    df = df.set_index("time").sort_index()
    ohlc = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    cols = [c for c in ohlc if c in df.columns]
    ohlc_filt = {k: v for k, v in ohlc.items() if k in cols}
    df = df.resample(CRYPTO_CANDLE_RESAMPLE, label="right", closed="right").agg(ohlc_filt).dropna()
    df = df.reset_index()
    return df


GRANULARITY_MAP = {"1d": "ONE_DAY", "4h": "SIX_HOUR", "1h": "ONE_HOUR"}


def fetch_data(symbol: str, force_interval: str = None) -> pd.DataFrame:
    asset_type = detect_asset_type(symbol)

    if force_interval == "1d":
        period, interval = "6mo", "1d"
    elif force_interval == "1h":
        period, interval = "1mo", "1h"
    else:
        period, interval = STOCK_PERIOD, STOCK_INTERVAL

    if asset_type == "crypto":
        cb_gran = GRANULARITY_MAP.get(force_interval or "4h", "ONE_HOUR")
        cb_limit = 300
        df = _fetch_coinbase(symbol, granularity=cb_gran, limit=cb_limit)
        if not df.empty:
            if not force_interval and CRYPTO_CANDLE_RESAMPLE == "4h" and cb_gran != "SIX_HOUR":
                df = _resample_to_4h(df)
            return df

    df = _fetch_yahoo(symbol, period, interval)
    if not df.empty:
        if not force_interval and asset_type == "crypto" and CRYPTO_CANDLE_RESAMPLE:
            df = _resample_to_4h(df)
        return df

    if asset_type == "crypto":
        cg_days = 30
        if force_interval == "1d":
            cg_days = 365
        elif force_interval == "1h":
            cg_days = 1
        df = _fetch_coingecko(symbol, days=cg_days)
        return df

    return df
