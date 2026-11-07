"""EXNESS RAW-TICK audit: reversed MSS signals, ONLY Stop Loss $20 or Take Profit $10.

Strict one-position-at-a-time 0.01 lot replay Jan 2020–Oct 2026,
WITHOUT any 12h, 24h, Friday, weekend, or year-end forced exit.

The old MSS signal schedule and entry/spread filters are unchanged.
Actual Bid fills BUY exit / SELL entry, actual Ask fills SELL exit / BUY entry.
Gap-through stops execute at the first real post-gap quote, not the stop price.
No swaps in available Bid/Ask source: all P/L excludes swaps (explicit).
Any position still open on final raw tick is UNREALIZED, not counted as closed.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd,requests
from numba import njit

@njit(cache=False)
def replay_ticks(t,bids,asks,book,basehour,st,
                 closed_i,entry_ns,exit_ns,entry_price,exit_price,direction_out,
                 net_out,exit_type,entry_spread,weekend_held,entry_i_ns,
                 raw_stats,annual_equity):
    # st: pos_open,side,entry,SL,TP,entry_timestamp,peak_equity,realized_equity,
    # max_dd, min_equity, last_hour, last_timestamp, last_bid,last_ask,
    # entry_spread, day_seen, max_floating_loss, n_trades_started,
    # n_ignored_busy, n_ignored_spread, n_ignored_closehour
    for z in range(len(t)):
        ns=t[z]
        bid=bids[z];ask=asks[z]
        if not np.isfinite(bid) or not np.isfinite(ask) or bid<=0 or ask<bid:continue
        if st[11]!=0 and ns<st[11]:
            raise ValueError("Source ticks not monotonically ordered")
        hr=ns//3600000000000
        first=hr!=int(st[10])
        if st[0]>0.5:
            side=int(st[1])
            exitpx=bid if side==1 else ask
            stophit=(exitpx<=st[3]) if side==1 else (exitpx>=st[3])
            takehit=(exitpx>=st[4]) if side==1 else (exitpx<=st[4])
            equity=st[7]+side*(exitpx-st[2])-.22
            if equity>st[6]:st[6]=equity
            dd=st[6]-equity
            if dd>st[8]:st[8]=dd
            if equity<st[9]:st[9]=equity
            mark_pnl=side*(exitpx-st[2])-.22
            if mark_pnl<st[16]:st[16]=mark_pnl
            if stophit or takehit:
                k=closed_i[0]
                if k>=len(entry_ns):raise ValueError("Closed trade overflow")
                closed_i[0]+=1
                entry_ns[k]=int(st[5]);exit_ns[k]=ns
                entry_price[k]=st[2];exit_price[k]=exitpx
                direction_out[k]=side
                net_out[k]=side*(exitpx-st[2])-.22
                exit_type[k]=2 if stophit else 1
                entry_spread[k]=st[14]
                weekend_held[k]=1 if ((ns-int(st[5]))//1000000000>48*3600) else 0
                entry_i_ns[k]=int(st[5])
                st[7]+=net_out[k]
                st[0]=0.
                # Filled stop/TP at actual tradable Bid/Ask, incl weekend gap
        if first and 0<=hr-basehour<len(book) and book[hr-basehour]!=0:
            if st[0]>0.5:st[18]+=1
            elif (ns//60000000000)%60 >=10:st[20]+=1
            elif ask-bid>.55:st[19]+=1
            else:
                side=-int(book[hr-basehour])
                px=ask if side==1 else bid
                st[0]=1.
                st[1]=side
                st[2]=px
                st[3]=px-side*10.
                st[4]=px+side*10.
                st[5]=ns
                st[14]=ask-bid
                st[16]=0.
                st[17]+=1
                # Entry commission/spread already in expected net exit P/L.
                # Also update initial drawdown from fees.
                equity=st[7]-.22-(ask-bid)
                if equity<st[9]:st[9]=equity
                dd=st[6]-equity
                if dd>st[8]:st[8]=dd
        st[10]=hr;st[11]=ns;st[12]=bid;st[13]=ask
        raw_stats[0]+=1

def original_schedule(h1_path):
    d=pd.read_csv(h1_path)
    d=d[d.complete.astype(str).str.lower().isin(("true","1"))].reset_index(drop=True)
    t=pd.to_datetime(d.hour_utc,utc=True)
    lo=d.bid_low;hi=d.bid_high;op=d.bid_open;cl=d.bid_close
    atr=(hi-lo).rolling(24,min_periods=24).mean()
    lo_sweep=(lo<lo.shift(1).rolling(48,min_periods=48).min()) & ((np.minimum(op,cl)-lo)/(hi-lo).clip(lower=.01)>.25)
    hi_sweep=(hi>hi.shift(1).rolling(48,min_periods=48).max()) & ((hi-np.maximum(op,cl))/(hi-lo).clip(lower=.01)>.25)
    buy=lo_sweep.shift(2,fill_value=False)&(cl>lo.shift(2)+.6*atr)&(cl>op)&(cl>hi.shift(1))
    sell=hi_sweep.shift(2,fill_value=False)&(cl<hi.shift(2)-.6*atr)&(cl<op)&(cl<lo.shift(1))
    sides=np.where(buy,1,np.where(sell,-1,0)).astype(np.int8)
    h=d.hour_epoch.to_numpy(np.int64);base=int(h[0])
    sched=np.zeros(int(h[-1]-h[0]+5),np.int8)
    total=0
    for j in np.flatnonzero(sides[:-1]):
        i=j+1
        if h[i]-h[j]!=1:continue
        if t.iloc[i].weekday()==4 and t.iloc[i].hour>=19:continue
        if not np.isfinite(atr.iloc[j]):continue
        sched[int(h[i]-base)]=sides[j]
        total+=1
    print("LOCKED_SCHEDULE",total,"H1",len(d),"RANGE",str(t.min()),str(t.max()),flush=True)
    return base,sched,dict(locked_original_signals=total,source_qualified_h1=len(d))

def fetch_month(url,outfile):
    sha=hashlib.sha256();total=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with outfile.open("wb") as f:
            for x in r.iter_content(1<<20):
                if x:f.write(x);sha.update(x);total+=len(x)
    if not zipfile.is_zipfile(outfile):raise ValueError("Non-zip downloaded")
    return sha.hexdigest(),total

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--h1",required=True)
    p.add_argument("--out",default="results/reversed_tp_sl_only")
    p.add_argument("--first",type=int,default=2020)
    p.add_argument("--last",type=int,default=2026)
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    base,book,meta=original_schedule(a.h1)
    capacity=3000
    arr_ns=np.zeros(capacity,np.int64);arr_out_ns=np.zeros(capacity,np.int64)
    arr_entry=np.zeros(capacity);arr_exit=np.zeros(capacity)
    arr_side=np.zeros(capacity,np.int8);arr_net=np.zeros(capacity)
    arr_type=np.zeros(capacity,np.int8);arr_spread=np.zeros(capacity)
    arr_weekend=np.zeros(capacity,np.int8);arr_open_ns=np.zeros(capacity,np.int64)
    closed_i=np.zeros(1,np.int64)
    st=np.zeros(22,np.float64);st[9]=0;st[10]=-1;st[11]=0;st[6]=0;st[7]=0
    raw_stats=np.zeros(1,np.int64);annual=np.zeros(1,np.float64)
    provenance=[]
    for yr in range(a.first,a.last+1):
        months=range(1,13) if yr<2026 else range(1,11)
        for m in months:
            mm=f"{m:02}"
            url=f"https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{yr}/{mm}/Exness_XAUUSD_Raw_Spread_{yr}_{mm}.zip"
            f=out/f"{yr}_{mm}.zip"
            sha,size=fetch_month(url,f)
            rows=0
            with zipfile.ZipFile(f) as z:
                bad=z.testzip()
                if bad:raise RuntimeError('ZIP CRC failed '+str(bad))
                for name in z.namelist():
                    if not name.lower().endswith(".csv"):continue
                    with z.open(name) as rd:
                        for df in pd.read_csv(rd,usecols=["Timestamp","Bid","Ask"],chunksize=500000):
                            dt=pd.to_datetime(df.Timestamp,utc=True,errors="coerce")
                            ok=dt.notna()&df.Bid.notna()&df.Ask.notna()
                            t=dt[ok].astype("int64").to_numpy(np.int64)
                            if len(t)==0:continue
                            if np.any(t[1:]<t[:-1]) or (st[11]>0 and t[0]<st[11]):
                                raise ValueError("Source out-of-order rows "+url)
                            replay_ticks(t,df.Bid[ok].to_numpy(np.float64),
                                df.Ask[ok].to_numpy(np.float64),book,base,st,
                                closed_i,arr_ns,arr_out_ns,arr_entry,arr_exit,arr_side,
                                arr_net,arr_type,arr_spread,arr_weekend,arr_open_ns,
                                raw_stats,annual)
                            rows+=len(t)
            f.unlink(missing_ok=True)
            provenance.append(dict(year=yr,month=m,zip_sha256=sha,bytes=size,ticks=rows,url=url))
            print("PROCESSED_MONTH",yr,mm,"ticks",rows,
                  "closed",int(closed_i[0]),"started",int(st[17]),
                  "open",int(st[0]),"equity_pnl",round(float(st[7]),3),flush=True)
    n=int(closed_i[0])
    ledger=pd.DataFrame({
        "entry_utc":pd.to_datetime(arr_ns[:n],unit="ns",utc=True).astype(str),
        "exit_utc":pd.to_datetime(arr_out_ns[:n],unit="ns",utc=True).astype(str),
        "direction":np.where(arr_side[:n]==1,"BUY","SELL"),
        "entry_price":arr_entry[:n],"exit_price":arr_exit[:n],
        "stop_price":arr_entry[:n]-arr_side[:n]*10.,
        "take_price":arr_entry[:n]+arr_side[:n]*10.,
        "entry_spread_usd":arr_spread[:n],
        "exit_reason":np.where(arr_type[:n]==1,"TP","SL"),
        "net_after_commission_and_slippage_allowance":arr_net[:n],
        "net_before_cost_allowance":arr_net[:n]+.22
    })
    ledger["entry_year"]=pd.to_datetime(ledger.entry_utc,utc=True,format='mixed').dt.year
    ledger["exit_year"]=pd.to_datetime(ledger.exit_utc,utc=True,format='mixed').dt.year
    ledger["holding_hours"]=(pd.to_datetime(ledger.exit_utc,utc=True,format='mixed')-pd.to_datetime(ledger.entry_utc,utc=True,format='mixed')).dt.total_seconds()/3600
    ledger.to_csv(out/"REVERSED_MSS_SL10_TP10_TP_OR_SL_ONLY_2020_2026.csv",index=False)
    byyear=[]
    for yr,g in ledger.groupby("exit_year"):
        vals=g.net_after_commission_and_slippage_allowance.to_numpy(float)
        byyear.append(dict(year=int(yr),trades_closed=len(g),TP=int((g.exit_reason=="TP").sum()),
            SL=int((g.exit_reason=="SL").sum()),net=float(vals.sum()),winrate=float(np.mean(vals>0)),
            avg_holding_hours=float(g.holding_hours.mean()),max_holding_hours=float(g.holding_hours.max())))
    pd.DataFrame(byyear).to_csv(out/"YEARLY_CLOSED_TRADES_TP_SL_ONLY.csv",index=False)
    # End of supplied October 2026 tick archive does NOT close an active trade.
    marked_open=None
    if st[0]>0.5:
        side=int(st[1]);entry=st[2]
        mark=st[12] if side==1 else st[13]
        unrealized=side*(mark-entry)-.22
        marked_open=dict(direction="BUY" if side==1 else "SELL",
           opened_at_utc=str(pd.Timestamp(int(st[5]),unit='ns',tz='UTC')),
           current_mark_at_utc=str(pd.Timestamp(int(st[11]),unit='ns',tz='UTC')),
           entry=float(entry),current_exit_quote=float(mark),
           SL=float(st[3]),TP=float(st[4]),
           unrealized_after_cost_allowance=float(unrealized))
    pnl=ledger.net_after_commission_and_slippage_allowance.to_numpy(float)
    eq=np.r_[0.,np.cumsum(pnl)]
    nTP=int((ledger.exit_reason=="TP").sum())
    nSL=int((ledger.exit_reason=="SL").sum())
    gross=float((ledger.net_before_cost_allowance).sum())
    summary={
       **meta,
       "rules":"Same MSS 48H sweep age=2 strength=0.6. Reverse original signal: old BUY => SELL, old SELL => BUY. Open on first new eligible H1 quote if Ask-Bid<=0.55, single open position maximum. TP exactly $10 favorable and SL exactly $10 unfavorable from actual Ask/Bid entry. Close ONLY on broker-side TP or SL at actual first qualifying Bid/Ask tick. NO hourly, Friday, weekend, annual, or end-of-sample forced close.",
       "source_period":f"{a.first}-01 through {a.last}-"+("10" if a.last==2026 else "12"),
       "count_raw_ticks":int(raw_stats[0]),
       "scheduled_total_H1":int(np.count_nonzero(book)),
       "trades_opened":int(st[17]),
       "trades_closed":n,
       "tp_hit":nTP,"sl_hit":nSL,
       "tp_hit_rate_closed":float(nTP/n) if n else None,
       "winning_trades_after_cost":int((pnl>0).sum()),
       "closed_net_001lot":float(pnl.sum()),
       "closed_gross_001lot":gross,
       "nominal_costs":float(n*.22),
       "max_closed_equity_drawdown":float(np.max(np.maximum.accumulate(eq)-eq)),
       "max_tick_mark_to_market_drawdown_before_swaps":float(st[8]),
       "maximum_holding_hours_closed":float(ledger.holding_hours.max()) if n else None,
       "average_holding_hours_closed":float(ledger.holding_hours.mean()) if n else None,
       "ignored_signals_when_position_open":int(st[18]),
       "ignored_signals_high_spread":int(st[19]),
       "ignored_signals_late_first_quote":int(st[20]),
       "end_of_data_OPEN_unclosed_position":marked_open,
       "caveats":"0.01 lot XAUUSD one ounce; fees assumed $0.07 round-trip + $0.15 additional adverse execution cost/trade. No historical Exness overnight swap rate, margin liquidation, outages or live-latency available. Negative gap crossing executes at next actual quote; terminal position remains OPEN. All P/L excluding swaps/financing. No profit guarantees.",
       "monthly_source_provenance":provenance
    }
    (out/"AUDIT_SUMMARY_TP_SL_ONLY.json").write_text(json.dumps(summary,indent=2))
    print("REVERSED_ONLY_TP_SL_FINAL",json.dumps({k:v for k,v in summary.items() if k!="monthly_source_provenance"},default=str),flush=True)
if __name__=="__main__":main()
