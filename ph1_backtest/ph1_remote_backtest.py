import argparse
import csv
import hashlib
import json
import math
import os
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from numba import njit

GRID = 1.0
COMMISSION = 0.07
LEVERAGE = 2000.0
START_BALANCE = 1000.0
TARGET = 10.0
MAX_NEG_DAYS = 128

# friday_mode: 0=current PH1; 1=no new Friday baskets; 2=no new baskets Thu>=18 UTC or Fri; 3=Thu>=12 or Fri
# danger_mode: 0=off; 1=stop adding after danger; 2=range-pause + convex extension
# convex_kind: 0 Fibonacci-ish 2,3,5,8,13...; 1 arithmetic 2,3,4,5...
CONFIGS = [
    ("BASELINE_NOWITHDRAW", 0, 0, 0, 0, 1, 0),
    ("BASELINE_W10",        0, 0, 0, 0, 1, 1),
    ("FRIDAY_NO_NEW_W10",   1, 0, 0, 0, 1, 1),
    ("D4_STOPADD_W10",      0, 4, 1, 0, 1, 1),
    ("D4_CONVEX_W10",       0, 4, 2, 0, 1, 1),
    ("D4_CONVEX_C2_W10",    0, 4, 2, 0, 2, 1),
    ("D4_CONVEX_C2_FRI",    1, 4, 2, 0, 2, 1),
    ("D3_CONVEX_C2_FRI",    1, 3, 2, 0, 2, 1),
    ("D5_CONVEX_C2_FRI",    1, 5, 2, 0, 2, 1),
    ("D4_CONVEX_C2_THU18",  2, 4, 2, 0, 2, 1),
    ("D4_CONVEX_C3_FRI",    1, 4, 2, 0, 3, 1),
    ("D4_ARITH_C2_FRI",     1, 4, 2, 1, 2, 1),
]


def config_arrays():
    names = [c[0] for c in CONFIGS]
    arr = np.array([c[1:] for c in CONFIGS], dtype=np.int64)
    return names, arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3], arr[:, 4], arr[:, 5]


def next_gap(kind, idx):
    if kind == 1:
        return float(2 + idx)
    fib = [2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0, 55.0]
    return fib[min(idx, len(fib) - 1)]


@njit(cache=True)
def _gap(kind, idx):
    if kind == 1:
        return 2.0 + idx
    if idx <= 0: return 2.0
    if idx == 1: return 3.0
    if idx == 2: return 5.0
    if idx == 3: return 8.0
    if idx == 4: return 13.0
    if idx == 5: return 21.0
    if idx == 6: return 34.0
    return 55.0


@njit(cache=True)
def process_chunk(ts, bids, asks,
                  friday_mode, danger_depth, danger_mode, convex_kind, confirm_ticks, withdraw_mode,
                  # account/state
                  balance, withdrawn, failed, failure_day,
                  open_n, buy_n, sell_n, buy_sum, sell_sum, p0, max_pos_lvl, min_neg_lvl,
                  danger_on, pos_gap_idx, neg_gap_idx, next_pos_px, next_neg_px, pos_conf, neg_conf,
                  ref_hi, ref_lo, has_ref, armed, stopped_today,
                  day_realized, day_activity, day_target,
                  # aggregates
                  traded_days, target_days, positive_days, negative_days, zero_days,
                  worst_day_pnl, worst_day_key, min_equity, max_positions, max_margin,
                  neg_count, neg_day_keys, neg_pnls, neg_maxpos,
                  day_maxpos,
                  # shared market state scalars packed arrays length 1
                  shared_i, shared_f):
    C = len(balance)
    # shared_i: [last_day, current_hour, initialized]
    # shared_f: [hour_hi,hour_lo,prev_bid,prev_ask,last_bid,last_ask]
    last_day = shared_i[0]
    cur_hour = shared_i[1]
    initialized = shared_i[2]
    hour_hi = shared_f[0]
    hour_lo = shared_f[1]
    prev_bid = shared_f[2]
    prev_ask = shared_f[3]
    last_bid = shared_f[4]
    last_ask = shared_f[5]

    for j in range(len(ts)):
        t = ts[j]
        bid = bids[j]
        ask = asks[j]
        if not (math.isfinite(bid) and math.isfinite(ask)):
            continue
        day = t // 86400000000000
        hour = t // 3600000000000
        dow = (day + 3) % 7  # Monday=0, 1970-01-01 was Thursday
        hod = (t // 3600000000000) % 24

        if initialized == 0:
            initialized = 1
            last_day = day
            cur_hour = hour
            hour_hi = bid
            hour_lo = bid
            prev_bid = bid
            prev_ask = ask
            last_bid = bid
            last_ask = ask

        # Day boundary: force Friday flat using final quote of Friday, then finalize previous day.
        if day != last_day:
            prev_dow = (last_day + 3) % 7
            if prev_dow == 4:
                for c in range(C):
                    if failed[c] == 0 and open_n[c] > 0:
                        liq = buy_n[c] * last_bid - buy_sum[c] + sell_sum[c] - sell_n[c] * last_ask - open_n[c] * COMMISSION
                        balance[c] += liq
                        day_realized[c] += liq
                        open_n[c] = 0; buy_n[c] = 0; sell_n[c] = 0; buy_sum[c] = 0.0; sell_sum[c] = 0.0
                        danger_on[c] = 0; pos_conf[c] = 0; neg_conf[c] = 0; armed[c] = 0
            for c in range(C):
                if day_activity[c] != 0:
                    traded_days[c] += 1
                if day_target[c] != 0:
                    target_days[c] += 1
                if day_realized[c] > 1e-9:
                    positive_days[c] += 1
                elif day_realized[c] < -1e-9:
                    negative_days[c] += 1
                    k = neg_count[c]
                    if k < MAX_NEG_DAYS:
                        neg_day_keys[c, k] = last_day
                        neg_pnls[c, k] = day_realized[c]
                        neg_maxpos[c, k] = day_maxpos[c]
                        neg_count[c] = k + 1
                elif day_activity[c] != 0:
                    zero_days[c] += 1
                if day_realized[c] < worst_day_pnl[c]:
                    worst_day_pnl[c] = day_realized[c]
                    worst_day_key[c] = last_day
                day_realized[c] = 0.0
                day_activity[c] = 0
                day_target[c] = 0
                day_maxpos[c] = 0
                stopped_today[c] = 0
            last_day = day

        # Completed H1 reference updates only for configurations that are flat.
        if hour != cur_hour:
            for c in range(C):
                if failed[c] == 0 and open_n[c] == 0:
                    ref_hi[c] = hour_hi
                    ref_lo[c] = hour_lo
                    has_ref[c] = 1
            cur_hour = hour
            hour_hi = bid
            hour_lo = bid
        else:
            if bid > hour_hi: hour_hi = bid
            if bid < hour_lo: hour_lo = bid

        for c in range(C):
            if failed[c] != 0:
                continue

            if open_n[c] > 0:
                day_activity[c] = 1
                if open_n[c] > day_maxpos[c]: day_maxpos[c] = open_n[c]
                liq = buy_n[c] * bid - buy_sum[c] + sell_sum[c] - sell_n[c] * ask - open_n[c] * COMMISSION
                # Daily target, tick by tick.
                if day_realized[c] + liq >= TARGET:
                    balance[c] += liq
                    day_realized[c] += liq
                    open_n[c] = 0; buy_n[c] = 0; sell_n[c] = 0; buy_sum[c] = 0.0; sell_sum[c] = 0.0
                    danger_on[c] = 0; pos_conf[c] = 0; neg_conf[c] = 0; armed[c] = 0
                    day_target[c] = 1
                    stopped_today[c] = 1
                    if withdraw_mode[c] != 0:
                        balance[c] -= TARGET
                        withdrawn[c] += TARGET

            # Rearm only after return inside reference H1 range.
            if open_n[c] == 0 and stopped_today[c] == 0 and has_ref[c] != 0 and armed[c] == 0:
                if bid >= ref_lo[c] and bid <= ref_hi[c]:
                    armed[c] = 1

            # First entry on H1 breakout.
            if open_n[c] == 0 and stopped_today[c] == 0 and has_ref[c] != 0 and armed[c] != 0:
                allow = 1
                fm = friday_mode[c]
                if fm == 1 and dow == 4:
                    allow = 0
                elif fm == 2 and (dow == 4 or (dow == 3 and hod >= 18)):
                    allow = 0
                elif fm == 3 and (dow == 4 or (dow == 3 and hod >= 12)):
                    allow = 0
                if allow != 0:
                    direction = 0
                    fill = 0.0
                    if prev_ask <= ref_hi[c] and ask > ref_hi[c]:
                        direction = 1; fill = ask
                    elif prev_bid >= ref_lo[c] and bid < ref_lo[c]:
                        direction = -1; fill = bid
                    if direction != 0:
                        req = fill / LEVERAGE
                        if balance[c] < req:
                            failed[c] = 1; failure_day[c] = day
                        else:
                            p0[c] = fill
                            open_n[c] = 1
                            if direction == 1:
                                buy_n[c] = 1; buy_sum[c] = fill; sell_n[c] = 0; sell_sum[c] = 0.0
                            else:
                                sell_n[c] = 1; sell_sum[c] = fill; buy_n[c] = 0; buy_sum[c] = 0.0
                            max_pos_lvl[c] = 0; min_neg_lvl[c] = 0
                            danger_on[c] = 0; pos_gap_idx[c] = 0; neg_gap_idx[c] = 0; pos_conf[c] = 0; neg_conf[c] = 0
                            day_activity[c] = 1; armed[c] = 0

            # Grid / whipsaw defence.
            if open_n[c] > 0 and failed[c] == 0:
                if danger_on[c] == 0:
                    # Positive virgin levels. Process all integer levels crossed in this tick.
                    while bid >= p0[c] + (max_pos_lvl[c] + 1) * GRID and open_n[c] > 0:
                        liq = buy_n[c] * bid - buy_sum[c] + sell_sum[c] - sell_n[c] * ask - open_n[c] * COMMISSION
                        if liq > 0.0:
                            balance[c] += liq; day_realized[c] += liq
                            open_n[c] = 0; buy_n[c] = 0; sell_n[c] = 0; buy_sum[c] = 0.0; sell_sum[c] = 0.0
                            armed[c] = 0
                            break
                        fill = ask
                        eq = balance[c] + liq
                        margin = open_n[c] * ((bid + ask) * 0.5) / LEVERAGE
                        req = fill / LEVERAGE
                        if eq - margin < req:
                            failed[c] = 1; failure_day[c] = day; break
                        buy_n[c] += 1; buy_sum[c] += fill; open_n[c] += 1; max_pos_lvl[c] += 1
                        if open_n[c] > max_positions[c]: max_positions[c] = open_n[c]
                        if open_n[c] > day_maxpos[c]: day_maxpos[c] = open_n[c]
                        baldepth = max_pos_lvl[c]
                        if -min_neg_lvl[c] < baldepth: baldepth = -min_neg_lvl[c]
                        if danger_mode[c] != 0 and danger_depth[c] > 0 and baldepth >= danger_depth[c]:
                            danger_on[c] = 1
                            g = _gap(convex_kind[c], 0)
                            next_pos_px[c] = p0[c] + max_pos_lvl[c] * GRID + g
                            next_neg_px[c] = p0[c] + min_neg_lvl[c] * GRID - g
                            break
                    # Negative virgin levels.
                    while danger_on[c] == 0 and bid <= p0[c] + (min_neg_lvl[c] - 1) * GRID and open_n[c] > 0 and failed[c] == 0:
                        liq = buy_n[c] * bid - buy_sum[c] + sell_sum[c] - sell_n[c] * ask - open_n[c] * COMMISSION
                        if liq > 0.0:
                            balance[c] += liq; day_realized[c] += liq
                            open_n[c] = 0; buy_n[c] = 0; sell_n[c] = 0; buy_sum[c] = 0.0; sell_sum[c] = 0.0
                            armed[c] = 0
                            break
                        fill = bid
                        eq = balance[c] + liq
                        margin = open_n[c] * ((bid + ask) * 0.5) / LEVERAGE
                        req = fill / LEVERAGE
                        if eq - margin < req:
                            failed[c] = 1; failure_day[c] = day; break
                        sell_n[c] += 1; sell_sum[c] += fill; open_n[c] += 1; min_neg_lvl[c] -= 1
                        if open_n[c] > max_positions[c]: max_positions[c] = open_n[c]
                        if open_n[c] > day_maxpos[c]: day_maxpos[c] = open_n[c]
                        baldepth = max_pos_lvl[c]
                        if -min_neg_lvl[c] < baldepth: baldepth = -min_neg_lvl[c]
                        if danger_mode[c] != 0 and danger_depth[c] > 0 and baldepth >= danger_depth[c]:
                            danger_on[c] = 1
                            g = _gap(convex_kind[c], 0)
                            next_pos_px[c] = p0[c] + max_pos_lvl[c] * GRID + g
                            next_neg_px[c] = p0[c] + min_neg_lvl[c] * GRID - g
                            break
                else:
                    # danger_mode 1 = range pause / stop adding completely.
                    # danger_mode 2 = range pause until convex outer extension, then confirmed 0.01 add.
                    if danger_mode[c] == 2:
                        if bid >= next_pos_px[c]: pos_conf[c] += 1
                        else: pos_conf[c] = 0
                        if bid <= next_neg_px[c]: neg_conf[c] += 1
                        else: neg_conf[c] = 0
                        if pos_conf[c] >= confirm_ticks[c]:
                            liq = buy_n[c] * bid - buy_sum[c] + sell_sum[c] - sell_n[c] * ask - open_n[c] * COMMISSION
                            if liq > 0.0:
                                balance[c] += liq; day_realized[c] += liq
                                open_n[c] = 0; buy_n[c] = 0; sell_n[c] = 0; buy_sum[c] = 0.0; sell_sum[c] = 0.0; armed[c] = 0
                            else:
                                fill = ask; eq = balance[c] + liq; margin = open_n[c] * ((bid + ask) * 0.5) / LEVERAGE; req = fill / LEVERAGE
                                if eq - margin < req:
                                    failed[c] = 1; failure_day[c] = day
                                else:
                                    buy_n[c] += 1; buy_sum[c] += fill; open_n[c] += 1
                                    pos_gap_idx[c] += 1
                                    next_pos_px[c] += _gap(convex_kind[c], pos_gap_idx[c])
                                    pos_conf[c] = 0
                        elif neg_conf[c] >= confirm_ticks[c]:
                            liq = buy_n[c] * bid - buy_sum[c] + sell_sum[c] - sell_n[c] * ask - open_n[c] * COMMISSION
                            if liq > 0.0:
                                balance[c] += liq; day_realized[c] += liq
                                open_n[c] = 0; buy_n[c] = 0; sell_n[c] = 0; buy_sum[c] = 0.0; sell_sum[c] = 0.0; armed[c] = 0
                            else:
                                fill = bid; eq = balance[c] + liq; margin = open_n[c] * ((bid + ask) * 0.5) / LEVERAGE; req = fill / LEVERAGE
                                if eq - margin < req:
                                    failed[c] = 1; failure_day[c] = day
                                else:
                                    sell_n[c] += 1; sell_sum[c] += fill; open_n[c] += 1
                                    neg_gap_idx[c] += 1
                                    next_neg_px[c] -= _gap(convex_kind[c], neg_gap_idx[c])
                                    neg_conf[c] = 0

                # If a positive basket close pushed realized day P/L above target, bank/withdraw now.
                if open_n[c] == 0 and stopped_today[c] == 0 and day_realized[c] >= TARGET:
                    day_target[c] = 1; stopped_today[c] = 1; armed[c] = 0
                    if withdraw_mode[c] != 0:
                        balance[c] -= TARGET; withdrawn[c] += TARGET

            # Account risk metrics and failure check.
            liq2 = 0.0
            if open_n[c] > 0:
                liq2 = buy_n[c] * bid - buy_sum[c] + sell_sum[c] - sell_n[c] * ask - open_n[c] * COMMISSION
            eq2 = balance[c] + liq2
            if eq2 < min_equity[c]: min_equity[c] = eq2
            if open_n[c] > max_positions[c]: max_positions[c] = open_n[c]
            m = open_n[c] * ((bid + ask) * 0.5) / LEVERAGE
            if m > max_margin[c]: max_margin[c] = m
            if eq2 <= 0.0:
                failed[c] = 1; failure_day[c] = day

        prev_bid = bid; prev_ask = ask; last_bid = bid; last_ask = ask

    shared_i[0] = last_day; shared_i[1] = cur_hour; shared_i[2] = initialized
    shared_f[0] = hour_hi; shared_f[1] = hour_lo; shared_f[2] = prev_bid; shared_f[3] = prev_ask; shared_f[4] = last_bid; shared_f[5] = last_ask


@njit(cache=True)
def finish_period(friday_mode, withdraw_mode,
                  balance, withdrawn, failed, open_n, buy_n, sell_n, buy_sum, sell_sum, armed,
                  day_realized, day_activity, day_target, traded_days, target_days, positive_days, negative_days, zero_days,
                  worst_day_pnl, worst_day_key, neg_count, neg_day_keys, neg_pnls, neg_maxpos, day_maxpos,
                  shared_i, shared_f):
    last_day = shared_i[0]
    if shared_i[2] == 0:
        return
    last_bid = shared_f[4]; last_ask = shared_f[5]
    C = len(balance)
    # If dataset ends on Friday, apply the same Friday-flat rule at the final quote.
    if (last_day + 3) % 7 == 4:
        for c in range(C):
            if failed[c] == 0 and open_n[c] > 0:
                liq = buy_n[c] * last_bid - buy_sum[c] + sell_sum[c] - sell_n[c] * last_ask - open_n[c] * COMMISSION
                balance[c] += liq; day_realized[c] += liq
                open_n[c] = 0; buy_n[c] = 0; sell_n[c] = 0; buy_sum[c] = 0.0; sell_sum[c] = 0.0; armed[c] = 0
    for c in range(C):
        if day_activity[c] != 0: traded_days[c] += 1
        if day_target[c] != 0: target_days[c] += 1
        if day_realized[c] > 1e-9: positive_days[c] += 1
        elif day_realized[c] < -1e-9:
            negative_days[c] += 1
            k = neg_count[c]
            if k < MAX_NEG_DAYS:
                neg_day_keys[c, k] = last_day; neg_pnls[c, k] = day_realized[c]; neg_maxpos[c, k] = day_maxpos[c]; neg_count[c] = k + 1
        elif day_activity[c] != 0: zero_days[c] += 1
        if day_realized[c] < worst_day_pnl[c]:
            worst_day_pnl[c] = day_realized[c]; worst_day_key[c] = last_day


def day_to_iso(day_key):
    if int(day_key) < 0:
        return ""
    return str(pd.Timestamp("1970-01-01", tz="UTC") + pd.Timedelta(days=int(day_key)))[:10]


def download(url, out):
    out = Path(out)
    h = hashlib.sha256()
    total = 0
    with requests.get(url, stream=True, timeout=(30, 300)) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk); h.update(chunk); total += len(chunk)
    return total, h.hexdigest()


def init_state(C):
    I = lambda v=0: np.full(C, v, dtype=np.int64)
    F = lambda v=0.0: np.full(C, v, dtype=np.float64)
    s = {}
    s['balance']=F(START_BALANCE); s['withdrawn']=F(0); s['failed']=I(0); s['failure_day']=I(-1)
    s['open_n']=I(0); s['buy_n']=I(0); s['sell_n']=I(0); s['buy_sum']=F(0); s['sell_sum']=F(0); s['p0']=F(0)
    s['max_pos_lvl']=I(0); s['min_neg_lvl']=I(0); s['danger_on']=I(0); s['pos_gap_idx']=I(0); s['neg_gap_idx']=I(0)
    s['next_pos_px']=F(0); s['next_neg_px']=F(0); s['pos_conf']=I(0); s['neg_conf']=I(0)
    s['ref_hi']=F(0); s['ref_lo']=F(0); s['has_ref']=I(0); s['armed']=I(0); s['stopped_today']=I(0)
    s['day_realized']=F(0); s['day_activity']=I(0); s['day_target']=I(0); s['day_maxpos']=I(0)
    s['traded_days']=I(0); s['target_days']=I(0); s['positive_days']=I(0); s['negative_days']=I(0); s['zero_days']=I(0)
    s['worst_day_pnl']=F(1e100); s['worst_day_key']=I(-1); s['min_equity']=F(START_BALANCE); s['max_positions']=I(0); s['max_margin']=F(0)
    s['neg_count']=I(0); s['neg_day_keys']=np.full((C,MAX_NEG_DAYS), -1, dtype=np.int64); s['neg_pnls']=np.zeros((C,MAX_NEG_DAYS)); s['neg_maxpos']=np.zeros((C,MAX_NEG_DAYS),dtype=np.int64)
    s['shared_i']=np.array([-1,-1,0], dtype=np.int64); s['shared_f']=np.zeros(6,dtype=np.float64)
    return s


def run_period(year, months, outdir):
    names, friday_mode, danger_depth, danger_mode, convex_kind, confirm_ticks, withdraw_mode = config_arrays()
    C = len(names); s = init_state(C)
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    provenance = []
    total_rows = 0

    # Warm numba compile with empty arrays.
    process_chunk(np.empty(0,dtype=np.int64), np.empty(0), np.empty(0), friday_mode,danger_depth,danger_mode,convex_kind,confirm_ticks,withdraw_mode,
                  s['balance'],s['withdrawn'],s['failed'],s['failure_day'],s['open_n'],s['buy_n'],s['sell_n'],s['buy_sum'],s['sell_sum'],s['p0'],s['max_pos_lvl'],s['min_neg_lvl'],
                  s['danger_on'],s['pos_gap_idx'],s['neg_gap_idx'],s['next_pos_px'],s['next_neg_px'],s['pos_conf'],s['neg_conf'],s['ref_hi'],s['ref_lo'],s['has_ref'],s['armed'],s['stopped_today'],
                  s['day_realized'],s['day_activity'],s['day_target'],s['traded_days'],s['target_days'],s['positive_days'],s['negative_days'],s['zero_days'],s['worst_day_pnl'],s['worst_day_key'],s['min_equity'],s['max_positions'],s['max_margin'],
                  s['neg_count'],s['neg_day_keys'],s['neg_pnls'],s['neg_maxpos'],s['day_maxpos'],s['shared_i'],s['shared_f'])

    for month in months:
        mm = f"{month:02d}"
        fn = f"Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip"
        url = f"https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}"
        path = outdir / fn
        print(f"DOWNLOAD {url}", flush=True)
        nbytes, sha = download(url, path)
        month_rows = 0
        with zipfile.ZipFile(path) as z:
            csv_names = [x for x in z.namelist() if x.lower().endswith('.csv')]
            if not csv_names:
                raise RuntimeError(f"No CSV in {fn}: {z.namelist()[:10]}")
            for csv_name in csv_names:
                with z.open(csv_name) as fh:
                    for df in pd.read_csv(fh, usecols=['Timestamp','Bid','Ask'], chunksize=500_000):
                        t = pd.to_datetime(df['Timestamp'], utc=True, errors='coerce')
                        good = t.notna() & df['Bid'].notna() & df['Ask'].notna()
                        if not bool(good.all()):
                            df = df.loc[good]; t = t.loc[good]
                        ts = t.astype('int64').to_numpy(dtype=np.int64, copy=False)
                        bids = df['Bid'].to_numpy(dtype=np.float64, copy=False)
                        asks = df['Ask'].to_numpy(dtype=np.float64, copy=False)
                        process_chunk(ts,bids,asks,friday_mode,danger_depth,danger_mode,convex_kind,confirm_ticks,withdraw_mode,
                                      s['balance'],s['withdrawn'],s['failed'],s['failure_day'],s['open_n'],s['buy_n'],s['sell_n'],s['buy_sum'],s['sell_sum'],s['p0'],s['max_pos_lvl'],s['min_neg_lvl'],
                                      s['danger_on'],s['pos_gap_idx'],s['neg_gap_idx'],s['next_pos_px'],s['next_neg_px'],s['pos_conf'],s['neg_conf'],s['ref_hi'],s['ref_lo'],s['has_ref'],s['armed'],s['stopped_today'],
                                      s['day_realized'],s['day_activity'],s['day_target'],s['traded_days'],s['target_days'],s['positive_days'],s['negative_days'],s['zero_days'],s['worst_day_pnl'],s['worst_day_key'],s['min_equity'],s['max_positions'],s['max_margin'],
                                      s['neg_count'],s['neg_day_keys'],s['neg_pnls'],s['neg_maxpos'],s['day_maxpos'],s['shared_i'],s['shared_f'])
                        month_rows += len(df); total_rows += len(df)
        provenance.append({'year':year,'month':month,'url':url,'file':fn,'bytes':nbytes,'sha256':sha,'rows':month_rows})
        path.unlink(missing_ok=True)
        print(f"DONE {year}-{mm}: rows={month_rows:,}", flush=True)

    finish_period(friday_mode,withdraw_mode,s['balance'],s['withdrawn'],s['failed'],s['open_n'],s['buy_n'],s['sell_n'],s['buy_sum'],s['sell_sum'],s['armed'],
                  s['day_realized'],s['day_activity'],s['day_target'],s['traded_days'],s['target_days'],s['positive_days'],s['negative_days'],s['zero_days'],
                  s['worst_day_pnl'],s['worst_day_key'],s['neg_count'],s['neg_day_keys'],s['neg_pnls'],s['neg_maxpos'],s['day_maxpos'],s['shared_i'],s['shared_f'])

    rows = []
    for c,name in enumerate(names):
        # Mark-to-market at period end if a non-Friday basket remains open.
        marked = s['balance'][c]
        if s['open_n'][c] > 0:
            lb,la = s['shared_f'][4],s['shared_f'][5]
            marked += s['buy_n'][c]*lb - s['buy_sum'][c] + s['sell_sum'][c] - s['sell_n'][c]*la - s['open_n'][c]*COMMISSION
        rows.append({
            'config':name,
            'failed':bool(s['failed'][c]),
            'failure_date':day_to_iso(s['failure_day'][c]),
            'account_balance':round(float(s['balance'][c]),6),
            'marked_equity':round(float(marked),6),
            'trading_pnl_before_withdrawals':round(float(s['balance'][c]+s['withdrawn'][c]-START_BALANCE),6),
            'cash_withdrawn':round(float(s['withdrawn'][c]),6),
            'traded_days':int(s['traded_days'][c]),
            'target_days':int(s['target_days'][c]),
            'target_rate_pct':round(100.0*float(s['target_days'][c])/max(1,int(s['traded_days'][c])),4),
            'positive_days':int(s['positive_days'][c]),
            'negative_days':int(s['negative_days'][c]),
            'zero_activity_days':int(s['zero_days'][c]),
            'worst_day_pnl':round(float(s['worst_day_pnl'][c] if s['worst_day_pnl'][c] < 1e90 else 0.0),6),
            'worst_day_date':day_to_iso(s['worst_day_key'][c]),
            'minimum_account_equity':round(float(s['min_equity'][c]),6),
            'max_positions':int(s['max_positions'][c]),
            'max_margin':round(float(s['max_margin'][c]),6),
            'open_positions_at_end':int(s['open_n'][c]),
        })
    pd.DataFrame(rows).to_csv(outdir / f"ph1_{year}_summary.csv", index=False)

    negrows=[]
    for c,name in enumerate(names):
        for k in range(int(s['neg_count'][c])):
            negrows.append({'config':name,'date':day_to_iso(s['neg_day_keys'][c,k]),'pnl':float(s['neg_pnls'][c,k]),'max_positions_that_day':int(s['neg_maxpos'][c,k])})
    pd.DataFrame(negrows).to_csv(outdir / f"ph1_{year}_negative_days.csv", index=False)
    with open(outdir / f"ph1_{year}_provenance.json",'w') as f:
        json.dump({'year':year,'months':months,'total_rows':total_rows,'source':'https://ticks.ex2archive.com/','files':provenance,'configs':CONFIGS},f,indent=2)
    print(pd.DataFrame(rows).to_string(index=False), flush=True)


if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',default='results')
    args=ap.parse_args()
    if args.year==2025: months=list(range(1,13))
    elif args.year==2026: months=list(range(1,11))
    else: raise SystemExit('Supported audit years: 2025 or 2026')
    run_period(args.year,months,args.outdir)
