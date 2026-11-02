import argparse
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

START_BALANCE = 1000.0
DAILY_TARGET = 20.0
DAILY_WITHDRAW = 10.0
LEVERAGE = 2000.0
COMMISSION_PER_LOT_RT = 7.0
LOT_STEP = 0.01
MAX_LOT = 0.10
SPREAD_HARD_CAP = 0.50
MAX_HOLD_MIN = 60


def download(url, out):
    with requests.get(url, stream=True, timeout=(30, 300)) as r:
        r.raise_for_status()
        with open(out, 'wb') as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)


def aggregate_month(year, month, workdir):
    mm = f'{month:02d}'
    fn = f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'
    url = f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{fn}'
    path = workdir / fn
    print('DOWNLOAD', url, flush=True)
    download(url, path)
    parts = []
    with zipfile.ZipFile(path) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith('.csv')]
        if not csvs:
            raise RuntimeError(f'No CSV in {fn}')
        for csv_name in csvs:
            with z.open(csv_name) as fh:
                for df in pd.read_csv(fh, usecols=['Timestamp', 'Bid', 'Ask'], chunksize=500_000):
                    t = pd.to_datetime(df['Timestamp'], utc=True, errors='coerce')
                    good = t.notna() & df['Bid'].notna() & df['Ask'].notna()
                    if year == 2026 and month == 10:
                        good &= (t <= pd.Timestamp('2026-10-29 23:59:59.999999999', tz='UTC'))
                    if not bool(good.all()):
                        df = df.loc[good].copy()
                        t = t.loc[good]
                    if len(df) == 0:
                        continue
                    minute = t.dt.floor('min').to_numpy()
                    bid = df['Bid'].to_numpy(dtype=float)
                    ask = df['Ask'].to_numpy(dtype=float)
                    mid = 0.5 * (bid + ask)
                    spread = ask - bid
                    x = pd.DataFrame({'minute': minute, 'bid': bid, 'ask': ask, 'mid': mid, 'spread': spread})
                    g = x.groupby('minute', sort=False).agg(
                        bid_o=('bid', 'first'), bid_h=('bid', 'max'), bid_l=('bid', 'min'), bid_c=('bid', 'last'),
                        ask_o=('ask', 'first'), ask_h=('ask', 'max'), ask_l=('ask', 'min'), ask_c=('ask', 'last'),
                        mid_o=('mid', 'first'), mid_h=('mid', 'max'), mid_l=('mid', 'min'), mid_c=('mid', 'last'),
                        spread_sum=('spread', 'sum'), ticks=('spread', 'size'))
                    parts.append(g.reset_index())
    path.unlink(missing_ok=True)
    m = pd.concat(parts, ignore_index=True).sort_values('minute')
    # Consolidate any minute split across source/chunk boundaries.
    m = m.groupby('minute', sort=True).agg(
        bid_o=('bid_o', 'first'), bid_h=('bid_h', 'max'), bid_l=('bid_l', 'min'), bid_c=('bid_c', 'last'),
        ask_o=('ask_o', 'first'), ask_h=('ask_h', 'max'), ask_l=('ask_l', 'min'), ask_c=('ask_c', 'last'),
        mid_o=('mid_o', 'first'), mid_h=('mid_h', 'max'), mid_l=('mid_l', 'min'), mid_c=('mid_c', 'last'),
        spread_sum=('spread_sum', 'sum'), ticks=('ticks', 'sum')).reset_index()
    m['spread_mean'] = m['spread_sum'] / m['ticks']
    m = m.drop(columns=['spread_sum']).set_index('minute')
    print(f'AGG {year}-{mm}: 1m bars={len(m):,}', flush=True)
    return m


def load_year(year, workdir):
    months = range(1, 13) if year == 2025 else range(1, 11)
    out = []
    for month in months:
        out.append(aggregate_month(year, month, workdir))
    df = pd.concat(out).sort_index()
    return df[~df.index.duplicated(keep='last')]


def add_indicators(m1):
    m1 = m1.copy()
    typical = (m1['mid_h'] + m1['mid_l'] + m1['mid_c']) / 3.0
    day = m1.index.normalize()
    pv = typical * m1['ticks']
    m1['tvwap'] = pv.groupby(day).cumsum() / m1['ticks'].groupby(day).cumsum()

    agg = {
        'mid_o': 'first', 'mid_h': 'max', 'mid_l': 'min', 'mid_c': 'last',
        'bid_o': 'first', 'bid_h': 'max', 'bid_l': 'min', 'bid_c': 'last',
        'ask_o': 'first', 'ask_h': 'max', 'ask_l': 'min', 'ask_c': 'last',
        'ticks': 'sum', 'spread_mean': 'mean', 'tvwap': 'last'
    }
    m5 = m1.resample('5min', label='left', closed='left').agg(agg).dropna(subset=['mid_o', 'mid_c'])
    c = m5['mid_c']
    h = m5['mid_h']
    l = m5['mid_l']
    pc = c.shift(1)
    tr = pd.concat([(h-l), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    m5['atr'] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    m5['ema20'] = c.ewm(span=20, adjust=False, min_periods=20).mean()
    m5['ema50'] = c.ewm(span=50, adjust=False, min_periods=50).mean()
    m5['ema200'] = c.ewm(span=200, adjust=False, min_periods=200).mean()
    rng = (h-l).replace(0, np.nan)
    m5['body_ratio'] = (c-m5['mid_o']).abs()/rng
    diff = c.diff().abs()
    m5['eff6'] = (c-c.shift(6)).abs() / diff.rolling(6).sum()
    m5['roll6_hi'] = h.shift(1).rolling(6).max()
    m5['roll6_lo'] = l.shift(1).rolling(6).min()
    return m1, m5


def news_block(ts):
    hm = ts.hour * 60 + ts.minute
    # Fixed blocks cover the common 08:30 ET US-data slot in both DST and standard time.
    return (12*60+25 <= hm < 12*60+40) or (13*60+25 <= hm < 13*60+40)


def in_trade_session(ts):
    hm = ts.hour * 60 + ts.minute
    return (7*60 <= hm < 10*60) or (12*60 <= hm < 16*60)


def session_end_for(ts):
    day = ts.normalize()
    hm = ts.hour * 60 + ts.minute
    if 7*60 <= hm < 10*60:
        return day + pd.Timedelta(hours=10)
    return day + pd.Timedelta(hours=16)


def signal_row(ts, direction, atr, anchor, strength, source):
    return {
        'time': ts + pd.Timedelta(minutes=5),
        'direction': int(direction),
        'atr': float(atr),
        'anchor': float(anchor),
        'strength': float(strength),
        'source': source,
        'session_end': session_end_for(ts),
    }


def generate_orb(m5, or_minutes=15):
    sigs = []
    for day, d in m5.groupby(m5.index.normalize()):
        for sh, eh in [(7, 10), (12, 16)]:
            s = day + pd.Timedelta(hours=sh)
            oe = s + pd.Timedelta(minutes=or_minutes)
            e = day + pd.Timedelta(hours=eh)
            orb = d[(d.index >= s) & (d.index < oe)]
            if len(orb) < max(2, or_minutes//5):
                continue
            or_hi = orb['mid_h'].max(); or_lo = orb['mid_l'].min()
            trail = d[(d.index >= oe) & (d.index < e)]
            pending = 0; expiry = None; used_long = 0; used_short = 0
            for ts, r in trail.iterrows():
                if not math.isfinite(r['atr']) or not math.isfinite(r['ema200']) or news_block(ts):
                    continue
                atr = r['atr']
                if (or_hi-or_lo) > 2.6*atr or (or_hi-or_lo) < 0.25*atr:
                    continue
                if pending != 0:
                    if ts > expiry:
                        pending = 0
                    elif pending > 0:
                        if r['mid_l'] <= or_hi + 0.25*atr and r['mid_c'] > or_hi and r['mid_c'] > r['mid_o'] and r['body_ratio'] >= 0.30:
                            anchor = min(r['mid_l'] - 0.10*atr, or_hi - 0.10*atr)
                            sigs.append(signal_row(ts, 1, atr, anchor, r['body_ratio']+r['eff6'], f'ORB{or_minutes}'))
                            used_long = 1; pending = 0
                        elif r['mid_c'] < or_hi - 0.25*atr:
                            pending = 0
                    else:
                        if r['mid_h'] >= or_lo - 0.25*atr and r['mid_c'] < or_lo and r['mid_c'] < r['mid_o'] and r['body_ratio'] >= 0.30:
                            anchor = max(r['mid_h'] + 0.10*atr, or_lo + 0.10*atr)
                            sigs.append(signal_row(ts, -1, atr, anchor, r['body_ratio']+r['eff6'], f'ORB{or_minutes}'))
                            used_short = 1; pending = 0
                        elif r['mid_c'] > or_lo + 0.25*atr:
                            pending = 0
                if pending == 0:
                    rrng = r['mid_h']-r['mid_l']
                    long_regime = r['ema20'] > r['ema50'] and r['mid_c'] > r['ema200'] and r['mid_c'] > r['tvwap'] and r['eff6'] >= 0.30
                    short_regime = r['ema20'] < r['ema50'] and r['mid_c'] < r['ema200'] and r['mid_c'] < r['tvwap'] and r['eff6'] >= 0.30
                    if not used_long and long_regime and r['mid_c'] > or_hi + 0.08*atr and r['body_ratio'] >= 0.50 and rrng <= 1.8*atr:
                        pending = 1; expiry = ts + pd.Timedelta(minutes=20)
                    elif not used_short and short_regime and r['mid_c'] < or_lo - 0.08*atr and r['body_ratio'] >= 0.50 and rrng <= 1.8*atr:
                        pending = -1; expiry = ts + pd.Timedelta(minutes=20)
    return pd.DataFrame(sigs)


def generate_ema_pullback(m5):
    sigs = []
    last_signal = None
    prev = None
    for ts, r in m5.iterrows():
        if not in_trade_session(ts) or news_block(ts) or prev is None:
            prev = r; continue
        if not (math.isfinite(r['atr']) and math.isfinite(r['ema200']) and math.isfinite(r['eff6'])):
            prev = r; continue
        if last_signal is not None and ts - last_signal < pd.Timedelta(minutes=15):
            prev = r; continue
        atr = r['atr']
        long_regime = r['ema20'] > r['ema50'] > r['ema200'] and r['mid_c'] > r['tvwap'] and r['eff6'] >= 0.32
        short_regime = r['ema20'] < r['ema50'] < r['ema200'] and r['mid_c'] < r['tvwap'] and r['eff6'] >= 0.32
        if long_regime and prev['mid_l'] <= prev['ema20'] + 0.15*atr and r['mid_c'] > r['ema20'] and r['mid_c'] > prev['mid_h'] and r['mid_c'] > r['mid_o'] and r['body_ratio'] >= 0.42:
            anchor = min(prev['mid_l'], r['mid_l']) - 0.10*atr
            sigs.append(signal_row(ts, 1, atr, anchor, r['body_ratio']+r['eff6'], 'EMA_PULL'))
            last_signal = ts
        elif short_regime and prev['mid_h'] >= prev['ema20'] - 0.15*atr and r['mid_c'] < r['ema20'] and r['mid_c'] < prev['mid_l'] and r['mid_c'] < r['mid_o'] and r['body_ratio'] >= 0.42:
            anchor = max(prev['mid_h'], r['mid_h']) + 0.10*atr
            sigs.append(signal_row(ts, -1, atr, anchor, r['body_ratio']+r['eff6'], 'EMA_PULL'))
            last_signal = ts
        prev = r
    return pd.DataFrame(sigs)


def generate_sweep(m5):
    sigs = []
    last_signal = None
    for ts, r in m5.iterrows():
        if not in_trade_session(ts) or news_block(ts):
            continue
        if not all(math.isfinite(r[x]) for x in ['atr','ema200','roll6_hi','roll6_lo']):
            continue
        if last_signal is not None and ts-last_signal < pd.Timedelta(minutes=10):
            continue
        atr = r['atr']
        long_ok = r['mid_l'] < r['roll6_lo'] - 0.08*atr and r['mid_c'] > r['roll6_lo'] and r['mid_c'] > r['mid_o'] and r['body_ratio'] >= 0.40 and r['mid_c'] > r['ema200']
        short_ok = r['mid_h'] > r['roll6_hi'] + 0.08*atr and r['mid_c'] < r['roll6_hi'] and r['mid_c'] < r['mid_o'] and r['body_ratio'] >= 0.40 and r['mid_c'] < r['ema200']
        if long_ok:
            sigs.append(signal_row(ts, 1, atr, r['mid_l']-0.10*atr, r['body_ratio']+0.5, 'SWEEP'))
            last_signal = ts
        elif short_ok:
            sigs.append(signal_row(ts, -1, atr, r['mid_h']+0.10*atr, r['body_ratio']+0.5, 'SWEEP'))
            last_signal = ts
    return pd.DataFrame(sigs)


def combine_signals(*dfs):
    good = [d for d in dfs if d is not None and len(d)]
    if not good:
        return pd.DataFrame(columns=['time','direction','atr','anchor','strength','source','session_end'])
    x = pd.concat(good, ignore_index=True).sort_values(['time','strength'], ascending=[True,False])
    return x.drop_duplicates('time', keep='first').reset_index(drop=True)


def trade_pnl(direction, entry, exit_px, lots):
    gross = (exit_px-entry)*lots*100.0 if direction > 0 else (entry-exit_px)*lots*100.0
    return gross - COMMISSION_PER_LOT_RT*lots


def simulate(m1, signals, rr, risk_usd, daily_loss_cap, start, end):
    data = m1[(m1.index >= start) & (m1.index <= end)]
    sig = signals[(signals['time'] >= start) & (signals['time'] <= end)].copy() if len(signals) else signals.copy()
    sig_map = {}
    for r in sig.to_dict('records'):
        sig_map.setdefault(pd.Timestamp(r['time']), []).append(r)

    balance = START_BALANCE; withdrawn = 0.0; open_trade = None
    cur_day = None; day_realized = 0.0; stopped = False; target_days = 0
    traded_days = set(); wins = 0; losses = 0; trades = 0; loss_days = 0
    daily_pnls = []; max_daily_loss = 0.0; peak_eq = START_BALANCE; max_dd = 0.0
    failed = False; failure_date = ''

    for ts, b in data.iterrows():
        day = ts.normalize()
        if cur_day is None or day != cur_day:
            if cur_day is not None:
                daily_pnls.append(day_realized)
                if day_realized < -1e-9: loss_days += 1
                max_daily_loss = min(max_daily_loss, day_realized)
            cur_day = day; day_realized = 0.0; stopped = False

        # Manage existing position.
        if open_trade is not None:
            t = open_trade; exit_px = None; reason = None
            if t['direction'] > 0:
                stop_hit = b['bid_l'] <= t['stop']; tp_hit = b['bid_h'] >= t['tp']
                if stop_hit and tp_hit: exit_px=t['stop']; reason='SL_BOTH'
                elif stop_hit: exit_px=t['stop']; reason='SL'
                elif tp_hit: exit_px=t['tp']; reason='TP'
            else:
                stop_hit = b['ask_h'] >= t['stop']; tp_hit = b['ask_l'] <= t['tp']
                if stop_hit and tp_hit: exit_px=t['stop']; reason='SL_BOTH'
                elif stop_hit: exit_px=t['stop']; reason='SL'
                elif tp_hit: exit_px=t['tp']; reason='TP'
            if exit_px is not None:
                pnl = trade_pnl(t['direction'], t['entry'], exit_px, t['lots'])
                balance += pnl; day_realized += pnl; trades += 1; traded_days.add(day)
                if pnl > 0: wins += 1
                else: losses += 1
                open_trade = None
            else:
                close_px = b['bid_c'] if t['direction'] > 0 else b['ask_c']
                floating = trade_pnl(t['direction'], t['entry'], close_px, t['lots'])
                # Daily target and daily loss cap are enforced on current liquidation P/L.
                if day_realized + floating >= DAILY_TARGET:
                    balance += floating; day_realized += floating; trades += 1; traded_days.add(day)
                    wins += int(floating > 0); losses += int(floating <= 0)
                    open_trade = None; withdrawn += DAILY_WITHDRAW; balance -= DAILY_WITHDRAW
                    target_days += 1; stopped = True
                elif day_realized + floating <= -daily_loss_cap or ts >= t['session_end'] or (ts-t['entry_time']).total_seconds()/60 >= MAX_HOLD_MIN:
                    balance += floating; day_realized += floating; trades += 1; traded_days.add(day)
                    wins += int(floating > 0); losses += int(floating <= 0)
                    open_trade = None
                    if day_realized <= -daily_loss_cap: stopped = True

        # If a normal TP pushed daily realized over target, withdraw and stop.
        if open_trade is None and not stopped and day_realized >= DAILY_TARGET:
            withdrawn += DAILY_WITHDRAW; balance -= DAILY_WITHDRAW; target_days += 1; stopped = True

        equity = balance
        if open_trade is not None:
            close_px = b['bid_c'] if open_trade['direction'] > 0 else b['ask_c']
            equity += trade_pnl(open_trade['direction'], open_trade['entry'], close_px, open_trade['lots'])
        peak_eq = max(peak_eq, equity)
        if peak_eq > 0: max_dd = max(max_dd, (peak_eq-equity)/peak_eq)
        if equity <= 0 or balance <= 0:
            failed=True; failure_date=str(ts.date()); break

        # Entry after all exits/guards.
        if open_trade is None and not stopped and ts in sig_map:
            candidates = sorted(sig_map[ts], key=lambda x: x['strength'], reverse=True)
            r = candidates[0]
            atr = r['atr']
            spread = b['ask_o']-b['bid_o']
            if not math.isfinite(atr) or atr <= 0 or spread > SPREAD_HARD_CAP or spread > 0.18*atr:
                continue
            direction = int(r['direction'])
            entry = b['ask_o'] if direction > 0 else b['bid_o']
            if direction > 0:
                stop = min(r['anchor'], entry-0.80*atr)
                dist = entry-stop
            else:
                stop = max(r['anchor'], entry+0.80*atr)
                dist = stop-entry
            if dist <= 0 or dist > 1.80*atr:
                continue
            lots_raw = risk_usd/(dist*100.0)
            lots = math.floor((lots_raw+1e-12)/LOT_STEP)*LOT_STEP
            lots = min(MAX_LOT, round(lots, 2))
            if lots < LOT_STEP:
                continue
            actual_risk = dist*100.0*lots + COMMISSION_PER_LOT_RT*lots
            if actual_risk > risk_usd*1.40:
                continue
            mid = 0.5*(b['bid_o']+b['ask_o'])
            margin = lots*100.0*mid/LEVERAGE
            if equity <= margin:
                continue
            tp = entry + rr*dist if direction > 0 else entry - rr*dist
            open_trade = {'direction':direction,'entry':entry,'stop':stop,'tp':tp,'lots':lots,'entry_time':ts,'session_end':pd.Timestamp(r['session_end']),'source':r['source']}

    if cur_day is not None:
        daily_pnls.append(day_realized)
        if day_realized < -1e-9: loss_days += 1
        max_daily_loss = min(max_daily_loss, day_realized)

    # Conservative final liquidation if period ends with a trade open.
    if open_trade is not None and len(data):
        b = data.iloc[-1]
        px = b['bid_c'] if open_trade['direction'] > 0 else b['ask_c']
        pnl = trade_pnl(open_trade['direction'], open_trade['entry'], px, open_trade['lots'])
        balance += pnl
        open_trade = None

    market_days = int(data.index.normalize().nunique())
    gross_profit = sum(x for x in daily_pnls if x > 0)
    gross_loss = -sum(x for x in daily_pnls if x < 0)
    pf = gross_profit/gross_loss if gross_loss > 1e-9 else (999.0 if gross_profit > 0 else 0.0)
    return {
        'failed': failed, 'failure_date': failure_date, 'ending_balance': round(balance,3), 'withdrawn': round(withdrawn,3),
        'economic_total': round(balance+withdrawn,3), 'net_economic_profit': round(balance+withdrawn-START_BALANCE,3),
        'market_days': market_days, 'target_days': target_days, 'target_day_rate_pct': round(100*target_days/market_days,3) if market_days else 0,
        'traded_days': len(traded_days), 'trades': trades, 'wins': wins, 'losses': losses,
        'win_rate_pct': round(100*wins/trades,3) if trades else 0, 'loss_days': loss_days,
        'profit_factor_day': round(pf,3), 'max_drawdown_pct': round(100*max_dd,3), 'worst_day_pnl': round(max_daily_loss,3),
    }


def select_system(m1_2025, signals_dict):
    train_start = pd.Timestamp('2025-01-01', tz='UTC'); train_end = pd.Timestamp('2025-08-31 23:59:59', tz='UTC')
    val_start = pd.Timestamp('2025-09-01', tz='UTC'); val_end = pd.Timestamp('2025-12-31 23:59:59', tz='UTC')
    rows = []
    for family, sig in signals_dict.items():
        for rr in [1.5, 2.0]:
            for risk in [5.0, 7.5, 10.0]:
                for dl in [15.0, 20.0]:
                    tr = simulate(m1_2025, sig, rr, risk, dl, train_start, train_end)
                    va = simulate(m1_2025, sig, rr, risk, dl, val_start, val_end)
                    row = {'family':family,'rr':rr,'risk_usd':risk,'daily_loss_cap':dl}
                    for k,v in tr.items(): row['train_'+k]=v
                    for k,v in va.items(): row['val_'+k]=v
                    stable = (not tr['failed']) and (not va['failed']) and tr['trades'] >= 15 and va['trades'] >= 8
                    row['stable'] = stable
                    row['robust_target_rate'] = min(tr['target_day_rate_pct'], va['target_day_rate_pct']) if stable else -1
                    row['avg_target_rate'] = (tr['target_day_rate_pct']+va['target_day_rate_pct'])/2 if stable else -1
                    row['worst_dd'] = max(tr['max_drawdown_pct'], va['max_drawdown_pct'])
                    rows.append(row)
    table = pd.DataFrame(rows)
    stable = table[table['stable']].copy()
    if len(stable)==0:
        pick = table.sort_values(['train_failed','val_failed','robust_target_rate','worst_dd'], ascending=[True,True,False,True]).iloc[0]
    else:
        # Consistency first, then frequency, then drawdown and economic result.
        stable['econ_sum'] = stable['train_net_economic_profit'] + stable['val_net_economic_profit']
        pick = stable.sort_values(['robust_target_rate','avg_target_rate','worst_dd','econ_sum'], ascending=[False,False,True,False]).iloc[0]
    return table, pick


def main(outdir):
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    workdir = outdir / 'tmp'; workdir.mkdir(exist_ok=True)

    m1_2025 = load_year(2025, workdir)
    m1_2025, m5_2025 = add_indicators(m1_2025)
    orb15_25 = generate_orb(m5_2025,15); orb30_25 = generate_orb(m5_2025,30)
    ema_25 = generate_ema_pullback(m5_2025); sweep_25 = generate_sweep(m5_2025)
    signals25 = {
        'ORB15_RETEST':orb15_25, 'ORB30_RETEST':orb30_25, 'EMA_PULLBACK':ema_25, 'SWEEP_REVERSAL':sweep_25,
        'HYBRID_ORB_EMA':combine_signals(orb15_25,ema_25),
        'HYBRID_ALL':combine_signals(orb15_25,ema_25,sweep_25),
    }
    print('SIGNALS 2025', {k:len(v) for k,v in signals25.items()}, flush=True)
    sweep_table, pick = select_system(m1_2025, signals25)
    sweep_table.to_csv(outdir/'2025_development_sweep.csv', index=False)
    winner = {'family':pick['family'],'rr':float(pick['rr']),'risk_usd':float(pick['risk_usd']),'daily_loss_cap':float(pick['daily_loss_cap'])}
    print('FROZEN WINNER', winner, flush=True)

    full25 = simulate(m1_2025, signals25[winner['family']], winner['rr'], winner['risk_usd'], winner['daily_loss_cap'],
                      pd.Timestamp('2025-01-01',tz='UTC'), pd.Timestamp('2025-12-31 23:59:59',tz='UTC'))

    # True out-of-sample period. No tuning below this line.
    m1_2026 = load_year(2026, workdir)
    m1_2026, m5_2026 = add_indicators(m1_2026)
    orb15_26 = generate_orb(m5_2026,15); orb30_26 = generate_orb(m5_2026,30)
    ema_26 = generate_ema_pullback(m5_2026); sweep_26 = generate_sweep(m5_2026)
    signals26 = {
        'ORB15_RETEST':orb15_26, 'ORB30_RETEST':orb30_26, 'EMA_PULLBACK':ema_26, 'SWEEP_REVERSAL':sweep_26,
        'HYBRID_ORB_EMA':combine_signals(orb15_26,ema_26),
        'HYBRID_ALL':combine_signals(orb15_26,ema_26,sweep_26),
    }
    full26 = simulate(m1_2026, signals26[winner['family']], winner['rr'], winner['risk_usd'], winner['daily_loss_cap'],
                      pd.Timestamp('2026-01-01',tz='UTC'), pd.Timestamp('2026-10-29 23:59:59',tz='UTC'))

    report = {
        'system_name':'Fresh XAU Session-Regime Scalp',
        'selection_method':'2025 Jan-Aug development + Sep-Dec holdout; freeze; 2026 Jan-Oct29 out-of-sample',
        'winner':winner,
        'immutable_accounting':{'start_balance':START_BALANCE,'daily_target':DAILY_TARGET,'withdraw_on_target':DAILY_WITHDRAW},
        'execution_assumptions':{'data':'Exness XAUUSD Raw Spread public tick archive aggregated to 1-minute bid/ask OHLC','commission_usd_per_lot_round_trip':COMMISSION_PER_LOT_RT,'leverage':LEVERAGE,'lot_step':LOT_STEP,'max_lot':MAX_LOT,'same_minute_stop_and_tp':'stop assumed first (conservative)','max_hold_minutes':MAX_HOLD_MIN},
        '2025_full':full25,'2026_oos':full26,
        'signal_counts_2025':{k:int(len(v)) for k,v in signals25.items()},
        'signal_counts_2026':{k:int(len(v)) for k,v in signals26.items()},
    }
    with open(outdir/'final_report.json','w') as f: json.dump(report,f,indent=2)
    pd.DataFrame([{'period':'2025_full',**full25},{'period':'2026_oos',**full26}]).to_csv(outdir/'final_results.csv', index=False)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--outdir', required=True); args = ap.parse_args(); main(args.outdir)
