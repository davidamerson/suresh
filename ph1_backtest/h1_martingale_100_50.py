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
ADVERSE_DISTANCE = 10.0   # user's 100 pips, using prior normalization: 10 pips = $1 XAU
BASKET_TARGET = 5.0       # user's 50 pips equivalent on 0.01-lot basis, net liquidation P/L
MAX_DEPTH_RECORD = 60


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
def process_chunk(ts, bids, asks,
                  balance, failed, failure_day,
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
        if failed[0] != 0:
            break
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

        # Completed H1 reference updates only while flat, matching the old H1-entry convention.
        if hour != cur_hour:
            if open_dir[0] == 0:
                ref_hi[0] = hour_hi
                ref_lo[0] = hour_lo
                has_ref[0] = 1
            cur_hour = hour
            hour_hi = bid
            hour_lo = bid
        else:
            if bid > hour_hi:
                hour_hi = bid
            if bid < hour_lo:
                hour_lo = bid

        # Existing basket: mark-to-market, close at net +50-pip-equivalent target, or add every 100 pips adverse.
        if open_dir[0] != 0:
            units = total_units[0]
            if open_dir[0] > 0:
                liq = units * bid - weighted_entry_sum[0] - units * COMMISSION_PER_001
            else:
                liq = weighted_entry_sum[0] - units * ask - units * COMMISSION_PER_001

            eq = balance[0] + liq
            if eq < min_equity[0]:
                min_equity[0] = eq
            if liq < worst_float[0]:
                worst_float[0] = liq
            if eq <= 0.0:
                failed[0] = 1
                failure_day[0] = day
                break

            if liq >= BASKET_TARGET:
                balance[0] += liq
                total_commission_closed[0] += units * COMMISSION_PER_001
                d = depth[0]
                if d >= MAX_DEPTH_RECORD:
                    d = MAX_DEPTH_RECORD - 1
                depth_hist[d] += 1
                baskets_closed[0] += 1
                open_dir[0] = 0
                depth[0] = 0
                total_units[0] = 0.0
                weighted_entry_sum[0] = 0.0
                next_add_trigger[0] = 0.0
                armed[0] = 0
            else:
                # Process multiple 100-pip levels crossed in a single tick if needed.
                for _ in range(32):
                    if open_dir[0] == 0 or failed[0] != 0:
                        break
                    add_now = False
                    if open_dir[0] > 0 and bid <= next_add_trigger[0]:
                        add_now = True
                    elif open_dir[0] < 0 and ask >= next_add_trigger[0]:
                        add_now = True
                    if not add_now:
                        break

                    new_units = 2.0 ** depth[0]  # depth1 first order=1 unit; next=2,4,8...
                    mid = 0.5 * (bid + ask)
                    current_margin = total_units[0] * mid / LEVERAGE
                    req_margin = new_units * mid / LEVERAGE

                    # Equity of current basket before adding.
                    units = total_units[0]
                    if open_dir[0] > 0:
                        liq_before = units * bid - weighted_entry_sum[0] - units * COMMISSION_PER_001
                    else:
                        liq_before = weighted_entry_sum[0] - units * ask - units * COMMISSION_PER_001
                    eq_before = balance[0] + liq_before
                    if eq_before - current_margin < req_margin:
                        failed[0] = 1
                        failure_day[0] = day
                        break

                    fill = ask if open_dir[0] > 0 else bid
                    total_units[0] += new_units
                    weighted_entry_sum[0] += new_units * fill
                    depth[0] += 1
                    if depth[0] > max_depth[0]:
                        max_depth[0] = depth[0]
                    if total_units[0] > max_total_units[0]:
                        max_total_units[0] = total_units[0]
                    if new_units > max_single_units[0]:
                        max_single_units[0] = new_units
                    if open_dir[0] > 0:
                        next_add_trigger[0] = fill - ADVERSE_DISTANCE
                    else:
                        next_add_trigger[0] = fill + ADVERSE_DISTANCE

                    # Immediate post-add risk check includes all round-trip commission reserve.
                    units2 = total_units[0]
                    if open_dir[0] > 0:
                        liq2 = units2 * bid - weighted_entry_sum[0] - units2 * COMMISSION_PER_001
                    else:
                        liq2 = weighted_entry_sum[0] - units2 * ask - units2 * COMMISSION_PER_001
                    eq2 = balance[0] + liq2
                    if eq2 < min_equity[0]:
                        min_equity[0] = eq2
                    if liq2 < worst_float[0]:
                        worst_float[0] = liq2
                    if eq2 <= 0.0:
                        failed[0] = 1
                        failure_day[0] = day
                        break

        # Rearm after price returns inside the current H1 reference range.
        if open_dir[0] == 0 and has_ref[0] != 0 and armed[0] == 0:
            if bid >= ref_lo[0] and bid <= ref_hi[0]:
                armed[0] = 1

        # Old H1 breakout entry: Ask crosses High => BUY; Bid crosses Low => SELL.
        if open_dir[0] == 0 and has_ref[0] != 0 and armed[0] != 0:
            direction = 0
            fill = 0.0
            if prev_ask <= ref_hi[0] and ask > ref_hi[0]:
                direction = 1
                fill = ask
            elif prev_bid >= ref_lo[0] and bid < ref_lo[0]:
                direction = -1
                fill = bid

            if direction != 0:
                units = 1.0  # 0.01 lot
                mid = 0.5 * (bid + ask)
                req_margin = units * mid / LEVERAGE
                if balance[0] < req_margin:
                    failed[0] = 1
                    failure_day[0] = day
                    break
                open_dir[0] = direction
                depth[0] = 1
                total_units[0] = units
                weighted_entry_sum[0] = fill
                next_add_trigger[0] = fill - ADVERSE_DISTANCE if direction > 0 else fill + ADVERSE_DISTANCE
                entries_started[0] += 1
                if max_depth[0] < 1:
                    max_depth[0] = 1
                if max_total_units[0] < 1.0:
                    max_total_units[0] = 1.0
                if max_single_units[0] < 1.0:
                    max_single_units[0] = 1.0
                armed[0] = 0

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

    balance = np.array([START_BALANCE], dtype=np.float64)
    failed = np.array([0], dtype=np.int64)
    failure_day = np.array([-1], dtype=np.int64)
    open_dir = np.array([0], dtype=np.int64)
    depth = np.array([0], dtype=np.int64)
    total_units = np.array([0.0], dtype=np.float64)
    weighted_entry_sum = np.array([0.0], dtype=np.float64)
    next_add_trigger = np.array([0.0], dtype=np.float64)
    ref_hi = np.array([0.0], dtype=np.float64)
    ref_lo = np.array([0.0], dtype=np.float64)
    has_ref = np.array([0], dtype=np.int64)
    armed = np.array([0], dtype=np.int64)
    baskets_closed = np.array([0], dtype=np.int64)
    entries_started = np.array([0], dtype=np.int64)
    min_equity = np.array([START_BALANCE], dtype=np.float64)
    max_depth = np.array([0], dtype=np.int64)
    max_total_units = np.array([0.0], dtype=np.float64)
    max_single_units = np.array([0.0], dtype=np.float64)
    worst_float = np.array([0.0], dtype=np.float64)
    total_commission_closed = np.array([0.0], dtype=np.float64)
    depth_hist = np.zeros(MAX_DEPTH_RECORD, dtype=np.int64)
    shared_i = np.array([-1, -1, 0], dtype=np.int64)
    shared_f = np.zeros(6, dtype=np.float64)

    # Compile.
    process_chunk(np.empty(0, dtype=np.int64), np.empty(0), np.empty(0),
                  balance, failed, failure_day, open_dir, depth, total_units, weighted_entry_sum, next_add_trigger,
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
                                      balance, failed, failure_day, open_dir, depth, total_units, weighted_entry_sum, next_add_trigger,
                                      ref_hi, ref_lo, has_ref, armed, baskets_closed, entries_started,
                                      min_equity, max_depth, max_total_units, max_single_units, worst_float, total_commission_closed,
                                      depth_hist, shared_i, shared_f)
                        month_rows += len(df)
                        total_rows += len(df)
                        if failed[0] != 0:
                            break
                if failed[0] != 0:
                    break
        provenance.append({'year': year, 'month': month, 'url': url, 'bytes': nbytes, 'sha256': sha, 'rows': month_rows})
        path.unlink(missing_ok=True)
        print(f'DONE {year}-{mm}: rows={month_rows:,} balance={balance[0]:.3f} depth={depth[0]} failed={failed[0]}', flush=True)
        if failed[0] != 0:
            break

    # End mark-to-market without forcing closure.
    marked_equity = balance[0]
    if open_dir[0] != 0:
        lb = shared_f[4]
        la = shared_f[5]
        units = total_units[0]
        if open_dir[0] > 0:
            liq = units * lb - weighted_entry_sum[0] - units * COMMISSION_PER_001
        else:
            liq = weighted_entry_sum[0] - units * la - units * COMMISSION_PER_001
        marked_equity += liq

    max_single_lot = max_single_units[0] * 0.01
    max_total_lots = max_total_units[0] * 0.01
    current_total_lots = total_units[0] * 0.01
    current_single_next_lot = (2.0 ** depth[0]) * 0.01 if open_dir[0] != 0 else 0.01

    summary = {
        'year': year,
        'failed': bool(failed[0]),
        'failure_date': day_to_iso(failure_day[0]),
        'starting_balance': START_BALANCE,
        'realized_balance': round(float(balance[0]), 6),
        'marked_equity': round(float(marked_equity), 6),
        'realized_profit': round(float(balance[0] - START_BALANCE), 6),
        'entries_started': int(entries_started[0]),
        'baskets_closed_at_target': int(baskets_closed[0]),
        'minimum_equity': round(float(min_equity[0]), 6),
        'worst_floating_basket_pnl': round(float(worst_float[0]), 6),
        'max_order_depth': int(max_depth[0]),
        'max_single_lot': round(float(max_single_lot), 6),
        'max_total_open_lots': round(float(max_total_lots), 6),
        'open_direction_at_end': int(open_dir[0]),
        'open_depth_at_end': int(depth[0]),
        'open_total_lots_at_end': round(float(current_total_lots), 6),
        'next_order_lot_if_needed': round(float(current_single_next_lot), 6),
        'target_net_usd_per_basket': BASKET_TARGET,
        'adverse_price_distance': ADVERSE_DISTANCE,
        'total_rows_processed': int(total_rows),
    }
    pd.DataFrame([summary]).to_csv(outdir / f'h1_martingale_100_50_{year}_summary.csv', index=False)

    hist_rows = []
    for d, n in enumerate(depth_hist):
        if n:
            hist_rows.append({'order_depth': d, 'closed_baskets': int(n), 'largest_lot_at_depth': round((2.0 ** (d-1))*0.01, 6) if d >= 1 else 0.0})
    pd.DataFrame(hist_rows).to_csv(outdir / f'h1_martingale_100_50_{year}_depth_hist.csv', index=False)
    with open(outdir / f'h1_martingale_100_50_{year}_provenance.json', 'w') as f:
        json.dump({'rules': {
            'entry': 'previous completed H1 High Ask-cross BUY / Low Bid-cross SELL; rearm after return inside H1 range',
            'first_lot': 0.01,
            'lot_sequence': '0.01,0.02,0.04,0.08,... same direction',
            'adverse_step_user_pips': 100,
            'adverse_step_xau_price': ADVERSE_DISTANCE,
            'basket_target_user_pips_equivalent': 50,
            'basket_target_net_usd': BASKET_TARGET,
            'commission_per_0.01_roundtrip': COMMISSION_PER_001,
            'leverage': LEVERAGE,
            'no_forced_loss_close': True,
            'no_daily_target_or_withdrawal': True,
        }, 'files': provenance, 'summary': summary}, f, indent=2)
    print(pd.DataFrame([summary]).to_string(index=False), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()
    if args.year not in (2025, 2026):
        raise SystemExit('year must be 2025 or 2026')
    run(args.year, args.outdir)
