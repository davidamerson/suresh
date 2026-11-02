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
PRICE_50PIPS = 5.0      # prior project normalization: 10 pips = $1 XAU move
PRICE_100PIPS = 10.0
GROUP_TARGET = 5.0      # 50-pip-equivalent net group target on 0.01-lot basis
MAX_EVENT_RING = 160


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
def main_units_for_depth(depth):
    # depth1=.01 lot => 1 unit; depth2=.02=>2; depth3=.04=>4; ...
    return 2.0 ** (depth - 1)


@njit(cache=True)
def hedge_units_for_even_depth(depth):
    # depth2 opens .01 hedge, depth4 .02, depth6 .04, ...
    return 2.0 ** (depth // 2 - 1)


@njit(cache=True)
def adverse_level_for_depth(depth):
    # Relative to FIRST main fill:
    # depth2 = 50 pips, depth3 = 100 pips, depth4 = 200, depth5=300, ...
    if depth == 2:
        return PRICE_50PIPS
    return (depth - 2) * PRICE_100PIPS


@njit(cache=True)
def push_event(ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
               ev_group_realized, ev_balance, ev_equity,
               t, code, price, depth, main_units, hedge_units, group_realized, balance, equity):
    n = ev_seq[0]
    idx = n % MAX_EVENT_RING
    ev_ts[idx] = t
    ev_code[idx] = code
    ev_price[idx] = price
    ev_depth[idx] = depth
    ev_main_units[idx] = main_units
    ev_hedge_units[idx] = hedge_units
    ev_group_realized[idx] = group_realized
    ev_balance[idx] = balance
    ev_equity[idx] = equity
    ev_seq[0] = n + 1


@njit(cache=True)
def calc_main_liq(direction, main_units, main_entry_sum, bid, ask):
    if main_units <= 0.0:
        return 0.0
    if direction > 0:
        return main_units * bid - main_entry_sum - main_units * COMMISSION_PER_001
    return main_entry_sum - main_units * ask - main_units * COMMISSION_PER_001


@njit(cache=True)
def calc_hedge_liq(direction, hedge_units, hedge_entry_sum, bid, ask):
    if hedge_units <= 0.0:
        return 0.0
    # Hedge is opposite the main direction.
    if direction > 0:  # main BUY => hedge SELL
        return hedge_entry_sum - hedge_units * ask - hedge_units * COMMISSION_PER_001
    # main SELL => hedge BUY
    return hedge_units * bid - hedge_entry_sum - hedge_units * COMMISSION_PER_001


@njit(cache=True)
def process_chunk(ts, bids, asks,
                  balance, failed, failure_day, failure_reason, failure_equity,
                  direction, depth, first_fill, main_units, main_entry_sum,
                  hedge_units, hedge_entry_sum, group_realized,
                  ref_hi, ref_lo, has_ref, armed,
                  entries_started, groups_closed, hedges_opened, hedges_closed,
                  min_equity, worst_group_float, max_depth, max_main_units, max_hedge_units, max_gross_units,
                  total_group_profit, total_hedge_realized,
                  shared_i, shared_f,
                  ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                  ev_group_realized, ev_balance, ev_equity):
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
        mid = 0.5 * (bid + ask)

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

        # Old exact H1 convention: completed clock-hour reference updates only while flat.
        if hour != cur_hour:
            if direction[0] == 0:
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

        if direction[0] != 0:
            mliq = calc_main_liq(direction[0], main_units[0], main_entry_sum[0], bid, ask)
            hliq = calc_hedge_liq(direction[0], hedge_units[0], hedge_entry_sum[0], bid, ask)
            current_group = group_realized[0] + mliq + hliq
            equity = balance[0] + mliq + hliq

            if equity < min_equity[0]:
                min_equity[0] = equity
            if current_group < worst_group_float[0]:
                worst_group_float[0] = current_group
            if equity <= 0.0:
                failed[0] = 1
                failure_day[0] = day
                failure_reason[0] = 1
                failure_equity[0] = equity
                push_event(ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                           ev_group_realized, ev_balance, ev_equity,
                           t, 6, mid, depth[0], main_units[0], hedge_units[0], group_realized[0], balance[0], equity)
                break

            # Entire group closes only when cumulative realized hedge P/L + all open liquidation P/L reaches target.
            if current_group >= GROUP_TARGET:
                balance[0] += mliq + hliq
                total_group_profit[0] += current_group
                groups_closed[0] += 1
                push_event(ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                           ev_group_realized, ev_balance, ev_equity,
                           t, 5, mid, depth[0], main_units[0], hedge_units[0], group_realized[0], balance[0], balance[0])
                direction[0] = 0
                depth[0] = 0
                first_fill[0] = 0.0
                main_units[0] = 0.0
                main_entry_sum[0] = 0.0
                hedge_units[0] = 0.0
                hedge_entry_sum[0] = 0.0
                group_realized[0] = 0.0
                armed[0] = 0
            else:
                # Process each absolute adverse level relative to the FIRST main fill.
                for _ in range(32):
                    next_depth = depth[0] + 1
                    adverse = adverse_level_for_depth(next_depth)
                    trigger = first_fill[0] - adverse if direction[0] > 0 else first_fill[0] + adverse
                    crossed = (direction[0] > 0 and bid <= trigger) or (direction[0] < 0 and ask >= trigger)
                    if not crossed:
                        break

                    # At odd depths >=3, close the currently open hedge first.
                    if next_depth >= 3 and next_depth % 2 == 1 and hedge_units[0] > 0.0:
                        hedge_pnl = calc_hedge_liq(direction[0], hedge_units[0], hedge_entry_sum[0], bid, ask)
                        balance[0] += hedge_pnl
                        group_realized[0] += hedge_pnl
                        total_hedge_realized[0] += hedge_pnl
                        hedges_closed[0] += 1
                        push_event(ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                                   ev_group_realized, ev_balance, ev_equity,
                                   t, 4, mid, depth[0], main_units[0], hedge_units[0], group_realized[0], balance[0], balance[0] + calc_main_liq(direction[0], main_units[0], main_entry_sum[0], bid, ask))
                        hedge_units[0] = 0.0
                        hedge_entry_sum[0] = 0.0

                        # Target can be reached by realized hedge profit before adding next main order.
                        mliq_now = calc_main_liq(direction[0], main_units[0], main_entry_sum[0], bid, ask)
                        current_group_now = group_realized[0] + mliq_now
                        if current_group_now >= GROUP_TARGET:
                            balance[0] += mliq_now
                            total_group_profit[0] += current_group_now
                            groups_closed[0] += 1
                            push_event(ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                                       ev_group_realized, ev_balance, ev_equity,
                                       t, 5, mid, depth[0], main_units[0], 0.0, group_realized[0], balance[0], balance[0])
                            direction[0] = 0
                            depth[0] = 0
                            first_fill[0] = 0.0
                            main_units[0] = 0.0
                            main_entry_sum[0] = 0.0
                            group_realized[0] = 0.0
                            armed[0] = 0
                            break

                    if direction[0] == 0:
                        break

                    new_main = main_units_for_depth(next_depth)
                    new_hedge = 0.0
                    if next_depth % 2 == 0:
                        new_hedge = hedge_units_for_even_depth(next_depth)

                    mliq_before = calc_main_liq(direction[0], main_units[0], main_entry_sum[0], bid, ask)
                    hliq_before = calc_hedge_liq(direction[0], hedge_units[0], hedge_entry_sum[0], bid, ask)
                    equity_before = balance[0] + mliq_before + hliq_before
                    current_margin = (main_units[0] + hedge_units[0]) * mid / LEVERAGE
                    req_margin = (new_main + new_hedge) * mid / LEVERAGE
                    free_margin = equity_before - current_margin
                    if free_margin < req_margin:
                        failed[0] = 1
                        failure_day[0] = day
                        failure_reason[0] = 2
                        failure_equity[0] = equity_before
                        push_event(ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                                   ev_group_realized, ev_balance, ev_equity,
                                   t, 7, mid, depth[0], main_units[0], hedge_units[0], group_realized[0], balance[0], equity_before)
                        break

                    main_fill = ask if direction[0] > 0 else bid
                    main_units[0] += new_main
                    main_entry_sum[0] += new_main * main_fill
                    depth[0] = next_depth
                    if depth[0] > max_depth[0]:
                        max_depth[0] = depth[0]
                    if main_units[0] > max_main_units[0]:
                        max_main_units[0] = main_units[0]
                    push_event(ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                               ev_group_realized, ev_balance, ev_equity,
                               t, 2, main_fill, depth[0], main_units[0], hedge_units[0], group_realized[0], balance[0], equity_before)

                    # Open opposite hedge together with each even-depth main add.
                    if new_hedge > 0.0:
                        hedge_fill = bid if direction[0] > 0 else ask
                        hedge_units[0] = new_hedge
                        hedge_entry_sum[0] = new_hedge * hedge_fill
                        hedges_opened[0] += 1
                        if hedge_units[0] > max_hedge_units[0]:
                            max_hedge_units[0] = hedge_units[0]
                        push_event(ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                                   ev_group_realized, ev_balance, ev_equity,
                                   t, 3, hedge_fill, depth[0], main_units[0], hedge_units[0], group_realized[0], balance[0], equity_before)

                    gross = main_units[0] + hedge_units[0]
                    if gross > max_gross_units[0]:
                        max_gross_units[0] = gross

                    # Immediate post-add mark including all commission reserve/spread.
                    mliq2 = calc_main_liq(direction[0], main_units[0], main_entry_sum[0], bid, ask)
                    hliq2 = calc_hedge_liq(direction[0], hedge_units[0], hedge_entry_sum[0], bid, ask)
                    eq2 = balance[0] + mliq2 + hliq2
                    group2 = group_realized[0] + mliq2 + hliq2
                    if eq2 < min_equity[0]:
                        min_equity[0] = eq2
                    if group2 < worst_group_float[0]:
                        worst_group_float[0] = group2
                    if eq2 <= 0.0:
                        failed[0] = 1
                        failure_day[0] = day
                        failure_reason[0] = 1
                        failure_equity[0] = eq2
                        push_event(ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                                   ev_group_realized, ev_balance, ev_equity,
                                   t, 6, mid, depth[0], main_units[0], hedge_units[0], group_realized[0], balance[0], eq2)
                        break

                if failed[0] != 0:
                    break

        # Rearm only after price comes back inside H1 reference range.
        if direction[0] == 0 and has_ref[0] != 0 and armed[0] == 0:
            if bid >= ref_lo[0] and bid <= ref_hi[0]:
                armed[0] = 1

        # Exact old H1 breakout entry.
        if direction[0] == 0 and has_ref[0] != 0 and armed[0] != 0:
            d = 0
            fill = 0.0
            if prev_ask <= ref_hi[0] and ask > ref_hi[0]:
                d = 1
                fill = ask
            elif prev_bid >= ref_lo[0] and bid < ref_lo[0]:
                d = -1
                fill = bid
            if d != 0:
                req_margin = 1.0 * mid / LEVERAGE
                if balance[0] < req_margin:
                    failed[0] = 1
                    failure_day[0] = day
                    failure_reason[0] = 2
                    failure_equity[0] = balance[0]
                    break
                direction[0] = d
                depth[0] = 1
                first_fill[0] = fill
                main_units[0] = 1.0
                main_entry_sum[0] = fill
                hedge_units[0] = 0.0
                hedge_entry_sum[0] = 0.0
                group_realized[0] = 0.0
                entries_started[0] += 1
                if max_depth[0] < 1:
                    max_depth[0] = 1
                if max_main_units[0] < 1.0:
                    max_main_units[0] = 1.0
                if max_gross_units[0] < 1.0:
                    max_gross_units[0] = 1.0
                armed[0] = 0
                entry_eq = balance[0] + calc_main_liq(d, 1.0, fill, bid, ask)
                push_event(ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                           ev_group_realized, ev_balance, ev_equity,
                           t, 1, fill, 1, 1.0, 0.0, 0.0, balance[0], entry_eq)

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


def failure_reason_text(code):
    return {0: '', 1: 'equity<=0', 2: 'insufficient_free_margin_for_next_order'}.get(int(code), 'unknown')


def run(year, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    months = list(range(1, 13)) if year == 2025 else list(range(1, 11))

    balance = np.array([START_BALANCE], dtype=np.float64)
    failed = np.array([0], dtype=np.int64)
    failure_day = np.array([-1], dtype=np.int64)
    failure_reason = np.array([0], dtype=np.int64)
    failure_equity = np.array([np.nan], dtype=np.float64)
    direction = np.array([0], dtype=np.int64)
    depth = np.array([0], dtype=np.int64)
    first_fill = np.array([0.0], dtype=np.float64)
    main_units = np.array([0.0], dtype=np.float64)
    main_entry_sum = np.array([0.0], dtype=np.float64)
    hedge_units = np.array([0.0], dtype=np.float64)
    hedge_entry_sum = np.array([0.0], dtype=np.float64)
    group_realized = np.array([0.0], dtype=np.float64)
    ref_hi = np.array([0.0], dtype=np.float64)
    ref_lo = np.array([0.0], dtype=np.float64)
    has_ref = np.array([0], dtype=np.int64)
    armed = np.array([0], dtype=np.int64)
    entries_started = np.array([0], dtype=np.int64)
    groups_closed = np.array([0], dtype=np.int64)
    hedges_opened = np.array([0], dtype=np.int64)
    hedges_closed = np.array([0], dtype=np.int64)
    min_equity = np.array([START_BALANCE], dtype=np.float64)
    worst_group_float = np.array([0.0], dtype=np.float64)
    max_depth = np.array([0], dtype=np.int64)
    max_main_units = np.array([0.0], dtype=np.float64)
    max_hedge_units = np.array([0.0], dtype=np.float64)
    max_gross_units = np.array([0.0], dtype=np.float64)
    total_group_profit = np.array([0.0], dtype=np.float64)
    total_hedge_realized = np.array([0.0], dtype=np.float64)
    shared_i = np.array([-1, -1, 0], dtype=np.int64)
    shared_f = np.zeros(6, dtype=np.float64)

    ev_seq = np.array([0], dtype=np.int64)
    ev_ts = np.zeros(MAX_EVENT_RING, dtype=np.int64)
    ev_code = np.zeros(MAX_EVENT_RING, dtype=np.int64)
    ev_price = np.zeros(MAX_EVENT_RING, dtype=np.float64)
    ev_depth = np.zeros(MAX_EVENT_RING, dtype=np.int64)
    ev_main_units = np.zeros(MAX_EVENT_RING, dtype=np.float64)
    ev_hedge_units = np.zeros(MAX_EVENT_RING, dtype=np.float64)
    ev_group_realized = np.zeros(MAX_EVENT_RING, dtype=np.float64)
    ev_balance = np.zeros(MAX_EVENT_RING, dtype=np.float64)
    ev_equity = np.zeros(MAX_EVENT_RING, dtype=np.float64)

    process_chunk(np.empty(0, dtype=np.int64), np.empty(0), np.empty(0),
                  balance, failed, failure_day, failure_reason, failure_equity,
                  direction, depth, first_fill, main_units, main_entry_sum,
                  hedge_units, hedge_entry_sum, group_realized,
                  ref_hi, ref_lo, has_ref, armed,
                  entries_started, groups_closed, hedges_opened, hedges_closed,
                  min_equity, worst_group_float, max_depth, max_main_units, max_hedge_units, max_gross_units,
                  total_group_profit, total_hedge_realized,
                  shared_i, shared_f,
                  ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                  ev_group_realized, ev_balance, ev_equity)

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
                                      balance, failed, failure_day, failure_reason, failure_equity,
                                      direction, depth, first_fill, main_units, main_entry_sum,
                                      hedge_units, hedge_entry_sum, group_realized,
                                      ref_hi, ref_lo, has_ref, armed,
                                      entries_started, groups_closed, hedges_opened, hedges_closed,
                                      min_equity, worst_group_float, max_depth, max_main_units, max_hedge_units, max_gross_units,
                                      total_group_profit, total_hedge_realized,
                                      shared_i, shared_f,
                                      ev_seq, ev_ts, ev_code, ev_price, ev_depth, ev_main_units, ev_hedge_units,
                                      ev_group_realized, ev_balance, ev_equity)
                        month_rows += len(df)
                        total_rows += len(df)
                        if failed[0] != 0:
                            break
                if failed[0] != 0:
                    break
        provenance.append({'year': year, 'month': month, 'url': url, 'bytes': nbytes, 'sha256': sha, 'rows': month_rows})
        path.unlink(missing_ok=True)
        print(f'DONE {year}-{mm}: rows={month_rows:,} balance={balance[0]:.3f} depth={depth[0]} hedge={hedge_units[0]*0.01:.3f} failed={failed[0]}', flush=True)
        if failed[0] != 0:
            break

    last_bid, last_ask = shared_f[4], shared_f[5]
    open_main_liq = 0.0
    open_hedge_liq = 0.0
    marked_equity = balance[0]
    open_group_net = group_realized[0]
    if direction[0] != 0 and failed[0] == 0:
        open_main_liq = float(calc_main_liq(direction[0], main_units[0], main_entry_sum[0], last_bid, last_ask))
        open_hedge_liq = float(calc_hedge_liq(direction[0], hedge_units[0], hedge_entry_sum[0], last_bid, last_ask))
        marked_equity = balance[0] + open_main_liq + open_hedge_liq
        open_group_net = group_realized[0] + open_main_liq + open_hedge_liq
    elif failed[0] != 0:
        marked_equity = failure_equity[0]

    summary = {
        'system': 'H1_DOUBLING_WITH_ALTERNATE_HEDGE_GROUP',
        'year': year,
        'failed': bool(failed[0]),
        'failure_date': day_to_iso(failure_day[0]),
        'failure_reason': failure_reason_text(failure_reason[0]),
        'failure_equity': None if not math.isfinite(float(failure_equity[0])) else round(float(failure_equity[0]), 6),
        'starting_balance': START_BALANCE,
        'realized_balance': round(float(balance[0]), 6),
        'marked_equity': round(float(marked_equity), 6),
        'entries_started': int(entries_started[0]),
        'groups_closed_at_target': int(groups_closed[0]),
        'group_close_rate_pct': round(100.0 * groups_closed[0] / entries_started[0], 4) if entries_started[0] else 0.0,
        'hedges_opened': int(hedges_opened[0]),
        'hedges_closed_before_group': int(hedges_closed[0]),
        'total_realized_hedge_pnl': round(float(total_hedge_realized[0]), 6),
        'total_group_profit_at_closes': round(float(total_group_profit[0]), 6),
        'minimum_equity': round(float(min_equity[0]), 6),
        'worst_group_net_pnl': round(float(worst_group_float[0]), 6),
        'max_main_depth': int(max_depth[0]),
        'max_main_lots': round(float(max_main_units[0] * 0.01), 6),
        'max_hedge_lots': round(float(max_hedge_units[0] * 0.01), 6),
        'max_gross_open_lots': round(float(max_gross_units[0] * 0.01), 6),
        'open_direction_at_end': int(direction[0]),
        'open_depth_at_end': int(depth[0]),
        'open_main_lots_at_end': round(float(main_units[0] * 0.01), 6),
        'open_hedge_lots_at_end': round(float(hedge_units[0] * 0.01), 6),
        'open_group_realized_hedge_pnl': round(float(group_realized[0]), 6),
        'open_group_net_at_end': round(float(open_group_net), 6),
        'rows_processed': int(total_rows),
        'rule_main_levels_pips': '0,50,100,200,300,400,...',
        'rule_main_lots': '0.01,0.02,0.04,0.08,0.16,0.32,...',
        'rule_hedges': 'open SELL/BUY opposite at main depths 2,4,6... with 0.01,0.02,0.04...; close at next odd main depth',
        'group_target_net_usd_equivalent': GROUP_TARGET,
    }

    pd.DataFrame([summary]).to_csv(outdir / 'summary.csv', index=False)
    with open(outdir / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    with open(outdir / 'provenance.json', 'w') as f:
        json.dump(provenance, f, indent=2)

    # Reconstruct the last event ring in chronological sequence.
    code_names = {1: 'MAIN_ENTRY', 2: 'MAIN_ADD', 3: 'HEDGE_OPEN', 4: 'HEDGE_CLOSE', 5: 'GROUP_CLOSE', 6: 'FAIL_EQUITY', 7: 'FAIL_MARGIN'}
    total_ev = int(ev_seq[0])
    n = min(total_ev, MAX_EVENT_RING)
    start = max(0, total_ev - n)
    rows = []
    for seq in range(start, total_ev):
        idx = seq % MAX_EVENT_RING
        ts_val = int(ev_ts[idx])
        ts_iso = ''
        if ts_val > 0:
            ts_iso = str(pd.Timestamp(ts_val, unit='ns', tz='UTC'))
        rows.append({
            'seq': seq,
            'timestamp': ts_iso,
            'event': code_names.get(int(ev_code[idx]), str(int(ev_code[idx]))),
            'price': ev_price[idx],
            'main_depth': int(ev_depth[idx]),
            'main_lots': ev_main_units[idx] * 0.01,
            'hedge_lots': ev_hedge_units[idx] * 0.01,
            'group_realized_hedge_pnl': ev_group_realized[idx],
            'account_balance': ev_balance[idx],
            'equity': ev_equity[idx],
        })
    pd.DataFrame(rows).to_csv(outdir / 'last_events.csv', index=False)

    print(pd.DataFrame([summary]).to_string(index=False), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, required=True, choices=[2025, 2026])
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()
    run(args.year, args.outdir)
