import argparse
import csv
import hashlib
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from numba import njit

START_BALANCE = 1000.0
LEVERAGE = 2000.0
COMMISSION_PER_001 = 0.07
FIXED_ADVERSE = 10.0   # user's 100 pips under prior normalization
BASKET_TARGET = 5.0     # user's 50-pip-equivalent target on 0.01-lot basis, net P/L
MAX_DEPTH_RECORD = 80

# Reference + requested A-E systems.
NAMES = [
    "REF_DOUBLING_FIXED100",
    "A_LINEAR_LOTS_FIXED100",
    "B_FIB_LOTS_FIXED100",
    "C_MILD_1P5_LOTS_FIXED100",
    "D_CAP004_FIXED100",
    "E_DOUBLING_EXPANDING_DISTANCE",
]
C = len(NAMES)


def download(url, out):
    h = hashlib.sha256()
    total = 0
    with requests.get(url, stream=True, timeout=(30, 300)) as r:
        r.raise_for_status()
        with open(out, 'wb') as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
                    h.update(chunk)
                    total += len(chunk)
    return total, h.hexdigest()


def day_to_iso(day_key):
    if int(day_key) < 0:
        return ''
    return str(pd.Timestamp('1970-01-01', tz='UTC') + pd.Timedelta(days=int(day_key)))[:10]


@njit(cache=True)
def lot_units_for(config, depth):
    # depth is 1-based order number. Return units where 1 unit = 0.01 lot.
    if config == 0:  # Reference doubling
        return 2.0 ** (depth - 1)
    if config == 1:  # A: 1,2,3,4,5...
        return float(depth)
    if config == 2:  # B: Fibonacci 1,2,3,5,8,13...
        if depth <= 1: return 1.0
        if depth == 2: return 2.0
        a = 1.0
        b = 2.0
        for _ in range(3, depth + 1):
            c = a + b
            a = b
            b = c
        return b
    if config == 3:  # C: 1,1.5,2,3,4.5,6.75... then x1.5
        if depth == 1: return 1.0
        if depth == 2: return 1.5
        if depth == 3: return 2.0
        x = 2.0
        for _ in range(4, depth + 1):
            x *= 1.5
        return x
    if config == 4:  # D: 1,2,4,4,4...
        if depth == 1: return 1.0
        if depth == 2: return 2.0
        return 4.0
    # E: doubling lots
    return 2.0 ** (depth - 1)


@njit(cache=True)
def adverse_distance_for(config, next_depth):
    # Distance from last fill to the next add. next_depth=2 is first add after initial order.
    if config != 5:
        return FIXED_ADVERSE
    # E sequence in user pips: 100,150,250,400,650,1050... => price 10,15,25,40,65,105...
    idx = next_depth - 2  # first add idx 0
    if idx <= 0:
        return 10.0
    if idx == 1:
        return 15.0
    a = 10.0
    b = 15.0
    for _ in range(2, idx + 1):
        c = a + b
        a = b
        b = c
    return b


@njit(cache=True)
def process_chunk(ts, bids, asks,
                  balance, failed, failure_day, failure_reason,
                  open_dir, depth, total_units, weighted_entry_sum, next_add_trigger,
                  ref_hi, ref_lo, has_ref, armed,
                  baskets_closed, entries_started,
                  min_equity, max_depth, max_total_units, max_single_units,
                  worst_float, total_commission_closed,
                  depth_hist,
                  shared_i, shared_f):
    # shared_i: last_day, cur_hour, initialized
    # shared_f: hour_hi, hour_lo, prev_bid, prev_ask, last_bid, last_ask
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

        # Completed clock-H1 reference updates independently for each config only while flat.
        if hour != cur_hour:
            for cidx in range(C):
                if failed[cidx] == 0 and open_dir[cidx] == 0:
                    ref_hi[cidx] = hour_hi
                    ref_lo[cidx] = hour_lo
                    has_ref[cidx] = 1
            cur_hour = hour
            hour_hi = bid
            hour_lo = bid
        else:
            if bid > hour_hi: hour_hi = bid
            if bid < hour_lo: hour_lo = bid

        for cidx in range(C):
            if failed[cidx] != 0:
                continue

            if open_dir[cidx] != 0:
                units = total_units[cidx]
                if open_dir[cidx] > 0:
                    liq = units * bid - weighted_entry_sum[cidx] - units * COMMISSION_PER_001
                else:
                    liq = weighted_entry_sum[cidx] - units * ask - units * COMMISSION_PER_001

                eq = balance[cidx] + liq
                if eq < min_equity[cidx]: min_equity[cidx] = eq
                if liq < worst_float[cidx]: worst_float[cidx] = liq
                if eq <= 0.0:
                    failed[cidx] = 1
                    failure_day[cidx] = day
                    failure_reason[cidx] = 1  # equity zero
                    continue

                if liq >= BASKET_TARGET:
                    balance[cidx] += liq
                    total_commission_closed[cidx] += units * COMMISSION_PER_001
                    d = depth[cidx]
                    if d >= MAX_DEPTH_RECORD: d = MAX_DEPTH_RECORD - 1
                    depth_hist[cidx, d] += 1
                    baskets_closed[cidx] += 1
                    open_dir[cidx] = 0
                    depth[cidx] = 0
                    total_units[cidx] = 0.0
                    weighted_entry_sum[cidx] = 0.0
                    next_add_trigger[cidx] = 0.0
                    armed[cidx] = 0
                else:
                    # Handle gap-through across multiple planned add levels.
                    for _ in range(32):
                        if open_dir[cidx] == 0 or failed[cidx] != 0:
                            break
                        add_now = False
                        if open_dir[cidx] > 0 and bid <= next_add_trigger[cidx]:
                            add_now = True
                        elif open_dir[cidx] < 0 and ask >= next_add_trigger[cidx]:
                            add_now = True
                        if not add_now:
                            break

                        next_depth = depth[cidx] + 1
                        new_units = lot_units_for(cidx, next_depth)
                        mid = 0.5 * (bid + ask)
                        current_margin = total_units[cidx] * mid / LEVERAGE
                        req_margin = new_units * mid / LEVERAGE

                        units0 = total_units[cidx]
                        if open_dir[cidx] > 0:
                            liq_before = units0 * bid - weighted_entry_sum[cidx] - units0 * COMMISSION_PER_001
                        else:
                            liq_before = weighted_entry_sum[cidx] - units0 * ask - units0 * COMMISSION_PER_001
                        eq_before = balance[cidx] + liq_before
                        if eq_before - current_margin < req_margin:
                            failed[cidx] = 1
                            failure_day[cidx] = day
                            failure_reason[cidx] = 2  # insufficient free margin for prescribed next order
                            break

                        fill = ask if open_dir[cidx] > 0 else bid
                        total_units[cidx] += new_units
                        weighted_entry_sum[cidx] += new_units * fill
                        depth[cidx] = next_depth
                        if depth[cidx] > max_depth[cidx]: max_depth[cidx] = depth[cidx]
                        if total_units[cidx] > max_total_units[cidx]: max_total_units[cidx] = total_units[cidx]
                        if new_units > max_single_units[cidx]: max_single_units[cidx] = new_units

                        dist = adverse_distance_for(cidx, depth[cidx] + 1)
                        if open_dir[cidx] > 0:
                            next_add_trigger[cidx] = fill - dist
                        else:
                            next_add_trigger[cidx] = fill + dist

                        units2 = total_units[cidx]
                        if open_dir[cidx] > 0:
                            liq2 = units2 * bid - weighted_entry_sum[cidx] - units2 * COMMISSION_PER_001
                        else:
                            liq2 = weighted_entry_sum[cidx] - units2 * ask - units2 * COMMISSION_PER_001
                        eq2 = balance[cidx] + liq2
                        if eq2 < min_equity[cidx]: min_equity[cidx] = eq2
                        if liq2 < worst_float[cidx]: worst_float[cidx] = liq2
                        if eq2 <= 0.0:
                            failed[cidx] = 1
                            failure_day[cidx] = day
                            failure_reason[cidx] = 1
                            break

            # Rearm after return inside active H1 reference.
            if open_dir[cidx] == 0 and has_ref[cidx] != 0 and armed[cidx] == 0:
                if bid >= ref_lo[cidx] and bid <= ref_hi[cidx]:
                    armed[cidx] = 1

            # Old H1 breakout entry.
            if open_dir[cidx] == 0 and has_ref[cidx] != 0 and armed[cidx] != 0:
                direction = 0
                fill = 0.0
                if prev_ask <= ref_hi[cidx] and ask > ref_hi[cidx]:
                    direction = 1
                    fill = ask
                elif prev_bid >= ref_lo[cidx] and bid < ref_lo[cidx]:
                    direction = -1
                    fill = bid
                if direction != 0:
                    units = lot_units_for(cidx, 1)
                    mid = 0.5 * (bid + ask)
                    req_margin = units * mid / LEVERAGE
                    if balance[cidx] < req_margin:
                        failed[cidx] = 1
                        failure_day[cidx] = day
                        failure_reason[cidx] = 2
                    else:
                        open_dir[cidx] = direction
                        depth[cidx] = 1
                        total_units[cidx] = units
                        weighted_entry_sum[cidx] = units * fill
                        dist = adverse_distance_for(cidx, 2)
                        next_add_trigger[cidx] = fill - dist if direction > 0 else fill + dist
                        entries_started[cidx] += 1
                        if max_depth[cidx] < 1: max_depth[cidx] = 1
                        if max_total_units[cidx] < units: max_total_units[cidx] = units
                        if max_single_units[cidx] < units: max_single_units[cidx] = units
                        armed[cidx] = 0

        prev_bid = bid
        prev_ask = ask
        last_bid = bid
        last_ask = ask
        last_day = day

    shared_i[0] = last_day
    shared_i[1] = cur_hour
    shared_i[2] = initialized
    shared_f[0] = hour_hi
    shared_f[1] = hour_lo
    shared_f[2] = prev_bid
    shared_f[3] = prev_ask
    shared_f[4] = last_bid
    shared_f[5] = last_ask


def run(year, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    months = list(range(1, 13)) if year == 2025 else list(range(1, 11))

    balance = np.full(C, START_BALANCE, dtype=np.float64)
    failed = np.zeros(C, dtype=np.int64)
    failure_day = np.full(C, -1, dtype=np.int64)
    failure_reason = np.zeros(C, dtype=np.int64)
    open_dir = np.zeros(C, dtype=np.int64)
    depth = np.zeros(C, dtype=np.int64)
    total_units = np.zeros(C, dtype=np.float64)
    weighted_entry_sum = np.zeros(C, dtype=np.float64)
    next_add_trigger = np.zeros(C, dtype=np.float64)
    ref_hi = np.zeros(C, dtype=np.float64)
    ref_lo = np.zeros(C, dtype=np.float64)
    has_ref = np.zeros(C, dtype=np.int64)
    armed = np.zeros(C, dtype=np.int64)
    baskets_closed = np.zeros(C, dtype=np.int64)
    entries_started = np.zeros(C, dtype=np.int64)
    min_equity = np.full(C, START_BALANCE, dtype=np.float64)
    max_depth = np.zeros(C, dtype=np.int64)
    max_total_units = np.zeros(C, dtype=np.float64)
    max_single_units = np.zeros(C, dtype=np.float64)
    worst_float = np.zeros(C, dtype=np.float64)
    total_commission_closed = np.zeros(C, dtype=np.float64)
    depth_hist = np.zeros((C, MAX_DEPTH_RECORD), dtype=np.int64)
    shared_i = np.array([-1, -1, 0], dtype=np.int64)
    shared_f = np.zeros(6, dtype=np.float64)

    process_chunk(np.empty(0, dtype=np.int64), np.empty(0), np.empty(0),
                  balance, failed, failure_day, failure_reason,
                  open_dir, depth, total_units, weighted_entry_sum, next_add_trigger,
                  ref_hi, ref_lo, has_ref, armed, baskets_closed, entries_started,
                  min_equity, max_depth, max_total_units, max_single_units, worst_float, total_commission_closed,
                  depth_hist, shared_i, shared_f)

    provenance = []
    total_rows = 0
    for month in months:
        mm = f'{month:02d}'
        fn = f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'
        url = f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}'
        path = outdir / fn
        print('DOWNLOAD', url, flush=True)
        nbytes, sha = download(url, path)
        month_rows = 0
        with zipfile.ZipFile(path) as z:
            csvs = [x for x in z.namelist() if x.lower().endswith('.csv')]
            if not csvs:
                raise RuntimeError(f'No CSV in {path}')
            for csv_name in csvs:
                with z.open(csv_name) as fh:
                    for df in pd.read_csv(fh, usecols=['Timestamp', 'Bid', 'Ask'], chunksize=500_000):
                        t = pd.to_datetime(df['Timestamp'], utc=True, errors='coerce')
                        good = t.notna() & df['Bid'].notna() & df['Ask'].notna()
                        if year == 2026 and month == 10:
                            good = good & (t <= pd.Timestamp('2026-10-29 23:59:59.999999999', tz='UTC'))
                        if not bool(good.all()):
                            df = df.loc[good]
                            t = t.loc[good]
                        if len(df) == 0:
                            continue
                        ts = t.astype('int64').to_numpy(dtype=np.int64, copy=False)
                        bids = df['Bid'].to_numpy(dtype=np.float64, copy=False)
                        asks = df['Ask'].to_numpy(dtype=np.float64, copy=False)
                        process_chunk(ts, bids, asks,
                                      balance, failed, failure_day, failure_reason,
                                      open_dir, depth, total_units, weighted_entry_sum, next_add_trigger,
                                      ref_hi, ref_lo, has_ref, armed, baskets_closed, entries_started,
                                      min_equity, max_depth, max_total_units, max_single_units, worst_float, total_commission_closed,
                                      depth_hist, shared_i, shared_f)
                        month_rows += len(df)
                        total_rows += len(df)
        provenance.append({'year': year, 'month': month, 'url': url, 'bytes': nbytes, 'sha256': sha, 'rows': month_rows})
        path.unlink(missing_ok=True)
        print(f'DONE {year}-{mm}: rows={month_rows:,} active={int(np.sum(failed==0))}/{C}', flush=True)

    rows = []
    lb = shared_f[4]
    la = shared_f[5]
    for cidx, name in enumerate(NAMES):
        marked = balance[cidx]
        if open_dir[cidx] != 0:
            units = total_units[cidx]
            if open_dir[cidx] > 0:
                liq = units * lb - weighted_entry_sum[cidx] - units * COMMISSION_PER_001
            else:
                liq = weighted_entry_sum[cidx] - units * la - units * COMMISSION_PER_001
            marked += liq
        reason = ''
        if failure_reason[cidx] == 1: reason = 'equity<=0'
        elif failure_reason[cidx] == 2: reason = 'insufficient_free_margin_for_next_order'
        next_units = lot_units_for(cidx, depth[cidx] + 1) if open_dir[cidx] != 0 else lot_units_for(cidx, 1)
        next_dist = adverse_distance_for(cidx, depth[cidx] + 1) if open_dir[cidx] != 0 else adverse_distance_for(cidx, 2)
        rows.append({
            'system': name,
            'year': year,
            'failed': bool(failed[cidx]),
            'failure_date': day_to_iso(failure_day[cidx]),
            'failure_reason': reason,
            'starting_balance': START_BALANCE,
            'realized_balance': round(float(balance[cidx]), 6),
            'marked_equity': round(float(marked), 6),
            'realized_profit': round(float(balance[cidx]-START_BALANCE), 6),
            'entries_started': int(entries_started[cidx]),
            'baskets_closed_at_target': int(baskets_closed[cidx]),
            'close_rate_pct': round(100.0 * float(baskets_closed[cidx]) / max(1, int(entries_started[cidx])), 4),
            'minimum_equity': round(float(min_equity[cidx]), 6),
            'worst_floating_pnl': round(float(worst_float[cidx]), 6),
            'max_depth': int(max_depth[cidx]),
            'max_single_lot': round(float(max_single_units[cidx]*0.01), 6),
            'max_total_lots': round(float(max_total_units[cidx]*0.01), 6),
            'commission_on_closed_baskets': round(float(total_commission_closed[cidx]), 6),
            'open_direction_at_end': int(open_dir[cidx]),
            'open_depth_at_end': int(depth[cidx]),
            'open_total_lots_at_end': round(float(total_units[cidx]*0.01), 6),
            'next_prescribed_lot': round(float(next_units*0.01), 6),
            'next_adverse_distance_price': round(float(next_dist), 6),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(outdir / f'h1_lot_distance_summary_{year}.csv', index=False)

    hist_rows = []
    for cidx, name in enumerate(NAMES):
        for d in range(1, MAX_DEPTH_RECORD):
            n = int(depth_hist[cidx, d])
            if n:
                hist_rows.append({'system': name, 'depth': d, 'closed_baskets': n})
    pd.DataFrame(hist_rows).to_csv(outdir / f'h1_lot_distance_depth_hist_{year}.csv', index=False)

    with open(outdir / f'h1_lot_distance_provenance_{year}.json', 'w') as f:
        json.dump({
            'year': year,
            'source': 'https://ticks.ex2archive.com/',
            'total_rows': total_rows,
            'rules': {
                'entry': 'previous completed clock-H1 high breakout BUY / low breakout SELL; rearm after return inside reference range',
                'basket_target_net_usd_equivalent': BASKET_TARGET,
                'fixed_100pip_price_distance': FIXED_ADVERSE,
                'commission_per_0.01_roundtrip': COMMISSION_PER_001,
                'leverage': LEVERAGE,
                'no_forced_loss_close': True,
                'no_withdrawals': True,
                'E_distance_sequence_price': [10,15,25,40,65,105],
                'C_sequence_units': [1,1.5,2,3,4.5,6.75],
            },
            'files': provenance,
        }, f, indent=2)

    print(summary.to_string(index=False), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()
    if args.year not in (2025, 2026):
        raise SystemExit('Supported years: 2025, 2026')
    run(args.year, args.outdir)
