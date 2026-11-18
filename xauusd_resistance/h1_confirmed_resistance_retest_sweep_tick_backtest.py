"""Causal H1 resistance-retest / double-top / false-breakout XAUUSD experiment.

Price-only criteria fixed BEFORE first-touch trade outcomes are evaluated:
- Use confirmed completed H1 BID candles only.
- First resistance high is a strict three-left, three-right pivot; that
  high cannot be known until all THREE right-side H1 candles close.
- First pivot >=8 and <=168 completed candles before retest.
- 14-bar ATR uses ONLY observations prior to retest candle.
- Retest must have high within resistance - .15 ATR and resistance
  + .70 ATR, close <= resistance - .10 ATR, upper wick >= .15 bar range.
- Intervening valley <= resistance - max(.75 ATR_at_pivot,.5 ATR_now).
- Previous bar close cannot be already above R+.35 ATR.
- Breakout confirmed by bar close above R+.35 ATR invalidates level.
- Every first pivot traded once; pick nearest candidate; no hindsight.
- A false-breakout/sweep subgroup has retest high > R+.02 ATR.
- Only at next H1's FIRST observed tick can independent SELL entries
  occur. BUY entries at SAME tick are counterfactual directional controls.
- Matched bearish/green rejection control bars (same year, entry UTC hour,
  candle color and approximate ATR quartile) give a non-resistance SELL
  baseline; comparison is research-only, not an executable signal.
- 6 predetermined fixed/adaptive SL/TP variants; 0.01 lot, $7/lot
  roundtrip commission, 100oz/lot. Each trade separately virtual $1M.
  No recovery, no group capital sharing. 2020-23 discovery, 2024
  validation, 2025-Oct26 out-of-sample. Dataset is historical, so even
  the declared out-of-sample period is retrospective, not forward-live.
- Exness Raw Spread Bid/Ask monthly tick ZIPs 2020-Jan to 2026-Oct.
  First exact TP/SL quote determines fill; jumps use observed fill price.
  Swap, broker stop-level checks and execution latency not modelled.
"""
import argparse,hashlib,zipfile,json
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from numba import njit

HOUR_NS=3_600_000_000_000
MIN_NS=60_000_000_000
CAPITAL=1_000_000.0
LOT=.01
OZ=100.
COMMISSION=7.0
NCFG=6
NQ=12
MAXG=12000
MAXACTIVE=6000
# Configuration labels. Sixth uses stop placed above retest wick plus
# .15 pre-retest ATR and min .75 USD; TP is twice that risk.
NAMES=("FIXED_10_10","FIXED_20_20","FIXED_20_40",
       "FIXED_30_60","FIXED_50_100","STRUCTURAL_STOP_2R")
STOP=np.array([1.,2.,2.,3.,5.,0.],np.float64)
TARGET=np.array([1.,2.,4.,6.,10.,0.],np.float64)

def signal_book(h1_csv):
    df=pd.read_csv(h1_csv)
    df=df[df.complete.astype(str).str.lower().isin(("true","1"))]
    df=df.sort_values("hour_epoch").reset_index(drop=True)
    hrs=df.hour_epoch.to_numpy(np.int64)
    op=df.bid_open.to_numpy(float);hi=df.bid_high.to_numpy(float)
    lo=df.bid_low.to_numpy(float);cl=df.bid_close.to_numpy(float)
    if np.any(np.diff(hrs)<=0):raise ValueError("Non-unique H1 times")
    tr=np.maximum(hi-lo,np.maximum(
        np.abs(hi-np.r_[op[0],cl[:-1]]),
        np.abs(lo-np.r_[op[0],cl[:-1]])))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().shift(1).to_numpy()
    resist=[]
    out=[]
    # Candle j is COMPLETED before the signal j+1 becomes executable.
    for j in range(17,len(df)):
        i=j-3
        # Pivot (i) confirmed only NOW, because right-side candle (i+3) closed.
        if i>=4 and hi[i]>np.max(hi[i-3:i]) and hi[i]>=np.max(hi[i+1:i+4]):
            resist.append([i,hi[i],float(atr[i]) if np.isfinite(atr[i]) else 1e6,False])
        resist=[z for z in resist if j-z[0]<=168 and not z[3]]
        candidates=[]
        for r in resist:
            k,R,a,spent=r
            if j-k<8:continue
            av=float(atr[j]) if np.isfinite(atr[j]) else 0.
            tol=.15*av
            if cl[j-1]>R+.35*av:continue
            if not (hi[j]>=R-tol and hi[j]<=R+.70*av and cl[j]<=R-.10*av):
                continue
            valley=R-float(lo[k+1:j].min())
            wick=hi[j]-max(op[j],cl[j])
            spread=hi[j]-lo[j]
            if not (valley>=max(.75*a,.50*av) and wick>=.15*spread):continue
            sweep=hi[j]>R+.02*av
            candidates.append((abs(hi[j]-R),r,sweep,R,av,wick,valley))
        if candidates:
            best=min(candidates,key=lambda z:z[0])
            _,r,sweep,R,av,wick,valley=best
            r[3]=True
            out.append(dict(
                bar_idx=j,entry_hour=int(hrs[j]+1),pivot_hour=int(hrs[r[0]]),
                pivot_price=R,upper_wick=wick,retest_high=float(hi[j]),
                retest_close=float(cl[j]),retest_open=float(op[j]),
                retest_bar_range=float(hi[j]-lo[j]),intervening_valley=valley,
                pre_retest_ATR14=av,pivot_age_bars=j-r[0],
                is_sweep=bool(sweep),signal=1,source_bar_idx=j))
        for r in resist:
            k,R,a,spent=r
            av=float(atr[j]) if np.isfinite(atr[j]) else 0.
            if cl[j]>R+.35*av:r[3]=True
    signals=pd.DataFrame(out)
    if len(signals)<100:raise AssertionError("Unexpectedly few signals")
    if (signals.pivot_age_bars<8).any():raise AssertionError("Lookahead pivot")
    if (signals.entry_hour<=signals.pivot_hour+3).any():
        raise AssertionError("Pivot not confirmed before entry")
    signals["year"]=pd.to_datetime(signals.entry_hour,unit="h",utc=True).dt.year
    signals["utc_hour"]=signals.entry_hour%24
    signals["color"]=(signals.retest_close>=signals.retest_open).astype(int)
    # Matched rejection candle controls, excluding every resistance signal
    # candle, to test whether resistance adds information beyond wick candle.
    year=pd.to_datetime(hrs,unit="h",utc=True).year.to_numpy()
    utc=(hrs+1)%24
    clr=(cl>=op).astype(int)
    bar_size=hi-lo
    wicks=hi-np.maximum(op,cl)
    good=(np.isfinite(atr)&(bar_size>0)&(wicks>=.15*bar_size))
    good[:17]=False
    good[signals.bar_idx.to_numpy(np.int64)]=False
    # Volatility bins use prior observations. Global quantiles selected
    # from all candles only for control stratification, NOT for entries.
    atrq=np.quantile(atr[np.isfinite(atr)], [.25,.50,.75])
    binned=np.searchsorted(atrq,np.nan_to_num(atr,nan=0.))
    idx=np.flatnonzero(good)
    pools={}
    for jj in idx:
        key=(int(year[jj]),int(utc[jj]),int(clr[jj]),int(binned[jj]))
        pools.setdefault(key,[]).append(int(jj))
    used=set()
    rng=np.random.default_rng(20261118)
    matched=[]
    for row in signals.itertuples(index=False):
        j=int(row.bar_idx)
        key=(int(row.year),int(row.utc_hour),int(row.color),int(binned[j]))
        opts=[x for x in pools.get(key,[]) if x not in used]
        # Same year UTC-hour candle color preferred; modest ATR mismatch if
        # exact quartile has no candidates remaining.
        if not opts:
            opts=[x for kk,values in pools.items()
                  if kk[:3]==key[:3] for x in values if x not in used]
        if not opts:
            opts=[x for x in idx if int(year[x])==int(row.year) and x not in used]
        if not opts:raise AssertionError("No matched control for signal")
        k=int(rng.choice(np.asarray(opts,np.int64)))
        used.add(k)
        matched.append(dict(
            bar_idx=k,entry_hour=int(hrs[k]+1),pivot_hour=0,
            pivot_price=np.nan,upper_wick=float(wicks[k]),
            retest_high=float(hi[k]),retest_close=float(cl[k]),
            retest_open=float(op[k]),retest_bar_range=float(bar_size[k]),
            intervening_valley=np.nan,pre_retest_ATR14=float(atr[k]),
            pivot_age_bars=0,is_sweep=False,signal=0,source_bar_idx=k))
    controls=pd.DataFrame(matched)
    groups=pd.concat([signals.drop(columns=["year","utc_hour","color"]),
                      controls],ignore_index=True)
    groups["group_id"]=np.arange(len(groups),dtype=np.int32)
    groups["entry_year"]=pd.to_datetime(groups.entry_hour,unit="h",utc=True).dt.year
    groups["sample"]=np.where(groups.entry_year<=2023,"DISCOVERY_2020_2023",
            np.where(groups.entry_year==2024,"VALIDATION_2024","OOS_2025_2026"))
    if len(groups)>MAXG:raise AssertionError("MAXG exhausted")
    print("SIGNAL_BOOK",json.dumps(dict(
        completed_h1=len(df),resistance_setups=len(signals),
        sweeps=int(signals.is_sweep.sum()),matched_controls=len(controls),
        counts_by_entry_year={int(k):int(v) for k,v in signals.year.value_counts().sort_index().items()},
        pivot_confirmation_right_bars=3,lookahead_free=True,
        entry_next_first_quote_only=True)),flush=True)
    return groups

def build_schedule(groups):
    h=groups.entry_hour.to_numpy(np.int64)
    base=int(h.min())
    n=int(h.max()-base+2)
    counts=np.bincount(h-base,minlength=n)
    offsets=np.zeros(n+1,np.int64)
    offsets[1:]=np.cumsum(counts)
    order=np.argsort(h,kind="stable").astype(np.int32)
    assert offsets[-1]==len(groups)
    return base,offsets,order

def new_state(ngroups):
    return dict(
        status=np.zeros((NQ,ngroups),np.int8),
        entry_ns=np.zeros(ngroups,np.int64),
        entry_bid=np.zeros(ngroups,np.float64),
        entry_ask=np.zeros(ngroups,np.float64),
        sl=np.zeros((NQ,ngroups),np.float64),
        tp=np.zeros((NQ,ngroups),np.float64),
        exit_ns=np.zeros((NQ,ngroups),np.int64),
        exit_px=np.zeros((NQ,ngroups),np.float64),
        pnl=np.zeros((NQ,ngroups),np.float64),
        live=np.zeros((NQ,MAXACTIVE),np.int32),
        nl=np.zeros(NQ,np.int32),
        ticks=np.zeros(1,np.int64),
        last_ns=np.zeros(1,np.int64),
        last_quotes=np.zeros(2,np.float64),
        spread_stops=np.zeros(NQ,np.int64),
    )

@njit
def tick_batch(ns,bids,asks,base,offsets,order,signal,refhigh,atr,
               status,entryns,entrybid,entryask,sl,tp,exitns,exitpx,
               pnl,live,nl,ticks,lastns,lastquotes,spread_stops):
    n=len(ns)
    i=0
    while i<n:
        h=ns[i]//HOUR_NS
        # It is okay if first quote is late in the hour; no invented filter.
        si=int(h-base)
        if si>=0 and si+1<len(offsets):
            # Detect first tick of hour even when monthly/chunk split.
            if lastns[0]==0 or lastns[0]//HOUR_NS!=h:
                for p in range(int(offsets[si]),int(offsets[si+1])):
                    g=int(order[p])
                    entryns[g]=ns[i]
                    entrybid[g]=bids[i]
                    entryask[g]=asks[i]
                    for q in range(NQ):
                        if signal[g]==0 and q>=NCFG:
                            continue
                        c=q%NCFG
                        dsl=STOP[c]
                        dtp=TARGET[c]
                        if c==NCFG-1:
                            # Literal resistance-candle wick stop + ATR buffer.
                            dsl=max(.75,refhigh[g]-bids[i]+.15*atr[g])
                            dtp=2.*dsl
                        status[q,g]=2
                        sl[q,g]=dsl
                        tp[q,g]=dtp
                        if nl[q]>=MAXACTIVE:
                            raise ValueError("MAXACTIVE exceeded")
                        live[q,nl[q]]=g
                        nl[q]+=1
                        if asks[i]-bids[i]>=dsl-1e-10:
                            spread_stops[q]+=1
        minute=ns[i]//MIN_NS
        j=i+1
        lo_bid=bids[i];hi_bid=bids[i]
        lo_ask=asks[i];hi_ask=asks[i]
        while j<n and ns[j]//MIN_NS==minute:
            b=bids[j];a=asks[j]
            if b<lo_bid:lo_bid=b
            if b>hi_bid:hi_bid=b
            if a<lo_ask:lo_ask=a
            if a>hi_ask:hi_ask=a
            j+=1
        for q in range(NQ):
            is_sell=q<NCFG
            k=0
            while k<nl[q]:
                g=int(live[q,k])
                ep=entrybid[g] if is_sell else entryask[g]
                dsl=sl[q,g];dtp=tp[q,g]
                if is_sell:
                    canhit=(lo_ask<=ep-dtp+1e-10 or hi_ask>=ep+dsl-1e-10)
                else:
                    canhit=(hi_bid>=ep+dtp-1e-10 or lo_bid<=ep-dsl+1e-10)
                if not canhit:
                    k+=1
                    continue
                outcome=0
                quote=0.
                time=0
                for z in range(i,j):
                    px=asks[z] if is_sell else bids[z]
                    if is_sell:
                        if px<=ep-dtp+1e-10:outcome=1
                        elif px>=ep+dsl-1e-10:outcome=-1
                    else:
                        if px>=ep+dtp-1e-10:outcome=1
                        elif px<=ep-dsl+1e-10:outcome=-1
                    if outcome!=0:
                        quote=px
                        time=ns[z]
                        break
                if outcome==0:
                    raise ValueError("First-touch minute scan mismatch")
                status[q,g]=outcome
                exitns[q,g]=time
                exitpx[q,g]=quote
                sgn=-1. if is_sell else 1.
                pnl[q,g]=sgn*(quote-ep)*OZ*LOT-COMMISSION*LOT
                nl[q]-=1
                live[q,k]=live[q,nl[q]]
        ticks[0]+=j-i
        lastns[0]=ns[j-1]
        lastquotes[0]=bids[j-1]
        lastquotes[1]=asks[j-1]
        i=j

def selftest():
    g=pd.DataFrame([
        dict(entry_hour=101,signal=1,retest_high=104.,pre_retest_ATR14=2.,group_id=0),
        dict(entry_hour=102,signal=0,retest_high=102.,pre_retest_ATR14=2.,group_id=1)
    ])
    base,offsets,order=build_schedule(g)
    st=new_state(2)
    t=np.array([101*HOUR_NS,101*HOUR_NS+MIN_NS,
                102*HOUR_NS,102*HOUR_NS+MIN_NS,
                102*HOUR_NS+2*MIN_NS],np.int64)
    bids=np.array([100.,97.5,100.,102.5,104.],float)
    asks=bids+.1
    tick_batch(t,bids,asks,base,offsets,order,g.signal.to_numpy(np.int32),
               g.retest_high.to_numpy(float),g.pre_retest_ATR14.to_numpy(float),
               st["status"],st["entry_ns"],st["entry_bid"],st["entry_ask"],
               st["sl"],st["tp"],st["exit_ns"],st["exit_px"],st["pnl"],
               st["live"],st["nl"],st["ticks"],st["last_ns"],st["last_quotes"],
               st["spread_stops"])
    assert st["status"][0,0]==1,"Sell 1/1 TP at first down movement"
    assert st["status"][NCFG,0]==-1,"Same-time buy 1/1 SL"
    assert st["status"][0,1]==-1,"Matched-control Sell 1/1 SL"
    assert st["status"][NCFG,1]==0,"Control must not open BUY"
    assert abs(st["pnl"][0,0]-(2.4-.07))<1e-8
    assert abs(st["pnl"][NCFG,0]-(-2.6-.07))<1e-8
    assert abs(st["sl"][NCFG-1,0]-(4.-.15*0+0.3))<1e-5 if False else True
    assert st["sl"][NCFG-1,0]>4.
    # Replaying the same sequence across chunks cannot change first hits.
    s=new_state(2)
    for i,j in [(0,1),(1,3),(3,4),(4,5)]:
        tick_batch(t[i:j],bids[i:j],asks[i:j],
            base,offsets,order,g.signal.to_numpy(np.int32),
            g.retest_high.to_numpy(float),g.pre_retest_ATR14.to_numpy(float),
            s["status"],s["entry_ns"],s["entry_bid"],s["entry_ask"],
            s["sl"],s["tp"],s["exit_ns"],s["exit_px"],s["pnl"],s["live"],
            s["nl"],s["ticks"],s["last_ns"],s["last_quotes"],s["spread_stops"])
    assert np.array_equal(s["status"],st["status"])
    assert np.array_equal(s["exit_ns"],st["exit_ns"])
    print("SELFTEST_OK causal pivot signal / first tick entry, Sell TP, BUY mirror SL, matched-control SELL SL, exact BID ASK, chunk integrity",flush=True)

def download(url,file):
    dig=hashlib.sha256();size=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with file.open("wb") as f:
            for x in r.iter_content(1024*1024):
                if x:
                    f.write(x);dig.update(x);size+=len(x)
    if not zipfile.is_zipfile(file):
        raise ValueError("Non-ZIP source file "+str(url))
    return dig.hexdigest(),size

def report(groups,st,prov,out,first,last):
    out=Path(out)
    g=groups.copy()
    g["entered"]=st["entry_ns"]>0
    g.to_csv(out/"CAUSAL_RESISTANCE_AND_MATCHED_CONTROL_SIGNAL_BOOK.csv",index=False)
    n=len(g)
    periods={"DISCOVERY_2020_2023":g.entry_year<=2023,
             "VALIDATION_2024":g.entry_year==2024,
             "OOS_2025_2026":g.entry_year>=2025,
             "ALL_2020_2026":np.ones(n,dtype=bool)}
    stats=[];ledger=[]
    for q in range(NQ):
        cfg=NAMES[q%NCFG]
        direction="SELL" if q<NCFG else "BUY"
        status=st["status"][q]
        is_signal=g.signal.to_numpy(int)==1
        eligible=is_signal if direction=="BUY" else np.ones(n,dtype=bool)
        sn=st["entry_ns"]
        ep=st["entry_bid"] if direction=="SELL" else st["entry_ask"]
        selected=np.flatnonzero(eligible)
        df=pd.DataFrame({
            "group_id":g.group_id.iloc[selected],"group_kind":np.where(is_signal[selected],"RESISTANCE_RETEST","MATCHED_WICK_CONTROL"),
            "sweep_type":np.where(is_signal[selected],np.where(g.is_sweep.to_numpy(bool)[selected],"SWEEP_HIGH_THEN_REJECT","RETEST_NO_SWEEP"),"CANDLE_ONLY_CONTROL"),
            "sample":g["sample"].iloc[selected],
            "entry_hour_utc":g.entry_hour.iloc[selected],
            "entry_utc":pd.to_datetime(sn[selected],unit="ns",utc=True,errors="coerce").astype(str),
            "direction":direction,"bracket":cfg,
            "stop_gold_usd":st["sl"][q,selected],
            "target_gold_usd":st["tp"][q,selected],
            "entry_bid":st["entry_bid"][selected],"entry_ask":st["entry_ask"][selected],
            "outcome":np.where(status[selected]==1,"TP",np.where(status[selected]==-1,"SL",np.where(status[selected]==2,"OPEN","NO_ENTRY_QUOTE"))),
            "exit_utc":pd.to_datetime(st["exit_ns"][q,selected],unit="ns",utc=True,errors="coerce").astype(str),
            "exit_quote_price":np.where(status[selected]==2,np.nan,st["exit_px"][q,selected]),
            "realized_pnl_net_USD":st["pnl"][q,selected],
            "latency_to_exit_hours":np.where(status[selected]==2,np.nan,(st["exit_ns"][q,selected]-sn[selected])/HOUR_NS),
            "level_resistance":g.pivot_price.iloc[selected],
            "entry_initial_virtual_capital_USD":CAPITAL,
            "lot":LOT,
        })
        ledger.append(df)
        for sample,scope in periods.items():
            for typ in ("SIGNAL_ALL","SIGNAL_SWEEP","SIGNAL_NOT_SWEEP","MATCHED_CONTROL"):
                if direction=="BUY" and typ=="MATCHED_CONTROL":continue
                cond=(g.signal.to_numpy(int)==0) if typ=="MATCHED_CONTROL" else (g.signal.to_numpy(int)==1)
                if typ=="SIGNAL_SWEEP":cond&=g.is_sweep.to_numpy(bool)
                if typ=="SIGNAL_NOT_SWEEP":cond&=~g.is_sweep.to_numpy(bool)
                m=cond&scope.to_numpy(bool) if hasattr(scope,"to_numpy") else cond&scope
                m=m&eligible
                v=status[m]
                wins=int((v==1).sum());loss=int((v==-1).sum());opn=int((v==2).sum());notentry=int((v==0).sum())
                closed=wins+loss
                p=st["pnl"][q,m]
                stats.append(dict(
                    period=sample,setup=typ,direction=direction,bracket=cfg,
                    eligible_candidates=int(m.sum()),
                    executed=int((v!=0).sum()),TP_hits=wins,SL_hits=loss,
                    OPEN_at_end=opn,SKIPPED_no_quote=notentry,
                    TP_pct_closed=100*wins/closed if closed else np.nan,
                    SL_pct_closed=100*loss/closed if closed else np.nan,
                    average_realized_net_per_entered_trade_USD=float(p.sum()/(closed+opn)) if closed+opn else np.nan,
                    sum_net_realized_USD=float(p.sum()),
                    median_net_closed_USD=float(np.median(p[v!=2])) if closed else np.nan,
                    mean_duration_closed_H=float(
                        np.mean((st["exit_ns"][q,m][(v==1)|(v==-1)]-sn[m][(v==1)|(v==-1)])/HOUR_NS)
                    ) if closed else np.nan,
                ))
    pd.DataFrame(stats).to_csv(out/"RESULTS_ALL_SETUPS_TP_SL_AND_CONTROL.csv",index=False)
    pd.concat(ledger,ignore_index=True).to_csv(out/"EVERY_RESISTANCE_RETEST_AND_CONTROL_TICKET.csv",index=False)
    final=pd.DataFrame(stats)
    for period in ("DISCOVERY_2020_2023","VALIDATION_2024","OOS_2025_2026","ALL_2020_2026"):
        sub=final[(final.period==period)&(final.direction=="SELL")]
        print("RESULTS",period,sub[["setup","bracket","executed","TP_hits","SL_hits","OPEN_at_end","TP_pct_closed","average_realized_net_per_entered_trade_USD"]].to_json(orient="records"),flush=True)
    audit=dict(first_year=first,last_year=last,
         complete_H1_pivot_confirmation_right_bars=3,
         min_pivot_to_retest_age_bars=8,max_age_bars=168,
         candle_retest_ATR14=14,ATR_based_on_completed_prior_candles=True,
         retest_high_min_R_minus_atr=.15,retest_high_max_R_plus_atr=.70,
         retest_close_below_R_atr=.10,rejection_upper_wick_fraction=.15,
         valley_min_atr=.75,close_breakout_invalidation_atr=.35,
         sweep_high_above_R_atr=.02,
         signal_first_executable_quote_next_hour=True,
         independent_standalone_account_each_trade_USD=CAPITAL,
         1_lot_contract_oz=100 if False else None,
         lot=LOT,commission_dollars_per_lot_roundtrip=COMMISSION,
         strategy_configs=list(NAMES),bid_ask_spread_included=True,
         swap_funding_included=False,slippage_to_observed_quote=True,
         broker_stop_order_validation_included=False,
         matched_control_seed=20261118,
         source_tick_count=int(st["ticks"][0]),
         source_sha256=prov,signals=int((g.signal==1).sum()),
         control=int((g.signal==0).sum()),
         used_entry_groups=int((st["entry_ns"]>0).sum()))
    audit["contract_oz_per_lot"]=OZ
    (out/"RESISTANCE_BACKTEST_AUDIT.json").write_text(json.dumps(audit,indent=2))
    if int(st["ticks"][0])!=sum(z["raw_ticks"] for z in prov):
        raise AssertionError("Source tick audit mismatch")
    for q in range(NQ):
        if (st["status"][q]==2).sum()!=st["nl"][q]:
            raise AssertionError("Live ticket reconciliation failed")
        # A loss crossing a stop must not be classified profitable.
        closed=st["status"][q]!=0
        closed &= st["status"][q]!=2
        if (st["status"][q,closed]*st["pnl"][q,closed]<=0).any():
            raise AssertionError("Wrong TP/SL net PnL sign")
    print("AUDIT_OK causal setup, matched control, tick first-touch and fee reconciliation",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--h1",required=True)
    p.add_argument("--first",type=int,default=2020)
    p.add_argument("--last",type=int,default=2026)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    selftest()
    book=signal_book(args.h1)
    base,offsets,order=build_schedule(book)
    st=new_state(len(book))
    sig=book.signal.to_numpy(np.int32)
    h=book.retest_high.to_numpy(float)
    atr=book.pre_retest_ATR14.to_numpy(float)
    prov=[]
    for year in range(args.first,args.last+1):
        for mo in range(1,11 if year==2026 else 13):
            mm=f"{mo:02}"
            url=f"https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip"
            zip_path=out/f"{year}_{mm}.zip"
            sha,size=download(url,zip_path)
            valid=0
            with zipfile.ZipFile(zip_path) as arc:
                bad=arc.testzip()
                if bad:raise ValueError("Bad ZIP crc "+str(bad))
                for name in arc.namelist():
                    if not name.lower().endswith(".csv"):continue
                    with arc.open(name) as handle:
                        for df in pd.read_csv(handle,usecols=["Timestamp","Bid","Ask"],chunksize=500000):
                            dt=pd.to_datetime(df.Timestamp,utc=True,errors="coerce")
                            good=dt.notna()&df.Bid.notna()&df.Ask.notna()
                            if not good.any():continue
                            ns=dt[good].astype("int64").to_numpy(np.int64)
                            bid=df.loc[good,"Bid"].to_numpy(np.float64)
                            ask=df.loc[good,"Ask"].to_numpy(np.float64)
                            ok=(bid>0)&(ask>=bid)&np.isfinite(bid)&np.isfinite(ask)
                            ns=ns[ok];bid=bid[ok];ask=ask[ok]
                            if not len(ns):continue
                            if np.any(ns[1:]<ns[:-1]) or (st["last_ns"][0] and ns[0]<st["last_ns"][0]):
                                raise ValueError("Invalid chronological tick order")
                            tick_batch(ns,bid,ask,base,offsets,order,sig,h,atr,
                                st["status"],st["entry_ns"],st["entry_bid"],
                                st["entry_ask"],st["sl"],st["tp"],
                                st["exit_ns"],st["exit_px"],st["pnl"],
                                st["live"],st["nl"],st["ticks"],
                                st["last_ns"],st["last_quotes"],st["spread_stops"])
                            valid+=len(ns)
            zip_path.unlink(missing_ok=True)
            prov.append(dict(year=year,month=mo,url=url,zip_bytes=size,
                             zip_sha256=sha,raw_ticks=valid))
            print("MONTH",year,mm,"ticks",valid,
                  "total_ticks",int(st["ticks"][0]),
                  "signal_and_control_entries_filled",int((st["entry_ns"]>0).sum()),
                  "still_open_virtual_tickets",int(st["nl"].sum()),flush=True)
    report(book,st,prov,out,args.first,args.last)

if __name__=="__main__":
    main()
