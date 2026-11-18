"""XAUUSD every-H1 independent BUY and SELL hit-rate study, TP/SL 10..100.

For each first valid quote of EVERY observed UTC hour, independently open:
  BUY 0.01 lot with SL=TP=1.00,2.00,...,10.00 XAUUSD price units
  SELL 0.01 lot with SL=TP=1.00,2.00,...,10.00 XAUUSD price units
The 20 virtual orders per hourly entry are separately funded with an
*illustrative* $1,000,000 account EACH. No equity, PnL, margin or exposure
is shared across hours, sides or distances. These independent virtual
price paths are NOT implementable as a single $1M trading account.

No prior-candle color filter, no recovery, no opposite trade at an SL,
no forced time exit, no 04-19 exclusion in the main 24-hour analysis.
The legacy UTC 04-19 subset is also reported, using identical trades.
BUY fill: opening Ask, exiting Bid; SELL open Bid, exit Ask.
At each observed tick, whichever of TP/SL crosses first determines
the outcome; historic quote gaps can produce price slippage. Stop
can occur at opening tick if the spread already exceeds SL distance.
$7 per 1.00 lot commission, 100 oz/lot contract, nominal .01 lot.
Swap/financing, latency, broker order rejection and variable leverage
are excluded. No lookahead: each trade starts on first observed quote
of its own hour, and ends at the first subsequent (or same) barrier tick.

Data: monthly public Exness XAUUSD Raw Spread bid/ask CSV ZIP tick archive,
2020 Jan - 2026 Oct; optional independent 2025 Jan - 2026 Oct replay.
Audit: per-hour exact entry, every trade's timestamp, TP/SL/OPEN outcome,
yearly, time window, UTC-hour stats and ZIP SHA256 records.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from numba import njit

NS_MIN = 60_000_000_000
NS_HOUR = 3_600_000_000_000
CAPITAL_PER_ORDER = 1_000_000.0
LOT = 0.01
OZ_PER_LOT = 100.0
FEE_ROUNDTRIP_PER_LOT = 7.0
N_STRAT = 20
MAX_HOURS = 60000
MAX_ACTIVE = 10000
TP_CODE = 1
SL_CODE = -1
OPEN_CODE = 0
# q=0..9: BUY,  q=10..19: SELL; q%10+1 = diagram pips/10,
# price threshold in USD/oz = q%10+1 (10 diagram pips -> $1).
def setup():
    return dict(
        times=np.zeros(MAX_HOURS, dtype=np.int64),
        entrybid=np.zeros(MAX_HOURS, dtype=np.float64),
        entryask=np.zeros(MAX_HOURS, dtype=np.float64),
        result=np.zeros((N_STRAT,MAX_HOURS), dtype=np.int8),
        exitns=np.zeros((N_STRAT,MAX_HOURS), dtype=np.int64),
        exitprice=np.zeros((N_STRAT,MAX_HOURS), dtype=np.float64),
        pnl=np.zeros((N_STRAT,MAX_HOURS), dtype=np.float64),
        live=np.zeros((N_STRAT,MAX_ACTIVE), dtype=np.int32),
        nlive=np.zeros(N_STRAT, dtype=np.int32),
        nstart=np.zeros(1, dtype=np.int64),
        prev_hour=np.array([-1],dtype=np.int64),
        last_ns=np.zeros(1,dtype=np.int64),
        num_ticks=np.zeros(1,dtype=np.int64),
        hour_late_10min=np.zeros(1,dtype=np.int64),
        opening_spread_exceeds_sl=np.zeros(N_STRAT,dtype=np.int64),
        last_bid_ask=np.zeros(2,dtype=np.float64)
    )

@njit
def _step(ns,bid,ask,times,entrybid,entryask,result,
          exitns,exitprice,pnl,live,nlive,nstart,prev_hour,last_ns,
          num_ticks,hour_late_10min,opening_spread_exceeds_sl,
          last_bid_ask):
    n=len(ns)
    i=0
    while i<n:
        now=ns[i]
        if last_ns[0] and now<last_ns[0]:
            raise ValueError("Source ticks not chronological")
        minute=now//NS_MIN
        hour=now//NS_HOUR
        # First quote of an observed UTC hour starts all 20 independent orders.
        if hour!=prev_hour[0]:
            g=int(nstart[0])
            if g>=MAX_HOURS:
                raise ValueError("Increase MAX_HOURS; too many observed UTC entry hours")
            nstart[0]+=1
            times[g]=now
            entrybid[g]=bid[i]
            entryask[g]=ask[i]
            if (now//NS_MIN)%60>=10:
                hour_late_10min[0]+=1
            for q in range(N_STRAT):
                if nlive[q]>=MAX_ACTIVE:
                    raise ValueError("Increase MAX_ACTIVE for long-lived virtual paths")
                live[q,nlive[q]]=g
                nlive[q]+=1
                if ask[i]-bid[i] >= (q%10+1)-1e-10:
                    opening_spread_exceeds_sl[q]+=1
            prev_hour[0]=hour

        # Build fast exact extrema over one minute or current chunk tail.
        j=i+1
        l_b=bid[i];h_b=bid[i];l_a=ask[i];h_a=ask[i]
        while j<n and ns[j]//NS_MIN==minute:
            b=bid[j];a=ask[j]
            if b<l_b:l_b=b
            if b>h_b:h_b=b
            if a<l_a:l_a=a
            if a>h_a:h_a=a
            j+=1

        # Trade paths do not share risk or funds. A threshold can be
        # ignored for this minute if the extrema prove it was not hit.
        for q in range(N_STRAT):
            is_buy=q<10
            dist=float((q%10)+1)
            k=0
            while k<nlive[q]:
                g=int(live[q,k])
                ep=entryask[g] if is_buy else entrybid[g]
                high_tp=ep+dist
                low_sl=ep-dist
                if is_buy:
                    can_hit=h_b>=high_tp-1e-10 or l_b<=low_sl+1e-10
                else:
                    can_hit=l_a<=low_sl+1e-10 or h_a>=high_tp-1e-10
                if not can_hit:
                    k+=1
                    continue
                # Exact first crossing tick; minute high/low cannot order
                # opposing threshold hits so scan only such candidate minutes.
                event=0
                px=0.0
                t_exit=0
                for t in range(i,j):
                    quote=bid[t] if is_buy else ask[t]
                    if is_buy:
                        if quote>=high_tp-1e-10:
                            event=TP_CODE
                        elif quote<=low_sl+1e-10:
                            event=SL_CODE
                    else:
                        if quote<=low_sl+1e-10:
                            event=TP_CODE
                        elif quote>=high_tp-1e-10:
                            event=SL_CODE
                    if event!=0:
                        px=quote
                        t_exit=ns[t]
                        break
                if event==0:
                    raise ValueError("Minute extrema indicated hit but no tick found")
                result[q,g]=event
                exitns[q,g]=t_exit
                exitprice[q,g]=px
                sgn=1.0 if is_buy else -1.0
                pnl[q,g]=sgn*(px-ep)*OZ_PER_LOT*LOT-FEE_ROUNDTRIP_PER_LOT*LOT
                nlive[q]-=1
                live[q,k]=live[q,nlive[q]]
                # Swapped index: do NOT increment k.
        num_ticks[0]+=j-i
        last_ns[0]=ns[j-1]
        last_bid_ask[0]=bid[j-1]
        last_bid_ask[1]=ask[j-1]
        i=j

def process(ns,bid,ask,state):
    _step(ns,bid,ask,
          state["times"],state["entrybid"],state["entryask"],state["result"],
          state["exitns"],state["exitprice"],state["pnl"],
          state["live"],state["nlive"],state["nstart"],state["prev_hour"],
          state["last_ns"],state["num_ticks"],state["hour_late_10min"],
          state["opening_spread_exceeds_sl"],state["last_bid_ask"])

def check_paths():
    h=NS_HOUR
    mi=NS_MIN
    # Two newly started UTC-hour groups; first group remains open across
    # hour boundary for high TP/SL, but ALL 20 new groups must start.
    s=setup()
    ns=np.array([h, h+mi, h+2*mi, 2*h, 2*h+mi, 2*h+2*mi],np.int64)
    bids=np.array([100.,100.4,101.2,100.,98.8,97.8],np.float64)
    asks=bids+.1
    process(ns,bids,asks,s)
    assert int(s["nstart"][0])==2
    # First hour: 10-pip BUY enters at 100.1 and takes TP at Bid 101.2,
    # 10-pip SELL enters at 100.0 and hits SL at Ask 101.3.
    assert s["result"][0,0]==TP_CODE
    assert s["result"][10,0]==SL_CODE
    assert s["exitns"][0,0]==h+2*mi
    assert s["exitns"][10,0]==h+2*mi
    # At $2 boundary, first hour BUY hits SL at second hour lower Bid,
    # SELL hits TP when Ask <=98.0, which occurs at 97.9.
    assert s["result"][1,0]==SL_CODE
    assert s["result"][11,0]==TP_CODE
    assert s["exitns"][1,0]==2*h+2*mi
    assert s["exitns"][11,0]==2*h+2*mi
    assert int(s["nlive"].sum())>0  # wider TP/SL unresolved.
    # First hour 10 BUY group already closed, second hour has new BUY
    # that reaches SL at 98.8, proving no group blocks later entry.
    assert s["result"][0,1]==SL_CODE
    assert s["exitns"][0,1]==2*h+mi
    assert abs(s["pnl"][0,0]-(1.2-.1-.07))<1e-9
    assert abs(s["pnl"][10,0]-(-1.3-.07))<1e-9
    # Split chunks across hour and minute boundaries must be identical.
    t=setup()
    for a,b in [(0,1),(1,3),(3,4),(4,6)]:
        process(ns[a:b],bids[a:b],asks[a:b],t)
    assert np.array_equal(t["result"][:,:2],s["result"][:,:2])
    assert np.array_equal(t["exitns"][:,:2],s["exitns"][:,:2])
    # Spread > stop triggers *immediate* SL, not a skipped hour.
    u=setup()
    process(np.array([4*h],np.int64),np.array([100.]),np.array([101.5]),u)
    assert u["nstart"][0]==1
    assert u["result"][0,0]==SL_CODE and u["result"][10,0]==SL_CODE
    assert u["opening_spread_exceeds_sl"][0]==1
    assert u["opening_spread_exceeds_sl"][10]==1
    print("SELFTEST_OK 20 independent BUY/SELL orders per H1, exact bid ask first hit, 10-100 pips, month/chunk persistence, no spread filter",flush=True)

def download(url,dst):
    digest=hashlib.sha256()
    size=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with dst.open("wb") as out:
            for part in r.iter_content(1024*1024):
                if part:
                    out.write(part)
                    digest.update(part)
                    size+=len(part)
    if not zipfile.is_zipfile(dst):
        raise ValueError("Invalid source ZIP "+url)
    return digest.hexdigest(),size

def iso_arr(a):
    return pd.to_datetime(a,utc=True,unit="ns",errors="coerce").strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def aggregate(state,output,first,last,provenance):
    out=Path(output)
    n=int(state["nstart"][0])
    assert n>1000
    en=state["times"][:n]
    timestamps=pd.to_datetime(en,utc=True,unit="ns")
    years=timestamps.year.to_numpy(np.int32)
    hours=timestamps.hour.to_numpy(np.int32)
    if np.any(np.diff(en)<=0) or len(np.unique(en//NS_HOUR))!=n:
        raise AssertionError("Expected one unique first quote per UTC hour")
    if int(state["num_ticks"][0])!=sum(p["valid_quotes"] for p in provenance):
        raise AssertionError("Valid tick-count provenance reconciliation failed")
    base=pd.DataFrame({
        "hour_group_id":np.arange(1,n+1,dtype=np.int64),
        "entry_utc":iso_arr(en),
        "entry_year":years,
        "entry_hour_utc":hours,
        "opening_bid":state["entrybid"][:n],
        "opening_ask":state["entryask"][:n],
        "opening_spread_USD_oz":state["entryask"][:n]-state["entrybid"][:n],
    })
    base.to_csv(out/"ALL_H1_ENTRY_FIRST_QUOTES.csv",index=False)

    ledger=[]
    overview=[]
    splits=[]
    yearsummary=[]
    hoursummary=[]
    for q in range(N_STRAT):
        side="BUY" if q<10 else "SELL"
        pips=10*(q%10+1)
        price_delta=float(q%10+1)
        result=state["result"][q,:n]
        pnl=state["pnl"][q,:n]
        exitns=state["exitns"][q,:n]
        ep=state["entryask"][:n] if q<10 else state["entrybid"][:n]
        xp=state["exitprice"][q,:n]
        live=result==0
        hit=(result!=0)
        if np.any((exitns[hit]<en[hit])) or np.any(exitns[live]!=0):
            raise AssertionError("Exit timestamp out of chronological bounds")
        if np.any(result[hit]*pnl[hit]<=0):
            raise AssertionError("TP must be profitable and SL must lose after commission")
        tp_count=int(np.sum(result==1))
        sl_count=int(np.sum(result==-1))
        unresolved=int(np.sum(live))
        if tp_count+sl_count+unresolved!=n:
            raise AssertionError("TP+SL+OPEN accounting mismatch")
        if int(state["nlive"][q])!=unresolved:
            raise AssertionError("Live positions do not match final OPEN records")
        for mask,name in [(np.ones(n,dtype=bool),"ALL_UTC_00_23"),
                          ((hours>=4)&(hours<=19),"LEGACY_UTC_04_19")]:
            r=result[mask]
            pn=pnl[mask]
            t=int(np.sum(r==1));sl=int(np.sum(r==-1));op=int(np.sum(r==0))
            count=int(len(r));closed=t+sl
            splits.append(dict(
                scope=name,side=side,SL_diagram_pips=pips,TP_diagram_pips=pips,
                SL_TP_price_delta_USD_oz=price_delta,
                entries=count,TP_hit=t,SL_hit=sl,unresolved_at_data_end=op,
                TP_pct_of_resolved=100*t/closed if closed else None,
                SL_pct_of_resolved=100*sl/closed if closed else None,
                TP_pct_of_all_entries=100*t/count if count else None,
                SL_pct_of_all_entries=100*sl/count if count else None,
                unresolved_pct_of_all=100*op/count if count else None,
                total_realized_net_USD=float(pn.sum()),
                avg_realized_PnL_per_entry_USD=float(pn.mean()) if count else None
            ))
        for yr in np.unique(years):
            m=(years==yr)
            r=result[m];t=int((r==1).sum());sl=int((r==-1).sum());op=int((r==0).sum())
            yearsummary.append(dict(
                side=side,pips=pips,entry_year=int(yr),entries=int(m.sum()),
                TP_hit=t,SL_hit=sl,open_at_end=op,
                TP_pct_of_resolved=100*t/(t+sl) if t+sl else None,
                SL_pct_of_resolved=100*sl/(t+sl) if t+sl else None,
                realized_net_pnl_usd=float(pnl[m].sum())
            ))
        for hr in range(24):
            m=(hours==hr);r=result[m]
            t=int((r==1).sum());sl=int((r==-1).sum());op=int((r==0).sum())
            hoursummary.append(dict(
                side=side,pips=pips,hour_UTC=hr,entries=int(m.sum()),
                TP_hit=t,SL_hit=sl,open_at_end=op,
                TP_pct_of_resolved=100*t/(t+sl) if t+sl else None,
                SL_pct_of_resolved=100*sl/(t+sl) if t+sl else None,
            ))
        # Mark-to-market is a separate metric for the few unresolved trades;
        # their proceeds do NOT enter realized TP/SL win rates.
        mtm=np.where(live,
              ((state["last_bid_ask"][0]-ep) if q<10 else (ep-state["last_bid_ask"][1]))
              *LOT*OZ_PER_LOT - FEE_ROUNDTRIP_PER_LOT*LOT, np.nan)
        frame=pd.DataFrame({
            "hour_group_id":np.arange(1,n+1,dtype=np.int64),
            "side":side,"SL_pips":pips,"TP_pips":pips,
            "entry_utc":base.entry_utc,"entry_hour_UTC":hours,
            "entry_bid":base.opening_bid,"entry_ask":base.opening_ask,
            "entry_fill_price":ep,"exit_quote_price":np.where(live,np.nan,xp),
            "exit_utc":np.where(live,None,iso_arr(np.maximum(exitns,1))),
            "outcome":np.where(result==1,"TP",np.where(result==-1,"SL","OPEN")),
            "exit_lag_hours":np.where(live,np.nan,(exitns-en)/NS_HOUR),
            "independent_initial_account_USD":CAPITAL_PER_ORDER,
            "lot":LOT,"net_realized_pnl_USD":pnl,
            "unresolved_marked_pnl_USD":mtm,
        })
        ledger.append(frame)
    summary=pd.DataFrame(splits)
    summary.to_csv(out/"TP_SL_PERCENTAGES_24H_AND_04_19.csv",index=False)
    pd.DataFrame(yearsummary).to_csv(out/"YEARLY_TP_SL_HIT_RATES.csv",index=False)
    pd.DataFrame(hoursummary).to_csv(out/"UTC_HOURLY_TP_SL_HIT_RATES.csv",index=False)
    pd.concat(ledger,ignore_index=True).to_csv(out/"EVERY_H1_BUY_SELL_TP_SL_OUTCOME.csv",index=False)
    audit=dict(
        run_years=[first,last],entire_trading_day=True,
        strategy="Separate standalone BUY and SELL at every first tick of each observed UTC hour; 10..100 equal SL TP; no recovery; no prior candle condition",
        capital_per_independent_order_USD=CAPITAL_PER_ORDER,
        single_trade_initial_lot=LOT,
        diagram_pip_in_gold_price_USD_oz=.1,
        assumed_contract_oz_per_lot=OZ_PER_LOT,
        assumed_roundtrip_commission_USD_per_lot=FEE_ROUNDTRIP_PER_LOT,
        buy_enter_ask_exit_bid=True,sell_enter_bid_exit_ask=True,
        resolve_first_tick_touch=True,
        no_entry_filter_due_to_spread_or_first_tick_delay=True,
        no_forced_close_at_data_end=True,
        no_recovery_reversal_doubling_or_simultaneous_account_aggregation=True,
        no_swap_or_slippage_beyond_observed_quotes=True,
        prices_same_quote_may_trigger_initial_SL_if_spread_large=True,
        number_of_eligible_historical_H1_entries=n,
        number_of_virtual_standalone_trades=n*N_STRAT,
        first_observed_entry=str(timestamps[0]),
        last_observed_entry=str(timestamps[-1]),
        first_tick_after_minute_10=int(state["hour_late_10min"][0]),
        source_tick_count=int(state["num_ticks"][0]),
        source_zip_sha256_and_rows=provenance
    )
    (out/"SOURCE_AND_METHOD_AUDIT.json").write_text(json.dumps(audit,indent=2))
    print("FINAL_COUNTS",json.dumps(dict(
         hours=n,raw_ticks=int(state["num_ticks"][0]),
         all_hours_summary=summary[summary.scope=="ALL_UTC_00_23"].to_dict("records"),
         legacy_04_19_summary=summary[summary.scope=="LEGACY_UTC_04_19"].to_dict("records")
         )),flush=True)
    print("AUDIT_PASSED all 20 independent BUY/SELL equal-TP-SL variants hit-rate and chronological checks",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",type=int,default=2020)
    p.add_argument("--last",type=int,default=2026)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    check_paths()
    st=setup()
    sources=[]
    for year in range(args.first,args.last+1):
        months=range(1,11) if year==2026 else range(1,13)
        for month in months:
            mm=f"{month:02}"
            u=f"https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip"
            dest=out/f"archive_{year}_{mm}.zip"
            sha,nbytes=download(u,dest)
            valid=0
            with zipfile.ZipFile(dest) as z:
                corrupt=z.testzip()
                if corrupt:raise ValueError("Bad monthly ZIP CRC "+str(corrupt))
                names=[nm for nm in z.namelist() if nm.lower().endswith(".csv")]
                if not names:raise ValueError("ZIP had no CSV "+u)
                for name in names:
                    with z.open(name) as handle:
                        for df in pd.read_csv(handle, usecols=["Timestamp","Bid","Ask"],chunksize=500000):
                            dt=pd.to_datetime(df["Timestamp"],utc=True,errors="coerce")
                            good=dt.notna()&df["Bid"].notna()&df["Ask"].notna()
                            if not good.any():
                                continue
                            ns=dt[good].astype("int64").to_numpy(np.int64)
                            bid=df.loc[good,"Bid"].to_numpy(np.float64)
                            ask=df.loc[good,"Ask"].to_numpy(np.float64)
                            quote_ok=(bid>0.0)&np.isfinite(bid)&np.isfinite(ask)&(ask>=bid)
                            ns=ns[quote_ok];bid=bid[quote_ok];ask=ask[quote_ok]
                            if not len(ns):continue
                            if np.any(ns[1:]<ns[:-1]) or (
                                st["last_ns"][0]>0 and ns[0]<st["last_ns"][0]):
                                raise ValueError("Ticks out of chronological order in "+u)
                            process(ns,bid,ask,st)
                            valid+=len(ns)
            dest.unlink(missing_ok=True)
            sources.append(dict(year=year,month=month,url=u,sha256=sha,
                                archive_bytes=nbytes,valid_quotes=valid))
            print("MONTH",year,mm,"valid_ticks",valid,
                  "cumulative_ticks",int(st["num_ticks"][0]),
                  "H1_first_tick_entries",int(st["nstart"][0]),
                  "currently_live_orders",int(st["nlive"].sum()),flush=True)
    aggregate(st,out,args.first,args.last,sources)

if __name__=="__main__":
    main()
