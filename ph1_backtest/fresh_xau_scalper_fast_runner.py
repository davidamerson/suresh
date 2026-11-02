import math
import numpy as np
import pandas as pd
import fresh_xau_scalper_research as m

DAY_NS = 86_400_000_000_000
MIN_NS = 60_000_000_000


def fast_simulate(m1, signals, rr, risk_usd, daily_loss_cap, start, end):
    data = m1[(m1.index >= start) & (m1.index <= end)]
    sig = signals[(signals['time'] >= start) & (signals['time'] <= end)].copy() if len(signals) else signals.copy()
    sig_map = {}
    if len(sig):
        for r in sig.to_dict('records'):
            key = int(pd.Timestamp(r['time']).value)
            rec = dict(r)
            rec['session_end_ns'] = int(pd.Timestamp(r['session_end']).value)
            sig_map.setdefault(key, []).append(rec)

    idx_ns = data.index.view('int64')
    bid_o = data['bid_o'].to_numpy(float); bid_h = data['bid_h'].to_numpy(float); bid_l = data['bid_l'].to_numpy(float); bid_c = data['bid_c'].to_numpy(float)
    ask_o = data['ask_o'].to_numpy(float); ask_h = data['ask_h'].to_numpy(float); ask_l = data['ask_l'].to_numpy(float); ask_c = data['ask_c'].to_numpy(float)
    day_keys = idx_ns // DAY_NS

    balance = m.START_BALANCE; withdrawn = 0.0; trade = None
    cur_day = -1; day_realized = 0.0; stopped = False; target_days = 0
    traded_days = set(); wins = 0; losses = 0; trades = 0; loss_days = 0
    daily_pnls = []; max_daily_loss = 0.0; peak_eq = m.START_BALANCE; max_dd = 0.0
    failed = False; failure_date = ''

    for i in range(len(idx_ns)):
        tns = int(idx_ns[i]); dkey = int(day_keys[i])
        if dkey != cur_day:
            if cur_day >= 0:
                daily_pnls.append(day_realized)
                if day_realized < -1e-9: loss_days += 1
                max_daily_loss = min(max_daily_loss, day_realized)
            cur_day = dkey; day_realized = 0.0; stopped = False

        if trade is not None:
            direction = trade['direction']; exit_px = None
            if direction > 0:
                sh = bid_l[i] <= trade['stop']; th = bid_h[i] >= trade['tp']
                if sh: exit_px = trade['stop']
                elif th: exit_px = trade['tp']
            else:
                sh = ask_h[i] >= trade['stop']; th = ask_l[i] <= trade['tp']
                if sh: exit_px = trade['stop']
                elif th: exit_px = trade['tp']
            if exit_px is not None:
                pnl = m.trade_pnl(direction, trade['entry'], exit_px, trade['lots'])
                balance += pnl; day_realized += pnl; trades += 1; traded_days.add(dkey)
                if pnl > 0: wins += 1
                else: losses += 1
                trade = None
            else:
                close_px = bid_c[i] if direction > 0 else ask_c[i]
                floating = m.trade_pnl(direction, trade['entry'], close_px, trade['lots'])
                if day_realized + floating >= m.DAILY_TARGET:
                    balance += floating; day_realized += floating; trades += 1; traded_days.add(dkey)
                    if floating > 0: wins += 1
                    else: losses += 1
                    trade = None; withdrawn += m.DAILY_WITHDRAW; balance -= m.DAILY_WITHDRAW; target_days += 1; stopped = True
                elif day_realized + floating <= -daily_loss_cap or tns >= trade['session_end_ns'] or (tns-trade['entry_ns'])/MIN_NS >= m.MAX_HOLD_MIN:
                    balance += floating; day_realized += floating; trades += 1; traded_days.add(dkey)
                    if floating > 0: wins += 1
                    else: losses += 1
                    trade = None
                    if day_realized <= -daily_loss_cap: stopped = True

        if trade is None and not stopped and day_realized >= m.DAILY_TARGET:
            withdrawn += m.DAILY_WITHDRAW; balance -= m.DAILY_WITHDRAW; target_days += 1; stopped = True

        equity = balance
        if trade is not None:
            px = bid_c[i] if trade['direction'] > 0 else ask_c[i]
            equity += m.trade_pnl(trade['direction'], trade['entry'], px, trade['lots'])
        if equity > peak_eq: peak_eq = equity
        if peak_eq > 0:
            dd = (peak_eq-equity)/peak_eq
            if dd > max_dd: max_dd = dd
        if equity <= 0 or balance <= 0:
            failed = True
            failure_date = str(pd.Timestamp(tns, unit='ns', tz='UTC').date())
            break

        if trade is None and not stopped and tns in sig_map:
            r = max(sig_map[tns], key=lambda x: x['strength'])
            atr = float(r['atr']); spread = ask_o[i]-bid_o[i]
            if not math.isfinite(atr) or atr <= 0 or spread > m.SPREAD_HARD_CAP or spread > 0.18*atr:
                continue
            direction = int(r['direction']); entry = ask_o[i] if direction > 0 else bid_o[i]
            if direction > 0:
                stop = min(float(r['anchor']), entry-0.80*atr); dist = entry-stop
            else:
                stop = max(float(r['anchor']), entry+0.80*atr); dist = stop-entry
            if dist <= 0 or dist > 1.80*atr:
                continue
            lots_raw = risk_usd/(dist*100.0)
            lots = math.floor((lots_raw+1e-12)/m.LOT_STEP)*m.LOT_STEP
            lots = min(m.MAX_LOT, round(lots,2))
            if lots < m.LOT_STEP: continue
            actual_risk = dist*100.0*lots + m.COMMISSION_PER_LOT_RT*lots
            if actual_risk > risk_usd*1.40: continue
            mid = 0.5*(bid_o[i]+ask_o[i]); margin = lots*100.0*mid/m.LEVERAGE
            if equity <= margin: continue
            tp = entry + rr*dist if direction > 0 else entry - rr*dist
            trade = {'direction':direction,'entry':entry,'stop':stop,'tp':tp,'lots':lots,'entry_ns':tns,'session_end_ns':int(r['session_end_ns'])}

    if cur_day >= 0:
        daily_pnls.append(day_realized)
        if day_realized < -1e-9: loss_days += 1
        max_daily_loss = min(max_daily_loss, day_realized)

    if trade is not None and len(idx_ns):
        i = len(idx_ns)-1; px = bid_c[i] if trade['direction'] > 0 else ask_c[i]
        pnl = m.trade_pnl(trade['direction'], trade['entry'], px, trade['lots']); balance += pnl

    market_days = int(np.unique(day_keys).size)
    gp = sum(x for x in daily_pnls if x > 0); gl = -sum(x for x in daily_pnls if x < 0)
    pf = gp/gl if gl > 1e-9 else (999.0 if gp > 0 else 0.0)
    return {
        'failed':failed,'failure_date':failure_date,'ending_balance':round(balance,3),'withdrawn':round(withdrawn,3),
        'economic_total':round(balance+withdrawn,3),'net_economic_profit':round(balance+withdrawn-m.START_BALANCE,3),
        'market_days':market_days,'target_days':target_days,'target_day_rate_pct':round(100*target_days/market_days,3) if market_days else 0,
        'traded_days':len(traded_days),'trades':trades,'wins':wins,'losses':losses,'win_rate_pct':round(100*wins/trades,3) if trades else 0,
        'loss_days':loss_days,'profit_factor_day':round(pf,3),'max_drawdown_pct':round(100*max_dd,3),'worst_day_pnl':round(max_daily_loss,3)
    }


m.simulate = fast_simulate

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--outdir', required=True); args = ap.parse_args(); m.main(args.outdir)
