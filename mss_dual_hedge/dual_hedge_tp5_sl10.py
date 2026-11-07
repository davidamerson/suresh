"""Same locked 48H sweep / age2 / strength0.6 MSS signal times as the
2026-11-07 19-grid audit; on the SAME tick open BUY and SELL simultaneously.
Both legs are 0.01 lot, TP = +$5 gold price, SL = -$10 gold price, per leg.
True BUY Ask entry/Bid exit and SELL Bid entry/Ask exit. One PAIR at a time:
do not open another until BOTH original legs have independently hit TP/SL.
NEVER close a surviving leg when the other exits; no Friday, time, annual or
end-of-dataset forced exit. Respect the old <=$0.55 entry spread filter.
Real Bid/Ask already captures spread. Charge $0.07 commission + assumed
$0.15 execution allowance PER LEG, hence $0.44 for both closed legs.
Price levels are $/oz, NOT MT4 broker "pips". No swap/margin/stopout modeling.
"""
import argparse, hashlib, json, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from numba import njit

TP = 5.0
SL = 10.0
COST_PER_LEG = 0.22
MAX_GROUPS = 4000
START_EQUITY = 1000.0

@njit
def replay_ticks(t, bids, asks, book, base, on, live, gid, entry_px, entry_ns,
                 group_entry_ns, group_entry_bid, group_entry_ask, group_exit_ns,
                 leg_exit_ns, leg_exit_px, leg_move, leg_reason,
                 groups_completed, realized, peak_mark, worst_dd, min_equity,
                 prevhour, prevns, last_quote, counters):
    for i in range(len(t)):
        ns = t[i]
        bid = bids[i]
        ask = asks[i]
        if not (np.isfinite(bid) and np.isfinite(ask) and ask >= bid > 0):
            continue
        if prevns[0] > 0 and ns < prevns[0]:
            raise ValueError("Backwards timestamp in quote archive")
        h = ns // 3600000000000
        first_tick = h != prevhour[0]
        idx = h - base
        signal = first_tick and (0 <= idx < len(book)) and book[idx] != 0

        # Exit each leg independently, based on its actual liquidation quote.
        if live[0]:
            q = gid[0]
            for side in range(2):
                if on[side]:
                    direction = 1 if side == 0 else -1
                    exit_px = bid if side == 0 else ask
                    movement = direction * (exit_px - entry_px[side])
                    if movement >= TP or movement <= -SL:
                        on[side] = 0
                        leg_exit_ns[q, side] = ns
                        leg_exit_px[q, side] = exit_px
                        leg_move[q, side] = movement
                        leg_reason[q, side] = 1 if movement >= TP else 2
                        realized[0] += movement - COST_PER_LEG
                        counters[4] += 1
            if not on[0] and not on[1]:
                live[0] = 0
                groups_completed[q] = 1
                group_exit_ns[q] = ns
                counters[1] += 1

        # A future MSS trigger is ignored until BOTH legs of this pair exit.
        if signal:
            if live[0]:
                counters[2] += 1
            elif ((ns // 60000000000) % 60) >= 10:
                counters[5] += 1
            elif ask - bid > 0.55:
                counters[3] += 1
            else:
                q = counters[0]
                if q >= MAX_GROUPS:
                    raise ValueError("Pair ledger capacity exhausted")
                gid[0] = q
                live[0] = 1
                on[0] = 1
                on[1] = 1
                entry_px[0] = ask
                entry_px[1] = bid
                entry_ns[0] = ns
                entry_ns[1] = ns
                group_entry_ns[q] = ns
                group_entry_bid[q] = bid
                group_entry_ask[q] = ask
                counters[0] += 1

        # Pathwise account-equity drawdown includes still-open legs.
        marked = realized[0]
        if live[0]:
            if on[0]:
                marked += (bid - entry_px[0]) - COST_PER_LEG
            if on[1]:
                marked += (entry_px[1] - ask) - COST_PER_LEG
        if marked > peak_mark[0]:
            peak_mark[0] = marked
        dd = peak_mark[0] - marked
        if dd > worst_dd[0]:
            worst_dd[0] = dd
        if START_EQUITY + marked < min_equity[0]:
            min_equity[0] = START_EQUITY + marked
        prevhour[0] = h
        prevns[0] = ns
        last_quote[0] = bid
        last_quote[1] = ask
        counters[6] += 1

def locked_schedule(h1_path):
    # Identical signal construction to 2026-11-07 19-combination source.
    df = pd.read_csv(h1_path)
    df = df[df.complete.astype(str).str.lower().isin(("true", "1"))].reset_index(drop=True)
    t = pd.to_datetime(df.hour_utc, utc=True)
    lo, hi, op, cl = df.bid_low, df.bid_high, df.bid_open, df.bid_close
    atr = (hi-lo).rolling(24, min_periods=24).mean()
    lowsweep = (lo < lo.shift(1).rolling(48, min_periods=48).min()) & (
        (np.minimum(op, cl)-lo)/(hi-lo).clip(lower=.01) > .25)
    hisweep = (hi > hi.shift(1).rolling(48, min_periods=48).max()) & (
        (hi-np.maximum(op, cl))/(hi-lo).clip(lower=.01) > .25)
    buy = lowsweep.shift(2, fill_value=False) & (cl > lo.shift(2)+.6*atr) & (cl > op) & (cl > hi.shift(1))
    sell = hisweep.shift(2, fill_value=False) & (cl < hi.shift(2)-.6*atr) & (cl < op) & (cl < lo.shift(1))
    s = np.where(buy, 1, np.where(sell, -1, 0)).astype(np.int8)
    hours = df.hour_epoch.to_numpy(np.int64)
    base = int(hours[0])
    book = np.zeros(int(hours[-1]-base+5), np.int8)
    for j in np.flatnonzero(s[:-1]):
        ix = j+1
        if hours[ix]-hours[j] != 1:
            continue
        if t.iloc[ix].weekday() == 4 and t.iloc[ix].hour >= 19:
            continue
        if not np.isfinite(atr.iloc[j]):
            continue
        book[hours[ix]-base] = s[j]
    print("H1_READY", len(df), "SCHEDULED", int(np.count_nonzero(book)), flush=True)
    return base, book

def download(url, dest):
    sha = hashlib.sha256()
    n = 0
    with requests.get(url, stream=True, timeout=(30,300)) as response:
        response.raise_for_status()
        with dest.open("wb") as f:
            for b in response.iter_content(1024*1024):
                if b:
                    sha.update(b)
                    n += len(b)
                    f.write(b)
    if not zipfile.is_zipfile(dest):
        raise ValueError("Not a valid ZIP: "+url)
    return sha.hexdigest(), n

def make_state():
    return dict(
        on=np.zeros(2, np.int8), live=np.zeros(1, np.int8),
        gid=np.zeros(1, np.int64), entry_px=np.zeros(2),
        entry_ns=np.zeros(2, np.int64),
        group_entry_ns=np.zeros(MAX_GROUPS, np.int64),
        group_entry_bid=np.zeros(MAX_GROUPS), group_entry_ask=np.zeros(MAX_GROUPS),
        group_exit_ns=np.zeros(MAX_GROUPS, np.int64),
        leg_exit_ns=np.zeros((MAX_GROUPS,2), np.int64),
        leg_exit_px=np.zeros((MAX_GROUPS,2)),
        leg_move=np.zeros((MAX_GROUPS,2)),
        leg_reason=np.zeros((MAX_GROUPS,2), np.int8),
        groups_completed=np.zeros(MAX_GROUPS, np.int8),
        realized=np.zeros(1), peak_mark=np.zeros(1),
        worst_dd=np.zeros(1), min_equity=np.array([START_EQUITY]),
        prevhour=np.array([-1], np.int64), prevns=np.zeros(1, np.int64),
        last_quote=np.zeros(2),
        # started, completed, busy, spread, closed legs, late, valid ticks
        counters=np.zeros(7, np.int64))

def run_chunk(t,bid,ask,book,base,st):
    replay_ticks(t,bid,ask,book,base,*st.values())

def selftest():
    base = 1000
    book = np.zeros(4, np.int8)
    book[1] = 1
    hour = 3600000000000
    start = (base+1)*hour
    arr = np.array([start, start+60000000000, start+120000000000], np.int64)
    # BUY TP then SELL TP. Both should close as an independently winning pair.
    s = make_state()
    run_chunk(arr, np.array([100.,105.2,94.8]), np.array([100.1,105.3,94.9]), book, base, s)
    assert s["counters"][0] == 1 and s["counters"][1] == 1
    assert list(s["leg_reason"][0]) == [1,1], s["leg_reason"][0]
    assert abs(s["realized"][0] - (10.2-0.44)) < .00001
    assert s["live"][0] == 0
    # BUY TP then SELL SL. One positive and one negative result.
    s = make_state()
    run_chunk(arr, np.array([100.,105.2,111.]), np.array([100.1,105.3,111.1]), book, base, s)
    assert s["counters"][0] == 1 and s["counters"][1] == 1
    assert list(s["leg_reason"][0]) == [1,2], s["leg_reason"][0]
    assert s["realized"][0] < 0
    print("SELFTEST_PASSED dual independent tickets, exits and cash reconciliation", flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--h1", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--first", type=int, default=2020)
    parser.add_argument("--last", type=int, default=2026)
    a = parser.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    selftest()
    base,book = locked_schedule(a.h1)
    st=make_state()
    provenance=[]
    for year in range(a.first,a.last+1):
        for month in range(1,11 if year==2026 else 13):
            mm = f"{month:02}"
            url = f"https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip"
            zip_path = out/f"{year}_{mm}.zip"
            digest, size = download(url, zip_path)
            count = 0
            with zipfile.ZipFile(zip_path) as archive:
                bad = archive.testzip()
                if bad:
                    raise ValueError("CRC failure: "+str(bad))
                for member in archive.namelist():
                    if not member.lower().endswith(".csv"):
                        continue
                    with archive.open(member) as reader:
                        for df in pd.read_csv(reader, usecols=["Timestamp","Bid","Ask"], chunksize=500000):
                            timestamps=pd.to_datetime(df.Timestamp,utc=True,errors="coerce")
                            ok=timestamps.notna()&df.Bid.notna()&df.Ask.notna()
                            ns=timestamps[ok].astype("int64").to_numpy(np.int64)
                            if not len(ns):
                                continue
                            if np.any(ns[1:]<ns[:-1]) or (st["prevns"][0] and ns[0]<st["prevns"][0]):
                                raise ValueError("Unordered source quotes "+url)
                            run_chunk(ns,df.Bid[ok].to_numpy(np.float64),
                                df.Ask[ok].to_numpy(np.float64),book,base,st)
                            count += len(ns)
            zip_path.unlink(missing_ok=True)
            provenance.append(dict(year=year, month=month, url=url, sha256=digest,
                                   zip_bytes=size, valid_timestamp_quote_rows=count))
            print("MONTH_DONE",year,mm,"ticks",count,"total",int(st["counters"][6]),
                  "started_pairs",int(st["counters"][0]),
                  "closed_pairs",int(st["counters"][1]), flush=True)

    def iso(ns):
        return str(pd.Timestamp(int(ns), unit="ns", tz="UTC")) if ns else None
    pairs=[]
    legs=[]
    for q in range(int(st["counters"][0])):
        closed=bool(st["groups_completed"][q])
        pair_pnl=0.
        r={}
        for side in range(2):
            movement=float(st["leg_move"][q,side])
            done=st["leg_exit_ns"][q,side]>0
            if done:
                pair_pnl += movement-COST_PER_LEG
            rr=int(st["leg_reason"][q,side])
            r["buy_reason" if side==0 else "sell_reason"] = ("TP" if rr==1 else ("SL" if rr==2 else "OPEN"))
            legs.append(dict(pair_id=q+1,side=("BUY" if side==0 else "SELL"),
                entry_utc=iso(st["group_entry_ns"][q]),exit_utc=iso(st["leg_exit_ns"][q,side]),
                entry_price=float(st["group_entry_ask"][q] if side==0 else st["group_entry_bid"][q]),
                exit_price=float(st["leg_exit_px"][q,side]) if done else None,
                exit_reason=("TP" if rr==1 else ("SL" if rr==2 else "OPEN")),
                quote_movement_usd=movement if done else None,
                roundtrip_cost_usd=COST_PER_LEG,
                net_after_fee_usd=movement-COST_PER_LEG if done else None,
                holding_hours=(float(st["leg_exit_ns"][q,side]-st["group_entry_ns"][q])/3.6e12 if done else None)))
        pairs.append(dict(pair_id=q+1, entry_utc=iso(st["group_entry_ns"][q]),
            exit_utc=iso(st["group_exit_ns"][q]),entry_bid=float(st["group_entry_bid"][q]),
            entry_ask=float(st["group_entry_ask"][q]),entry_spread=float(st["group_entry_ask"][q]-st["group_entry_bid"][q]),
            fully_closed=closed, buy_outcome=r["buy_reason"],sell_outcome=r["sell_reason"],
            realized_so_far_usd=pair_pnl,
            pair_net_if_closed_usd=pair_pnl if closed else None,
            holding_hours_if_closed=(float(st["group_exit_ns"][q]-st["group_entry_ns"][q])/3.6e12 if closed else None)))
    pair_df=pd.DataFrame(pairs)
    leg_df=pd.DataFrame(legs)
    pair_df.to_csv(out/"PAIR_LEDGER_EXACT_BID_ASK.csv",index=False)
    leg_df.to_csv(out/"BOTH_LEGS_EXECUTION_LEDGER.csv",index=False)
    finished=pair_df[pair_df.fully_closed].copy()
    if len(finished):
        finished["exit_year"]=pd.to_datetime(finished.exit_utc,utc=True,format='mixed').dt.year
        yearly=finished.groupby("exit_year").agg(
            completed_pairs=("pair_id","count"),
            net_usd=("pair_net_if_closed_usd","sum"),
            both_tp=("buy_outcome",lambda x:0)).reset_index()
        yearly["both_tp"]=yearly.exit_year.map(
            finished[(finished.buy_outcome=="TP")&(finished.sell_outcome=="TP")].groupby("exit_year").size()).fillna(0).astype(int)
        yearly["mixed_tp_sl"]=yearly.exit_year.map(
            finished[finished.buy_outcome!=finished.sell_outcome].groupby("exit_year").size()).fillna(0).astype(int)
        yearly["both_sl"]=yearly.exit_year.map(
            finished[(finished.buy_outcome=="SL")&(finished.sell_outcome=="SL")].groupby("exit_year").size()).fillna(0).astype(int)
        yearly.to_csv(out/"YEARLY_PAIRS_NET.csv",index=False)
    else:
        yearly=pd.DataFrame()
    closed_net=float(finished.pair_net_if_closed_usd.sum()) if len(finished) else 0.
    # Realized includes any leg closed inside a still-unresolved pair.
    leftover_closed_legs=float(pair_df.loc[~pair_df.fully_closed,"realized_so_far_usd"].sum()) if len(pair_df) else 0.
    if abs(closed_net+leftover_closed_legs-float(st["realized"][0]))>.0001:
        raise AssertionError("Cash/ledger mismatch")
    if len(leg_df):
        if int(leg_df.exit_utc.notna().sum()) != int(st["counters"][4]):
            raise AssertionError("Ticket closure counts differ")
    if int(finished.shape[0])!=int(st["counters"][1]):
        raise AssertionError("Pair count mismatch")
    open_legs=[]
    unrealized=0.
    if st["live"][0]:
        q=int(st["gid"][0])
        for side in range(2):
            if st["on"][side]:
                price=float(st["last_quote"][0] if side==0 else st["last_quote"][1])
                ep=float(st["entry_px"][side])
                raw=(price-ep) if side==0 else (ep-price)
                unrealized+=raw-COST_PER_LEG
                open_legs.append(dict(pair_id=q+1,side=("BUY" if side==0 else "SELL"),
                    entry_utc=iso(st["entry_ns"][side]),entry_price=ep,
                    last_exit_quote=price,mark_to_market_after_cost=raw-COST_PER_LEG))
    by_reason=leg_df.exit_reason.value_counts().to_dict() if len(leg_df) else {}
    both_tp=int(((finished.buy_outcome=="TP")&(finished.sell_outcome=="TP")).sum()) if len(finished) else 0
    both_sl=int(((finished.buy_outcome=="SL")&(finished.sell_outcome=="SL")).sum()) if len(finished) else 0
    mixed=int(((finished.buy_outcome!=finished.sell_outcome)).sum()) if len(finished) else 0
    summary=dict(model="MSS_48H_SIMULTANEOUS_BUY_SELL_TP5_SL10_USD_PER_OUNCE",
        years=f"{a.first}-{a.last}_Oct30",starting_equity_usd=START_EQUITY,
        dataset_ticks=int(st["counters"][6]),source_zip_sha256=provenance,
        scheduled_original_MSS_signals=int(np.count_nonzero(book)),
        started_pairs=int(st["counters"][0]),fully_closed_pairs=int(st["counters"][1]),
        closed_tickets=int(st["counters"][4]),by_leg_exit_reason=by_reason,
        both_tp_pairs=both_tp,mixed_tp_sl_pairs=mixed,both_sl_pairs=both_sl,
        ignored_signals_while_pair_open=int(st["counters"][2]),
        ignored_high_spread_signals=int(st["counters"][3]),
        ignored_late_first_tick=int(st["counters"][5]),
        realized_usd=float(st["realized"][0]),fully_closed_pairs_net_usd=closed_net,
        unfinished_pair_realized_leg_usd=leftover_closed_legs,
        unresolved_legs=open_legs,unrealized_usd_excluding_swap=unrealized,
        end_marked_equity_usd=float(START_EQUITY+st["realized"][0]+unrealized),
        max_pathwise_marked_drawdown_usd=float(st["worst_dd"][0]),
        min_pathwise_equity_usd=float(st["min_equity"][0]),
        tp_price_distance_usd=TP,sl_price_distance_usd=SL,
        lot_per_leg=.01,commission_usd_per_leg=.07,
        extra_execution_assumption_usd_per_leg=.15,spread_in_real_bid_ask=True,
        historical_swap_included=False,margin_stopout_included=False,
        no_friday_time_calendar_or_end_of_test_forced_exit=True)
    (out/"SOURCE_AND_EXACT_RISK_AUDIT.json").write_text(json.dumps(summary,indent=2))
    print("FINAL_DUAL_HEDGE",json.dumps({k:summary[k] for k in [
        "years","dataset_ticks","started_pairs","fully_closed_pairs","closed_tickets",
        "by_leg_exit_reason","both_tp_pairs","mixed_tp_sl_pairs","both_sl_pairs",
        "ignored_signals_while_pair_open","ignored_high_spread_signals",
        "realized_usd","fully_closed_pairs_net_usd","end_marked_equity_usd",
        "max_pathwise_marked_drawdown_usd","min_pathwise_equity_usd","unresolved_legs"]}),flush=True)
    print("YEARLY_RESULTS",yearly.to_json(orient="records"),flush=True)
    print("AUDIT_OK all ticket/pair sums reconciled",flush=True)

if __name__=="__main__":
    main()
