import argparse
import hashlib
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from numba import njit

START_BALANCE = 1000.0
TARGET = 10.0
COMMISSION = 0.07
LEVERAGE = 2000.0
BASE_STEP = 1.0  # normalized: current PH1 $1 XAU move = user's 10-pip base step
MAX_NEG_DAYS = 400

METHODS = [
    "ROLL60_BREAKOUT",
    "EMA_PULLBACK_RECLAIM",
    "MOMENTUM_5M_IMPULSE",
    "COMPRESSION_BREAKOUT",
    "ZSCORE_MEAN_REVERSION",
    "ZIGZAG_SWING_REVERSAL",
    "LIQUIDITY_SWEEP_REJECTION",
    "BREAK_RETEST_REBREAK",
    "EFFICIENCY_TREND",
    "RSI14_EXTREME_REVERSAL",
]


def download(url, out):
    h = hashlib.sha256()
    total = 0
    with requests.get(url, stream=True, timeout=(30, 300)) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
                    h.update(chunk)
                    total += len(chunk)
    return total, h.hexdigest()


def day_to_iso(day_key):
    if int(day_key) < 0:
        return ""
    return str(pd.Timestamp("1970-01-01", tz="UTC") + pd.Timedelta(days=int(day_key)))[:10]


def aggregate_zip_to_minutes(path, year, month):
    parts = []
    with zipfile.ZipFile(path) as z:
        csvs = [x for x in z.namelist() if x.lower().endswith(".csv")]
        if not csvs:
            raise RuntimeError(f"No CSV in {path}")
        for csv_name in csvs:
            with z.open(csv_name) as fh:
                for df in pd.read_csv(fh, usecols=["Timestamp", "Bid"], chunksize=500_000):
                    t = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
                    good = t.notna() & df["Bid"].notna()
                    if year == 2026 and month == 10:
                        good = good & (t <= pd.Timestamp("2026-10-29 23:59:59.999999999", tz="UTC"))
                    if not bool(good.all()):
                        df = df.loc[good]
                        t = t.loc[good]
                    if len(df) == 0:
                        continue
                    minute = t.dt.floor("min")
                    x = pd.DataFrame({"minute": minute.to_numpy(), "bid": df["Bid"].to_numpy()})
                    g = x.groupby("minute", sort=False)["bid"].agg(["first", "max", "min", "last"]).reset_index()
                    parts.append(g)
    if not parts:
        return pd.DataFrame(columns=["minute", "open", "high", "low", "close"])
    m = pd.concat(parts, ignore_index=True)
    # A minute can straddle input chunks. Aggregate duplicate minute rows in original order.
    m = m.groupby("minute", sort=True).agg(open=("first", "first"), high=("max", "max"), low=("min", "min"), close=("last", "last")).reset_index()
    return m


def add_signal(rows, method, when, direction):
    rows.append((int(pd.Timestamp(when).value), method, int(direction)))


def build_signals(bars):
    b = bars.copy().sort_values("minute").reset_index(drop=True)
    c = b["close"]
    h = b["high"]
    l = b["low"]

    hi60 = h.rolling(60).max().shift(1)
    lo60 = l.rolling(60).min().shift(1)
    hi30 = h.rolling(30).max().shift(1)
    lo30 = l.rolling(30).min().shift(1)
    hi10 = h.rolling(10).max().shift(1)
    lo10 = l.rolling(10).min().shift(1)
    hi5 = h.rolling(5).max().shift(1)
    lo5 = l.rolling(5).min().shift(1)
    hi3 = h.rolling(3).max().shift(1)
    lo3 = l.rolling(3).min().shift(1)
    r10 = (h.rolling(10).max() - l.rolling(10).min()).shift(1)
    r60 = (h.rolling(60).max() - l.rolling(60).min()).shift(1)
    avg_range20 = (h - l).rolling(20).mean().shift(1)

    ema5 = c.ewm(span=5, adjust=False).mean()
    ema20 = c.ewm(span=20, adjust=False).mean()

    mu30 = c.rolling(30).mean().shift(1)
    sd30 = c.rolling(30).std(ddof=0).shift(1)
    z = (c - mu30) / sd30

    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    abs_move20 = (c - c.shift(20)).abs()
    path20 = c.diff().abs().rolling(20).sum()
    er20 = abs_move20 / path20.replace(0, np.nan)

    sig = [[] for _ in METHODS]

    for i in range(1, len(b)):
        when = b.loc[i, "minute"] + pd.Timedelta(minutes=1)
        close = float(c.iloc[i])
        prev_close = float(c.iloc[i - 1])

        # 1. Rolling 60-minute channel breakout, no fixed H1 candle.
        if pd.notna(hi60.iloc[i]) and pd.notna(lo60.iloc[i]):
            if close > hi60.iloc[i] and prev_close <= hi60.iloc[i - 1] if pd.notna(hi60.iloc[i - 1]) else False:
                add_signal(sig[0], 0, when, 1)
            elif close < lo60.iloc[i] and prev_close >= lo60.iloc[i - 1] if pd.notna(lo60.iloc[i - 1]) else False:
                add_signal(sig[0], 0, when, -1)

        # 2. EMA5/EMA20 trend with pullback reclaim.
        if i >= 2:
            if ema5.iloc[i] > ema20.iloc[i] and c.iloc[i - 1] <= ema5.iloc[i - 1] and close > ema5.iloc[i]:
                add_signal(sig[1], 1, when, 1)
            elif ema5.iloc[i] < ema20.iloc[i] and c.iloc[i - 1] >= ema5.iloc[i - 1] and close < ema5.iloc[i]:
                add_signal(sig[1], 1, when, -1)

        # 3. Five-minute impulse plus local 3-minute break.
        if i >= 5 and pd.notna(avg_range20.iloc[i]) and pd.notna(hi3.iloc[i]) and pd.notna(lo3.iloc[i]):
            threshold = max(1.0, 1.5 * float(avg_range20.iloc[i]))
            move5 = close - float(c.iloc[i - 5])
            if move5 >= threshold and close > hi3.iloc[i]:
                add_signal(sig[2], 2, when, 1)
            elif move5 <= -threshold and close < lo3.iloc[i]:
                add_signal(sig[2], 2, when, -1)

        # 4. Volatility compression, then breakout from the compressed range.
        if pd.notna(r10.iloc[i]) and pd.notna(r60.iloc[i]) and r60.iloc[i] > 0 and r10.iloc[i] <= 0.35 * r60.iloc[i]:
            if close > hi10.iloc[i]:
                add_signal(sig[3], 3, when, 1)
            elif close < lo10.iloc[i]:
                add_signal(sig[3], 3, when, -1)

        # 5. Statistical mean reversion on z-score threshold crossing.
        if i >= 2 and pd.notna(z.iloc[i]) and pd.notna(z.iloc[i - 1]):
            if z.iloc[i] <= -2.2 and z.iloc[i - 1] > -2.2:
                add_signal(sig[4], 4, when, 1)
            elif z.iloc[i] >= 2.2 and z.iloc[i - 1] < 2.2:
                add_signal(sig[4], 4, when, -1)

        # 7. Liquidity sweep/rejection of prior 30-minute extreme.
        if pd.notna(hi30.iloc[i]) and pd.notna(lo30.iloc[i]):
            if h.iloc[i] > hi30.iloc[i] + 0.20 and close < hi30.iloc[i]:
                add_signal(sig[6], 6, when, -1)
            elif l.iloc[i] < lo30.iloc[i] - 0.20 and close > lo30.iloc[i]:
                add_signal(sig[6], 6, when, 1)

        # 9. Directional efficiency trend continuation with a 5-minute break.
        if i >= 20 and pd.notna(er20.iloc[i]) and pd.notna(hi5.iloc[i]) and pd.notna(lo5.iloc[i]):
            move20 = close - float(c.iloc[i - 20])
            if er20.iloc[i] >= 0.55 and move20 >= 2.0 and close > hi5.iloc[i]:
                add_signal(sig[8], 8, when, 1)
            elif er20.iloc[i] >= 0.55 and move20 <= -2.0 and close < lo5.iloc[i]:
                add_signal(sig[8], 8, when, -1)

        # 10. RSI extreme reversal, enter only when RSI exits the extreme.
        if i >= 15 and pd.notna(rsi.iloc[i]) and pd.notna(rsi.iloc[i - 1]):
            if rsi.iloc[i - 1] < 25 and rsi.iloc[i] >= 25:
                add_signal(sig[9], 9, when, 1)
            elif rsi.iloc[i - 1] > 75 and rsi.iloc[i] <= 75:
                add_signal(sig[9], 9, when, -1)

    # 6. Pure price-action ZigZag swing reversal.
    if len(b):
        high_ext = float(c.iloc[0])
        low_ext = float(c.iloc[0])
        mode = 0
        for i in range(1, len(b)):
            x = float(c.iloc[i])
            high_ext = max(high_ext, x)
            low_ext = min(low_ext, x)
            when = b.loc[i, "minute"] + pd.Timedelta(minutes=1)
            span = high_ext - low_ext
            if mode >= 0 and span >= 3.0 and high_ext - x >= 1.0:
                add_signal(sig[5], 5, when, -1)
                mode = -1
                high_ext = x
                low_ext = x
            elif mode <= 0 and span >= 3.0 and x - low_ext >= 1.0:
                add_signal(sig[5], 5, when, 1)
                mode = 1
                high_ext = x
                low_ext = x

    # 8. Break -> retest -> rebreak of rolling 60-minute channel.
    state = 0
    level = 0.0
    for i in range(60, len(b)):
        if pd.isna(hi60.iloc[i]) or pd.isna(lo60.iloc[i]):
            continue
        x = float(c.iloc[i])
        when = b.loc[i, "minute"] + pd.Timedelta(minutes=1)
        if state == 0:
            if x > hi60.iloc[i]:
                state = 1
                level = float(hi60.iloc[i])
            elif x < lo60.iloc[i]:
                state = -1
                level = float(lo60.iloc[i])
        elif state == 1:
            if x <= level + 0.30:
                state = 2
            elif x < level - 1.50:
                state = 0
        elif state == 2:
            if x > level + 0.60:
                add_signal(sig[7], 7, when, 1)
                state = 0
            elif x < level - 1.50:
                state = 0
        elif state == -1:
            if x >= level - 0.30:
                state = -2
            elif x > level + 1.50:
                state = 0
        elif state == -2:
            if x < level - 0.60:
                add_signal(sig[7], 7, when, -1)
                state = 0
            elif x > level + 1.50:
                state = 0

    # Convert to compact 2D arrays. Sort and deduplicate same-minute repeated signals.
    cleaned = []
    maxn = 1
    for cidx, rows in enumerate(sig):
        rows = sorted(rows, key=lambda x: x[0])
        out = []
        last_t = -1
        for t, _, d in rows:
            if t == last_t:
                continue
            out.append((t, d))
            last_t = t
        cleaned.append(out)
        maxn = max(maxn, len(out))
    times = np.full((len(METHODS), maxn), np.iinfo(np.int64).max, dtype=np.int64)
    dirs = np.zeros((len(METHODS), maxn), dtype=np.int8)
    counts = np.zeros(len(METHODS), dtype=np.int64)
    for cidx, rows in enumerate(cleaned):
        counts[cidx] = len(rows)
        for k, (t, d) in enumerate(rows):
            times[cidx, k] = t
            dirs[cidx, k] = d
    return times, dirs, counts, cleaned


@njit(cache=True)
def gap_from_switches(switches):
    # 10,30,60,100,150,210... normalized pips => 1,3,6,10,15,21... XAU price units.
    n = switches + 1
    return BASE_STEP * n * (n + 1) / 2.0


@njit(cache=True)
def process_ticks(ts, bids, asks, sig_t, sig_d, sig_n,
                  balance, withdrawn, failed, failure_day, sig_ptr,
                  open_n, buy_n, sell_n, buy_sum, sell_sum,
                  up_outer, dn_outer, next_up, next_dn, last_side, switches,
                  stopped_today, day_realized, day_activity, day_target, day_maxpos,
                  traded_days, target_days, positive_days, negative_days, zero_days,
                  worst_day_pnl, worst_day_key, min_equity, max_positions, max_margin,
                  neg_count, neg_day_keys, neg_pnls, neg_maxpos,
                  shared_i, shared_f):
    C = len(balance)
    last_day = shared_i[0]
    initialized = shared_i[1]
    last_bid = shared_f[0]
    last_ask = shared_f[1]

    for j in range(len(ts)):
        t = ts[j]
        bid = bids[j]
        ask = asks[j]
        if not (math.isfinite(bid) and math.isfinite(ask)):
            continue
        day = t // 86400000000000
        dow = (day + 3) % 7

        if initialized == 0:
            initialized = 1
            last_day = day
            last_bid = bid
            last_ask = ask

        if day != last_day:
            prev_dow = (last_day + 3) % 7
            if prev_dow == 4:
                for cidx in range(C):
                    if failed[cidx] == 0 and open_n[cidx] > 0:
                        liq = buy_n[cidx] * last_bid - buy_sum[cidx] + sell_sum[cidx] - sell_n[cidx] * last_ask - open_n[cidx] * COMMISSION
                        balance[cidx] += liq
                        day_realized[cidx] += liq
                        open_n[cidx] = 0
                        buy_n[cidx] = 0
                        sell_n[cidx] = 0
                        buy_sum[cidx] = 0.0
                        sell_sum[cidx] = 0.0
                        last_side[cidx] = 0
                        switches[cidx] = 0
            for cidx in range(C):
                if day_activity[cidx] != 0:
                    traded_days[cidx] += 1
                if day_target[cidx] != 0:
                    target_days[cidx] += 1
                if day_realized[cidx] > 1e-9:
                    positive_days[cidx] += 1
                elif day_realized[cidx] < -1e-9:
                    negative_days[cidx] += 1
                    k = neg_count[cidx]
                    if k < MAX_NEG_DAYS:
                        neg_day_keys[cidx, k] = last_day
                        neg_pnls[cidx, k] = day_realized[cidx]
                        neg_maxpos[cidx, k] = day_maxpos[cidx]
                        neg_count[cidx] = k + 1
                elif day_activity[cidx] != 0:
                    zero_days[cidx] += 1
                if day_realized[cidx] < worst_day_pnl[cidx]:
                    worst_day_pnl[cidx] = day_realized[cidx]
                    worst_day_key[cidx] = last_day
                day_realized[cidx] = 0.0
                day_activity[cidx] = 0
                day_target[cidx] = 0
                day_maxpos[cidx] = 0
                stopped_today[cidx] = 0
            last_day = day

        for cidx in range(C):
            if failed[cidx] != 0:
                continue

            if open_n[cidx] > 0:
                day_activity[cidx] = 1
                if open_n[cidx] > day_maxpos[cidx]:
                    day_maxpos[cidx] = open_n[cidx]
                liq = buy_n[cidx] * bid - buy_sum[cidx] + sell_sum[cidx] - sell_n[cidx] * ask - open_n[cidx] * COMMISSION
                if day_realized[cidx] + liq >= TARGET:
                    balance[cidx] += liq
                    day_realized[cidx] += liq
                    open_n[cidx] = 0
                    buy_n[cidx] = 0
                    sell_n[cidx] = 0
                    buy_sum[cidx] = 0.0
                    sell_sum[cidx] = 0.0
                    last_side[cidx] = 0
                    switches[cidx] = 0
                    day_target[cidx] = 1
                    stopped_today[cidx] = 1
                    balance[cidx] -= TARGET
                    withdrawn[cidx] += TARGET

            # Discard stale signals while busy/stopped; execute fresh signal at first tick >= signal time.
            while sig_ptr[cidx] < sig_n[cidx] and sig_t[cidx, sig_ptr[cidx]] <= t:
                d = sig_d[cidx, sig_ptr[cidx]]
                sig_ptr[cidx] += 1
                if open_n[cidx] != 0 or stopped_today[cidx] != 0:
                    continue
                if dow >= 4:  # no new Friday/weekend baskets
                    continue
                fill = ask if d > 0 else bid
                req = fill / LEVERAGE
                if balance[cidx] < req:
                    failed[cidx] = 1
                    failure_day[cidx] = day
                    break
                open_n[cidx] = 1
                if d > 0:
                    buy_n[cidx] = 1
                    buy_sum[cidx] = fill
                    sell_n[cidx] = 0
                    sell_sum[cidx] = 0.0
                    last_side[cidx] = 1
                else:
                    sell_n[cidx] = 1
                    sell_sum[cidx] = fill
                    buy_n[cidx] = 0
                    buy_sum[cidx] = 0.0
                    last_side[cidx] = -1
                switches[cidx] = 0
                up_outer[cidx] = fill
                dn_outer[cidx] = fill
                g = gap_from_switches(0)
                next_up[cidx] = fill + g
                next_dn[cidx] = fill - g
                day_activity[cidx] = 1
                break

            # Adaptive outer-level grid. Only zigzag side-switches increase spacing.
            if open_n[cidx] > 0 and failed[cidx] == 0:
                for _ in range(12):
                    acted = 0
                    if bid >= next_up[cidx]:
                        liq = buy_n[cidx] * bid - buy_sum[cidx] + sell_sum[cidx] - sell_n[cidx] * ask - open_n[cidx] * COMMISSION
                        if liq > 0.0:
                            balance[cidx] += liq
                            day_realized[cidx] += liq
                            open_n[cidx] = 0
                            buy_n[cidx] = 0
                            sell_n[cidx] = 0
                            buy_sum[cidx] = 0.0
                            sell_sum[cidx] = 0.0
                            last_side[cidx] = 0
                            switches[cidx] = 0
                        else:
                            fill = ask
                            eq = balance[cidx] + liq
                            margin = open_n[cidx] * ((bid + ask) * 0.5) / LEVERAGE
                            req = fill / LEVERAGE
                            if eq - margin < req:
                                failed[cidx] = 1
                                failure_day[cidx] = day
                            else:
                                if last_side[cidx] == -1:
                                    switches[cidx] += 1
                                last_side[cidx] = 1
                                buy_n[cidx] += 1
                                buy_sum[cidx] += fill
                                open_n[cidx] += 1
                                up_outer[cidx] = next_up[cidx]
                                g = gap_from_switches(switches[cidx])
                                next_up[cidx] = up_outer[cidx] + g
                                next_dn[cidx] = dn_outer[cidx] - g
                        acted = 1
                    elif bid <= next_dn[cidx]:
                        liq = buy_n[cidx] * bid - buy_sum[cidx] + sell_sum[cidx] - sell_n[cidx] * ask - open_n[cidx] * COMMISSION
                        if liq > 0.0:
                            balance[cidx] += liq
                            day_realized[cidx] += liq
                            open_n[cidx] = 0
                            buy_n[cidx] = 0
                            sell_n[cidx] = 0
                            buy_sum[cidx] = 0.0
                            sell_sum[cidx] = 0.0
                            last_side[cidx] = 0
                            switches[cidx] = 0
                        else:
                            fill = bid
                            eq = balance[cidx] + liq
                            margin = open_n[cidx] * ((bid + ask) * 0.5) / LEVERAGE
                            req = fill / LEVERAGE
                            if eq - margin < req:
                                failed[cidx] = 1
                                failure_day[cidx] = day
                            else:
                                if last_side[cidx] == 1:
                                    switches[cidx] += 1
                                last_side[cidx] = -1
                                sell_n[cidx] += 1
                                sell_sum[cidx] += fill
                                open_n[cidx] += 1
                                dn_outer[cidx] = next_dn[cidx]
                                g = gap_from_switches(switches[cidx])
                                next_up[cidx] = up_outer[cidx] + g
                                next_dn[cidx] = dn_outer[cidx] - g
                        acted = 1
                    if acted == 0 or open_n[cidx] == 0 or failed[cidx] != 0:
                        break

                if open_n[cidx] == 0 and stopped_today[cidx] == 0 and day_realized[cidx] >= TARGET:
                    day_target[cidx] = 1
                    stopped_today[cidx] = 1
                    balance[cidx] -= TARGET
                    withdrawn[cidx] += TARGET

            liq2 = 0.0
            if open_n[cidx] > 0:
                liq2 = buy_n[cidx] * bid - buy_sum[cidx] + sell_sum[cidx] - sell_n[cidx] * ask - open_n[cidx] * COMMISSION
            eq2 = balance[cidx] + liq2
            if eq2 < min_equity[cidx]:
                min_equity[cidx] = eq2
            if open_n[cidx] > max_positions[cidx]:
                max_positions[cidx] = open_n[cidx]
            margin2 = open_n[cidx] * ((bid + ask) * 0.5) / LEVERAGE
            if margin2 > max_margin[cidx]:
                max_margin[cidx] = margin2
            if eq2 <= 0.0:
                failed[cidx] = 1
                failure_day[cidx] = day

        last_bid = bid
        last_ask = ask

    shared_i[0] = last_day
    shared_i[1] = initialized
    shared_f[0] = last_bid
    shared_f[1] = last_ask


def init_state(C):
    I = lambda v=0: np.full(C, v, dtype=np.int64)
    F = lambda v=0.0: np.full(C, v, dtype=np.float64)
    s = {}
    s["balance"] = F(START_BALANCE)
    s["withdrawn"] = F(0)
    s["failed"] = I(0)
    s["failure_day"] = I(-1)
    s["sig_ptr"] = I(0)
    s["open_n"] = I(0)
    s["buy_n"] = I(0)
    s["sell_n"] = I(0)
    s["buy_sum"] = F(0)
    s["sell_sum"] = F(0)
    s["up_outer"] = F(0)
    s["dn_outer"] = F(0)
    s["next_up"] = F(0)
    s["next_dn"] = F(0)
    s["last_side"] = I(0)
    s["switches"] = I(0)
    s["stopped_today"] = I(0)
    s["day_realized"] = F(0)
    s["day_activity"] = I(0)
    s["day_target"] = I(0)
    s["day_maxpos"] = I(0)
    s["traded_days"] = I(0)
    s["target_days"] = I(0)
    s["positive_days"] = I(0)
    s["negative_days"] = I(0)
    s["zero_days"] = I(0)
    s["worst_day_pnl"] = F(1e100)
    s["worst_day_key"] = I(-1)
    s["min_equity"] = F(START_BALANCE)
    s["max_positions"] = I(0)
    s["max_margin"] = F(0)
    s["neg_count"] = I(0)
    s["neg_day_keys"] = np.full((C, MAX_NEG_DAYS), -1, dtype=np.int64)
    s["neg_pnls"] = np.zeros((C, MAX_NEG_DAYS), dtype=np.float64)
    s["neg_maxpos"] = np.zeros((C, MAX_NEG_DAYS), dtype=np.int64)
    s["shared_i"] = np.array([-1, 0], dtype=np.int64)
    s["shared_f"] = np.zeros(2, dtype=np.float64)
    return s


def finalize_last_day(s):
    C = len(METHODS)
    if s["shared_i"][1] == 0:
        return
    last_day = int(s["shared_i"][0])
    last_bid = float(s["shared_f"][0])
    last_ask = float(s["shared_f"][1])
    if (last_day + 3) % 7 == 4:
        for cidx in range(C):
            if s["failed"][cidx] == 0 and s["open_n"][cidx] > 0:
                liq = s["buy_n"][cidx] * last_bid - s["buy_sum"][cidx] + s["sell_sum"][cidx] - s["sell_n"][cidx] * last_ask - s["open_n"][cidx] * COMMISSION
                s["balance"][cidx] += liq
                s["day_realized"][cidx] += liq
                s["open_n"][cidx] = 0
    for cidx in range(C):
        if s["day_activity"][cidx] != 0:
            s["traded_days"][cidx] += 1
        if s["day_target"][cidx] != 0:
            s["target_days"][cidx] += 1
        pnl = s["day_realized"][cidx]
        if pnl > 1e-9:
            s["positive_days"][cidx] += 1
        elif pnl < -1e-9:
            s["negative_days"][cidx] += 1
            k = int(s["neg_count"][cidx])
            if k < MAX_NEG_DAYS:
                s["neg_day_keys"][cidx, k] = last_day
                s["neg_pnls"][cidx, k] = pnl
                s["neg_maxpos"][cidx, k] = s["day_maxpos"][cidx]
                s["neg_count"][cidx] = k + 1
        elif s["day_activity"][cidx] != 0:
            s["zero_days"][cidx] += 1
        if pnl < s["worst_day_pnl"][cidx]:
            s["worst_day_pnl"][cidx] = pnl
            s["worst_day_key"][cidx] = last_day


def run(year, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    months = list(range(1, 13)) if year == 2025 else list(range(1, 11))
    zips = []
    minute_parts = []
    provenance = []

    for month in months:
        mm = f"{month:02d}"
        fn = f"Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip"
        url = f"https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}"
        path = outdir / fn
        print(f"DOWNLOAD {url}", flush=True)
        nbytes, sha = download(url, path)
        bars = aggregate_zip_to_minutes(path, year, month)
        minute_parts.append(bars)
        zips.append((month, path))
        provenance.append({"year": year, "month": month, "url": url, "bytes": nbytes, "sha256": sha, "minute_rows": len(bars)})
        print(f"BARS {year}-{mm}: {len(bars):,}", flush=True)

    bars = pd.concat(minute_parts, ignore_index=True).sort_values("minute").drop_duplicates("minute", keep="last").reset_index(drop=True)
    sig_t, sig_d, sig_n, cleaned = build_signals(bars)
    pd.DataFrame([{"method": METHODS[i], "signals": int(sig_n[i])} for i in range(len(METHODS))]).to_csv(outdir / f"signal_counts_{year}.csv", index=False)

    C = len(METHODS)
    s = init_state(C)

    # Numba warmup.
    process_ticks(np.empty(0, dtype=np.int64), np.empty(0), np.empty(0), sig_t, sig_d, sig_n,
                  s["balance"], s["withdrawn"], s["failed"], s["failure_day"], s["sig_ptr"],
                  s["open_n"], s["buy_n"], s["sell_n"], s["buy_sum"], s["sell_sum"],
                  s["up_outer"], s["dn_outer"], s["next_up"], s["next_dn"], s["last_side"], s["switches"],
                  s["stopped_today"], s["day_realized"], s["day_activity"], s["day_target"], s["day_maxpos"],
                  s["traded_days"], s["target_days"], s["positive_days"], s["negative_days"], s["zero_days"],
                  s["worst_day_pnl"], s["worst_day_key"], s["min_equity"], s["max_positions"], s["max_margin"],
                  s["neg_count"], s["neg_day_keys"], s["neg_pnls"], s["neg_maxpos"], s["shared_i"], s["shared_f"])

    for month, path in zips:
        with zipfile.ZipFile(path) as z:
            csvs = [x for x in z.namelist() if x.lower().endswith(".csv")]
            for csv_name in csvs:
                with z.open(csv_name) as fh:
                    for df in pd.read_csv(fh, usecols=["Timestamp", "Bid", "Ask"], chunksize=500_000):
                        t = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
                        good = t.notna() & df["Bid"].notna() & df["Ask"].notna()
                        if year == 2026 and month == 10:
                            good = good & (t <= pd.Timestamp("2026-10-29 23:59:59.999999999", tz="UTC"))
                        if not bool(good.all()):
                            df = df.loc[good]
                            t = t.loc[good]
                        if len(df) == 0:
                            continue
                        ts = t.astype("int64").to_numpy(dtype=np.int64, copy=False)
                        bids = df["Bid"].to_numpy(dtype=np.float64, copy=False)
                        asks = df["Ask"].to_numpy(dtype=np.float64, copy=False)
                        process_ticks(ts, bids, asks, sig_t, sig_d, sig_n,
                                      s["balance"], s["withdrawn"], s["failed"], s["failure_day"], s["sig_ptr"],
                                      s["open_n"], s["buy_n"], s["sell_n"], s["buy_sum"], s["sell_sum"],
                                      s["up_outer"], s["dn_outer"], s["next_up"], s["next_dn"], s["last_side"], s["switches"],
                                      s["stopped_today"], s["day_realized"], s["day_activity"], s["day_target"], s["day_maxpos"],
                                      s["traded_days"], s["target_days"], s["positive_days"], s["negative_days"], s["zero_days"],
                                      s["worst_day_pnl"], s["worst_day_key"], s["min_equity"], s["max_positions"], s["max_margin"],
                                      s["neg_count"], s["neg_day_keys"], s["neg_pnls"], s["neg_maxpos"], s["shared_i"], s["shared_f"])
        path.unlink(missing_ok=True)
        print(f"REPLAY DONE {year}-{month:02d}", flush=True)

    finalize_last_day(s)

    rows = []
    for cidx, name in enumerate(METHODS):
        marked = float(s["balance"][cidx])
        if s["open_n"][cidx] > 0:
            lb = float(s["shared_f"][0])
            la = float(s["shared_f"][1])
            marked += s["buy_n"][cidx] * lb - s["buy_sum"][cidx] + s["sell_sum"][cidx] - s["sell_n"][cidx] * la - s["open_n"][cidx] * COMMISSION
        td = int(s["traded_days"][cidx])
        tg = int(s["target_days"][cidx])
        rows.append({
            "method": name,
            "failed": bool(s["failed"][cidx]),
            "failure_date": day_to_iso(s["failure_day"][cidx]),
            "account_balance": round(float(s["balance"][cidx]), 3),
            "marked_equity": round(marked, 3),
            "cash_withdrawn": round(float(s["withdrawn"][cidx]), 3),
            "traded_days": td,
            "target_days": tg,
            "target_rate_pct": round(100.0 * tg / td, 4) if td else 0.0,
            "positive_days": int(s["positive_days"][cidx]),
            "negative_days": int(s["negative_days"][cidx]),
            "zero_activity_days": int(s["zero_days"][cidx]),
            "worst_day_pnl": round(float(s["worst_day_pnl"][cidx] if s["worst_day_pnl"][cidx] < 1e90 else 0.0), 3),
            "worst_day_date": day_to_iso(s["worst_day_key"][cidx]),
            "minimum_account_equity": round(float(s["min_equity"][cidx]), 3),
            "max_positions": int(s["max_positions"][cidx]),
            "max_margin": round(float(s["max_margin"][cidx]), 6),
            "open_positions_at_end": int(s["open_n"][cidx]),
            "signals_generated": int(sig_n[cidx]),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(outdir / f"entry10_adaptive_summary_{year}.csv", index=False)

    negrows = []
    for cidx, name in enumerate(METHODS):
        for k in range(int(s["neg_count"][cidx])):
            negrows.append({"method": name, "date": day_to_iso(s["neg_day_keys"][cidx, k]), "pnl": float(s["neg_pnls"][cidx, k]), "max_positions": int(s["neg_maxpos"][cidx, k])})
    pd.DataFrame(negrows).to_csv(outdir / f"entry10_adaptive_negative_days_{year}.csv", index=False)
    pd.DataFrame(provenance).to_csv(outdir / f"provenance_{year}.csv", index=False)
    (outdir / "RULES.txt").write_text(
        "Immutable rule: hit net +$10 -> close all -> withdraw exactly $10 -> stop trading for that UTC day.\n"
        "Lot size fixed 0.01 equivalent throughout; no martingale.\n"
        "No new Friday/weekend basket; any Friday basket is flattened by Friday end.\n"
        "Adaptive spacing after side switches: normalized 10,30,60,100,150,210... pips = $1,$3,$6,$10,$15,$21... XAU movement.\n"
        "Positive basket may close at a new adaptive outer level before adding the next order.\n"
        "Entry signals use completed 1-minute data only and are executed on the first subsequent raw tick.\n"
    )
    print(summary.to_string(index=False), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    if args.year not in (2025, 2026):
        raise SystemExit("year must be 2025 or 2026")
    run(args.year, args.outdir)


if __name__ == "__main__":
    main()
