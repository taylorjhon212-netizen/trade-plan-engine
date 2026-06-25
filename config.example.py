import os

CRYPTO_TIMEFRAME = "1h"
CRYPTO_LIMIT = 200
CRYPTO_CANDLE_RESAMPLE = "4h"

STOCK_PERIOD = "6mo"
STOCK_INTERVAL = "1d"

DEFAULT_BALANCE = 10_000
MAX_RISK_PCT = 0.02
MAX_DAILY_LOSS_PCT = 0.05
COOLDOWN_SECONDS = 30
MAX_TRADE_SIZE_PCT = 0.05

CRYPTO_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
    "AVAXUSDT", "UNIUSDT",
    "ARKMUSDT", "WLDUSDT", "ALLOUSDT", "GRTUSDT",
    "RENDERUSDT", "JUPUSDT", "ASTRUSDT", "IDUSDT", "RDNTUSDT",
    "BNBUSDT", "DOGEUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT",
    "TRXUSDT", "SHIBUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT",
    "OPUSDT", "ARBUSDT", "LTCUSDT", "BCHUSDT", "FILUSDT",
    "ATOMUSDT", "ETCUSDT", "XLMUSDT", "STXUSDT", "INJUSDT",
    "SEIUSDT", "FETUSDT", "PEPEUSDT", "FLOKIUSDT", "WIFUSDT",
    "BONKUSDT", "RUNEUSDT", "THETAUSDT", "SANDUSDT", "MANAUSDT",
    "AXSUSDT", "EOSUSDT",
]

STOCK_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "JPM", "V", "JNJ",
    "WMT", "PG", "MA", "UNH", "HD",
    "DIS", "NFLX", "ADBE", "CRM", "INTC",
    "BRK.B", "LLY", "AVGO", "COST", "ABBV",
    "ORCL", "AMD", "ACN", "QCOM", "CSCO",
    "INTU", "AMAT", "TXN", "IBM", "BA",
    "CAT", "MCD", "NKE", "KO", "PEP",
    "MRK", "ABT", "TMO", "MDT", "UNP",
    "HON", "LMT", "GE", "UPS", "BAC",
    "WFC", "GS", "CVX", "XOM", "LIN",
]

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or ""
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID") or ""

COINBASE_KEY_NAME = os.environ.get("COINBASE_KEY_NAME") or ""
COINBASE_PRIVATE_KEY = os.environ.get("COINBASE_PRIVATE_KEY") or ""

CRYPTO_COINGECKO_ID = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple",
    "AVAX": "avalanche-2", "UNI": "uniswap", "ARKM": "arkham", "WLD": "worldcoin-wld",
    "ALLO": "allori", "GRT": "the-graph", "RENDER": "render-token", "JUP": "jupiter",
    "ASTR": "astar", "ID": "space-id", "RDNT": "radiant-capital", "BNB": "binancecoin",
    "DOGE": "dogecoin", "ADA": "cardano", "DOT": "polkadot", "LINK": "chainlink",
    "TRX": "tron", "SHIB": "shiba-inu", "NEAR": "near", "APT": "aptos",
    "SUI": "sui", "OP": "optimism", "ARB": "arbitrum", "LTC": "litecoin",
    "BCH": "bitcoin-cash", "FIL": "filecoin", "ATOM": "cosmos", "ETC": "ethereum-classic",
    "XLM": "stellar", "STX": "stacks", "INJ": "injective-protocol", "SEI": "sei-network",
    "FET": "fetch-ai", "PEPE": "pepe", "FLOKI": "floki", "WIF": "dogwifcoin",
    "BONK": "bonk", "RUNE": "thorchain", "THETA": "theta-token", "SAND": "the-sandbox",
    "MANA": "decentraland", "AXS": "axie-infinity", "EOS": "eos",
}

YAHOO_SYMBOL_MAP = {}
