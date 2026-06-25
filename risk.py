import time
from config import DEFAULT_BALANCE, MAX_RISK_PCT, MAX_DAILY_LOSS_PCT, COOLDOWN_SECONDS


class RiskManager:
    def __init__(self, balance: float = DEFAULT_BALANCE):
        self.balance = balance
        self.enabled = True
        self.daily_pnl = 0.0
        self.max_daily_loss = balance * MAX_DAILY_LOSS_PCT
        self.cooldown = COOLDOWN_SECONDS
        self.last_trade_time = 0.0
        self.trade_count = 0
        self.max_trades_per_day = 5
        self.daily_reset_time = time.time()

    def can_trade(self) -> tuple:
        self._maybe_reset_daily()
        if not self.enabled:
            return False, "TRADING_DISABLED"
        if self.daily_pnl <= -self.max_daily_loss:
            self.kill("MAX_DAILY_LOSS_REACHED")
            return False, "MAX_DAILY_LOSS"
        if self.trade_count >= self.max_trades_per_day:
            return False, "MAX_TRADES_REACHED"
        if time.time() - self.last_trade_time < self.cooldown:
            return False, "COOLDOWN"
        return True, "OK"

    def kill(self, reason="MANUAL"):
        self.enabled = False

    def enable(self):
        self.enabled = True
        self.daily_pnl = 0.0
        self.trade_count = 0

    def position_size(self, risk_pct: float = None) -> float:
        pct = risk_pct or MAX_RISK_PCT
        return self.balance * pct

    def register_trade(self, pnl: float = 0.0):
        self.last_trade_time = time.time()
        self.trade_count += 1
        self.daily_pnl += pnl

    def _maybe_reset_daily(self):
        now = time.time()
        if now - self.daily_reset_time > 86400:
            self.daily_pnl = 0.0
            self.trade_count = 0
            self.daily_reset_time = now

    def status(self) -> dict:
        self._maybe_reset_daily()
        return {
            "enabled": self.enabled,
            "balance": round(self.balance, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "daily_loss_limit": round(-self.max_daily_loss, 2),
            "trades_today": self.trade_count,
            "cooldown_active": time.time() - self.last_trade_time < self.cooldown,
        }
