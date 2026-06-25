import numpy as np
import pandas as pd


def detect_candle_patterns(df: pd.DataFrame) -> list:
    if df.empty or len(df) < 3:
        return []
    o = float(df["open"].iloc[-1])
    h = float(df["high"].iloc[-1])
    l = float(df["low"].iloc[-1])
    c = float(df["close"].iloc[-1])
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    total = h - l
    if total == 0:
        return []

    patterns = []

    if body <= total * 0.08:
        patterns.append(("DOJI", "Indecision; potential reversal"))
    elif body <= total * 0.15 and upper < body * 0.3 and lower > body * 2:
        patterns.append(("HAMMER", "Bullish reversal at support"))
    elif body <= total * 0.15 and lower < body * 0.3 and upper > body * 2:
        patterns.append(("SHOOTING_STAR", "Bearish reversal at resistance"))
    elif c > o and body > total * 0.6:
        patterns.append(("MARUBOZU", "Strong directional candle"))

    if len(df) >= 2:
        po = float(df["open"].iloc[-2])
        ph = float(df["high"].iloc[-2])
        pl = float(df["low"].iloc[-2])
        pc = float(df["close"].iloc[-2])
        pbody = abs(pc - po)

        if c > o and pc < po and c > po and o > pc:
            patterns.append(("BULLISH_ENGULF", "Strong bullish reversal"))
        elif c < o and pc > po and c < po and o < pc:
            patterns.append(("BEARISH_ENGULF", "Strong bearish reversal"))
        elif c > o and body > total * 0.4 and pbody > 0 and pc > po:
            patterns.append(("CONFIRM_BAR", "Follow-through buying"))

        if c < o and pc > po and o < pc and c > pl:
            patterns.append(("PIN_BAR_BULL", "Rejection of lows, potential bounce"))
        elif c > o and pc < po and o > pc and c < ph:
            patterns.append(("PIN_BAR_BEAR", "Rejection of highs, potential drop"))

    if len(df) >= 3:
        o3 = float(df["open"].iloc[-3])
        c3 = float(df["close"].iloc[-3])
        o2 = float(df["open"].iloc[-2])
        c2 = float(df["close"].iloc[-2])
        o1 = float(df["open"].iloc[-1])
        c1 = float(df["close"].iloc[-1])

        if c3 < o3 and abs(c2 - o2) <= (float(df["high"].iloc[-2]) - float(df["low"].iloc[-2])) * 0.1 and c1 > o1:
            patterns.append(("MORNING_STAR", "Bullish reversal (3-candle)"))
        elif c3 > o3 and abs(c2 - o2) <= (float(df["high"].iloc[-2]) - float(df["low"].iloc[-2])) * 0.1 and c1 < o1:
            patterns.append(("EVENING_STAR", "Bearish reversal (3-candle)"))

        w1_low = min(o3, c3)
        w1_high = max(o3, c3)
        w2_low = min(o2, c2)
        w2_high = max(o2, c2)
        w3_low = min(o1, c1)
        w3_high = max(o1, c1)

        if w1_high < w2_low and w2_high < w3_low and c3 < o3 and c2 < o2 and c1 > o1:
            patterns.append(("THREE_WHITE_SOLDIERS", "Strong bullish continuation"))
        elif w1_low > w2_high and w2_low > w3_high and c3 > o3 and c2 > o2 and c1 < o1:
            patterns.append(("THREE_BLACK_CROWS", "Strong bearish continuation"))

    return patterns


def detect_chart_patterns(df: pd.DataFrame) -> list:
    if df.empty or len(df) < 40:
        return []

    close = df["close"].values.astype(float)
    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    patterns = []
    n = len(close)

    wins = [n // 4, n // 3, n // 2]
    for w in wins:
        if w < 10:
            continue
        h_roll = pd.Series(high).rolling(w, center=True).max().values
        l_roll = pd.Series(low).rolling(w, center=True).min().values

        pks = np.where((high == h_roll) & ~np.isnan(h_roll))[0]
        trs = np.where((low == l_roll) & ~np.isnan(l_roll))[0]

        if len(pks) >= 2:
            for i in range(len(pks) - 1):
                p1, p2 = pks[i], pks[i + 1]
                if abs(p2 - p1) < 5:
                    continue
                if abs(high[p1] - high[p2]) / max(high[p1], high[p2]) < 0.02:
                    mid = (p1 + p2) // 2
                    trough = low[p1:p2].min()
                    if trough < close[p1] * 0.9 and close[-1] > max(high[p1], high[p2]):
                        patterns.append(("DOUBLE_BOTTOM", f"Bullish reversal at ${trough:,.2f}"))
                    elif close[-1] < min(high[p1], high[p2]) * 1.02:
                        patterns.append(("DOUBLE_TOP", f"Bearish rejection at ${high[p1]:,.2f}"))

        if len(pks) >= 3:
            for i in range(len(pks) - 2):
                lpk, mpk, rpk = pks[i], pks[i + 1], pks[i + 2]
                if abs(mpk - lpk) < 5 or abs(rpk - mpk) < 5:
                    continue
                if high[mpk] > high[lpk] and high[mpk] > high[rpk]:
                    if abs(high[lpk] - high[rpk]) / max(high[lpk], high[rpk]) < 0.03:
                        neckline = (high[lpk] + high[rpk]) / 2
                        patterns.append(("HNS_TOP", f"Head & shoulders at ${high[mpk]:,.2f}, neck ${neckline:,.2f}"))

        if len(trs) >= 3:
            for i in range(len(trs) - 2):
                ltr, mtr, rtr = trs[i], trs[i + 1], trs[i + 2]
                if abs(mtr - ltr) < 5 or abs(rtr - mtr) < 5:
                    continue
                if low[mtr] < low[ltr] and low[mtr] < low[rtr]:
                    if abs(low[ltr] - low[rtr]) / max(low[ltr], low[rtr]) < 0.03:
                        neckline = (low[ltr] + low[rtr]) / 2
                        patterns.append(("HNS_BOTTOM", f"Inv H&S at ${low[mtr]:,.2f}, neck ${neckline:,.2f}"))

    if n >= 40:
        mid = n // 2
        left = close[:mid]
        right = close[mid:]
        left_high = left.max()
        left_high_idx = left.argmax()
        left_low = left.min()
        right_low = right.min()
        right_now = close[-1]

        cup_depth = (left_high - left_low) / left_high
        if 0.1 < cup_depth < 0.5 and right_low > left_low * 0.95:
            if right_now > left_high * 0.95:
                patterns.append(("CUP_HANDLE", f"Bullish cup & handle near breakout ${left_high:,.2f}"))

    if n >= 20:
        recent = close[-20:]
        highs = pd.Series(recent).rolling(5, center=True).max().values
        lows = pd.Series(recent).rolling(5, center=True).min().values
        highs = highs[~np.isnan(highs)]
        lows = lows[~np.isnan(lows)]
        if len(highs) < 3 or len(lows) < 3:
            pass
        else:
            h_line = np.mean(highs)
            l_line = np.mean(lows)
            h_touches = int(np.sum(abs(highs - h_line) / h_line < 0.01))
            l_touches = int(np.sum(abs(lows - l_line) / l_line < 0.01))

            if h_touches >= 3 and l_touches >= 2 and abs(h_line - l_line) / h_line > 0.02:
                if close[-1] > h_line:
                    patterns.append(("ASCENDING_TRIANGLE", f"Breakout above ${h_line:,.2f} resistance"))
                elif close[-1] < l_line:
                    patterns.append(("DESCENDING_TRIANGLE", f"Breakdown below ${l_line:,.2f} support"))

    if n >= 15:
        recent_c = close[-15:]
        recent_h = high[-15:]
        recent_l = low[-15:]
        move = abs(recent_c[-1] - recent_c[0]) / recent_c[0]
        if move > 0.08:
            pole_high = recent_h.max()
            pole_low = recent_l.min()
            consolidation = recent_c[-8:]
            range_pct = (consolidation.max() - consolidation.min()) / consolidation.min()
            if range_pct < 0.05:
                if recent_c[-1] > recent_c[-8]:
                    patterns.append(("BULL_FLAG", f"Bull flag, target ${pole_high + (pole_high - pole_low):,.2f}"))
                else:
                    patterns.append(("BEAR_FLAG", f"Bear flag, target ${pole_low - (pole_high - pole_low):,.2f}"))

    return patterns
