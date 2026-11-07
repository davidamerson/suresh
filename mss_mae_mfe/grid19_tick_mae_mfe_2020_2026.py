"""Exness XAUUSD 19-condition TP/SL first-hit replay with path excursion audit.

Original locked MSS 48H sweep/age2/strength0.6 H1 signals, REVERSED
old BUY -> SELL, old SELL -> BUY. Same first-hour raw quote, spread <=0.55,
one simultaneous position per TP/SL variant, no time exit, no Friday exit.

Exactly the 19 user-specified pairs, distances in $/oz (not broker pips):
TP10..TP1 SL10; TP10 SL9..SL1. Actual tick BID for BUY exit, ASK for SELL
exit. Record maximum adverse excursion MAE, maximum favorable excursion MFE
from entry through (and including) FIRST true stop/take touch on live side.
A trade not closed by Oct 30 2026 remains unrealized, never force closed.
Fees: actual spread embedded in raw entry/exit plus $0.07 0.01-lot
commission + $0.15 *assumed* per-order-roundtrip adverse cost. No historical
swaps available, no margin enforcement or live fill delay.
"""
import argparse, hashlib, json, zipfile, requests
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit

TP=np.array(list(range(10,0,-1))+[10]*9,dtype=np.float64)
SL=np.array([10]*10+list(range(9,0,-1)),dtype=np.float64)
N=19
MAXTR=3000
FEE=.22

@njit
def tick_chunk(t,bs,asks,book,base,on,side,entr,entry_ns,entry_spread,
               mae,mfe,mae_ns,mfe_ns,realized,peak_closed,dd_closed,
               peak_mark,dd_mark,min_equity,
               closed_n,rec_entry_ns,rec_exit_ns,rec_side,rec_entry,rec_exit,
               rec_mae,rec_mfe,rec_mae_ns,rec_mfe_ns,rec_spread,rec_cost,
               rec_reason,rec_stop_slippage,prevhour,prevns,last_quote,stats,
               trade_starts,skipped_busy,skipped_spread,skipped_late):
    for i in range(len(t)):
        n=t[i];bid=bs[i];ask=asks[i]
        if not (np.isfinite(bid) and np.isfinite(ask) and ask>=bid>0):
            continue
        if prevns[0]>0 and n<prevns[0]:
            raise ValueError("Tick timestamp backwards")
        h=n//3600000000000
        first=h!=prevhour[0]
        bidx=h-base
        has_signal=first and 0<=bidx<len(book) and book[bidx]!=0
        min_in_hour=(n//60000000000)%60
        for q in range(N):
            if on[q]!=0:
                d=side[q]
                x=bid if d==1 else ask
                movement=d*(x-entr[q])
                if movement<0.:
                    adverse=-movement
                    if adverse>mae[q]:
                        mae[q]=adverse
                        mae_ns[q]=n
                elif movement>mfe[q]:
                    mfe[q]=movement
                    mfe_ns[q]=n
                mark=realized[q]+movement-FEE
                if mark>peak_mark[q]:
                    peak_mark[q]=mark
                draw=peak_mark[q]-mark
                if draw>dd_mark[q]: dd_mark[q]=draw
                if mark<min_equity[q]: min_equity[q]=mark

                hitSL=movement<=-SL[q]
                hitTP=movement>=TP[q]
                if hitSL or hitTP:
                    k=closed_n[q]
                    if k>=MAXTR: raise ValueError("Trade ledger capacity exceeded")
                    rec_entry_ns[q,k]=entry_ns[q]
                    rec_exit_ns[q,k]=n
                    rec_side[q,k]=d
                    rec_entry[q,k]=entr[q]
                    rec_exit[q,k]=x
                    rec_mae[q,k]=mae[q]
                    rec_mfe[q,k]=mfe[q]
                    rec_mae_ns[q,k]=mae_ns[q]
                    rec_mfe_ns[q,k]=mfe_ns[q]
                    rec_spread[q,k]=entry_spread[q]
                    rec_cost[q,k]=movement-FEE
                    rec_reason[q,k]=1 if hitTP else 2
                    rec_stop_slippage[q,k]=(-movement-SL[q]) if hitSL else 0.
                    closed_n[q]=k+1
                    realized[q]+=movement-FEE
                    if realized[q]>peak_closed[q]:peak_closed[q]=realized[q]
                    dd=peak_closed[q]-realized[q]
                    if dd>dd_closed[q]:dd_closed[q]=dd
                    on[q]=0
            if has_signal:
                if on[q]!=0:
                    skipped_busy[q]+=1
                elif min_in_hour>=10:
                    skipped_late[q]+=1
                elif ask-bid>.55:
                    skipped_spread[q]+=1
                else:
                    d=-book[bidx]
                    on[q]=1
                    side[q]=d
                    entr[q]=ask if d==1 else bid
                    entry_ns[q]=n
                    entry_spread[q]=ask-bid
                    mae[q]=ask-bid
                    mfe[q]=0.
                    mae_ns[q]=n
                    mfe_ns[q]=n
                    trade_starts[q]+=1
                    startmark=realized[q]-(ask-bid)-FEE
                    if startmark<min_equity[q]:min_equity[q]=startmark
                    xdd=peak_mark[q]-startmark
                    if xdd>dd_mark[q]:dd_mark[q]=xdd
        prevhour[0]=h
        prevns[0]=n
        last_quote[0]=bid
        last_quote[1]=ask
        stats[0]+=1

def locked_schedule(h1):
    df=pd.read_csv(h1)
    df=df[df.complete.astype(str).str.lower().isin(('true','1'))].reset_index(drop=True)
    t=pd.to_datetime(df.hour_utc,utc=True)
    lo=df.bid_low;hi=df.bid_high;op=df.bid_open;cl=df.bid_close
    atr=(hi-lo).rolling(24,min_periods=24).mean()
    lowsweep=(lo<lo.shift(1).rolling(48,min_periods=48).min()) & ((np.minimum(op,cl)-lo)/(hi-lo).clip(lower=.01)>.25)
    hisweep=(hi>hi.shift(1).rolling(48,min_periods=48).max()) & ((hi-np.maximum(op,cl))/(hi-lo).clip(lower=.01)>.25)
    buy=lowsweep.shift(2,fill_value=False)&(cl>lo.shift(2)+.6*atr)&(cl>op)&(cl>hi.shift(1))
    sell=hisweep.shift(2,fill_value=False)&(cl<hi.shift(2)-.6*atr)&(cl<op)&(cl<lo.shift(1))
    s=np.where(buy,1,np.where(sell,-1,0)).astype(np.int8)
    hours=df.hour_epoch.to_numpy(np.int64)
    base=int(hours[0]);book=np.zeros(int(hours[-1]-base+5),np.int8)
    for j in np.flatnonzero(s[:-1]):
        ix=j+1
        if hours[ix]-hours[j]!=1: continue
        if t.iloc[ix].weekday()==4 and t.iloc[ix].hour>=19: continue
        if not np.isfinite(atr.iloc[j]):continue
        book[hours[ix]-base]=s[j]
    print('H1_READY',len(df),'SCHEDULED',int(np.count_nonzero(book)),flush=True)
    return base,book

def download(url,p):
    sha=hashlib.sha256();sz=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with p.open('wb') as f:
            for chunk in r.iter_content(1024*1024):
                if chunk:
                    f.write(chunk);sha.update(chunk);sz+=len(chunk)
    if not zipfile.is_zipfile(p):raise RuntimeError('Not zip '+url)
    return sha.hexdigest(),sz

def qstats(v):
    arr=np.asarray(v,dtype=float)
    if not len(arr):return {key:None for key in ('mean','p50','p75','p90','p95','max')}
    return dict(mean=float(np.mean(arr)),p50=float(np.quantile(arr,.5)),
        p75=float(np.quantile(arr,.75)),p90=float(np.quantile(arr,.9)),
        p95=float(np.quantile(arr,.95)),max=float(arr.max()))

def excursions_summary(trades):
    rows=[]
    for (tp,sl),g in trades.groupby(['TP_USD','SL_USD'],sort=False):
        for outcome,part,measure in [('TP','MAE_USD'),('SL','MFE_USD')]:
            sub=g[g.exit_reason==outcome]
            values=sub[measure].to_numpy(float)
            qs=qstats(values)
            rows.append(dict(TP_USD=tp,SL_USD=sl,exit_reason=outcome,
                metric=measure,samples=len(values),**qs,**{
                    f'ge_{th}_USD_pct':float(100*np.mean(values>=th-1e-9)) if len(values) else None
                    for th in range(1,11)}))
    return pd.DataFrame(rows)

def grid_results(trades,config,opened,dd_closed,dd_mark,skipped_busy,skipped_spread,last_open):
    out=[];yearly=[]
    for q in range(N):
        tp=float(TP[q]);sl=float(SL[q])
        g=trades[trades.setting_idx==q].sort_values('exit_utc')
        vals=g.net_usd_0p01lot.to_numpy(float)
        for label,sub in [('ALL_2020_2026',g),('TRAIN_2020_2024',g[g.exit_year<=2024]),
                          ('OOS_2025_2026',g[g.exit_year>=2025])]:
            p=sub.net_usd_0p01lot.to_numpy(float)
            eq=np.r_[0.,np.cumsum(p)]
            tpct=int((sub.exit_reason=='TP').sum())
            sp=int((sub.exit_reason=='SL').sum())
            out.append(dict(TP_USD=tp,SL_USD=sl,period=label,
                trades=len(sub),TP_hits=tpct,SL_hits=sp,
                TP_pct=float(100*tpct/len(sub)) if len(sub) else None,
                net_after_spread_commission_extra=float(p.sum()),
                gross_after_bid_ask_spread=float(p.sum()+FEE*len(sub)),
                assumed_commission_and_extra_cost=float(FEE*len(sub)),
                max_closed_trade_DD=float(np.max(np.maximum.accumulate(eq)-eq)),
                pathwise_full_max_closed_DD=float(dd_closed[q]) if label=='ALL_2020_2026' else None,
                pathwise_full_max_marked_DD=float(dd_mark[q]) if label=='ALL_2020_2026' else None,
                started_all_periods=int(opened[q]) if label=='ALL_2020_2026' else None,
                open_at_end=int(last_open[q]) if label=='ALL_2020_2026' else None,
                skipped_when_busy=int(skipped_busy[q]) if label=='ALL_2020_2026' else None,
                skipped_high_spread=int(skipped_spread[q]) if label=='ALL_2020_2026' else None,
                TP_winner_MAE_mean_USD=float(sub.loc[sub.exit_reason=='TP','MAE_USD'].mean()),
                TP_winner_MAE_p90_USD=float(sub.loc[sub.exit_reason=='TP','MAE_USD'].quantile(.9)),
                SL_loser_MFE_mean_USD=float(sub.loc[sub.exit_reason=='SL','MFE_USD'].mean()),
                SL_loser_MFE_p90_USD=float(sub.loc[sub.exit_reason=='SL','MFE_USD'].quantile(.9))))
        for year,part in g.groupby('exit_year'):
            v=part.net_usd_0p01lot.to_numpy(float)
            yearly.append(dict(year=int(year),TP_USD=tp,SL_USD=sl,trades=len(part),
                TP_hits=int((part.exit_reason=='TP').sum()),
                SL_hits=int((part.exit_reason=='SL').sum()),net=float(v.sum()),
                TP_pct=float(100*np.mean(part.exit_reason=='TP')),
                TP_MAE_mean=float(part.loc[part.exit_reason=='TP','MAE_USD'].mean()),
                SL_MFE_mean=float(part.loc[part.exit_reason=='SL','MFE_USD'].mean())))
    return pd.DataFrame(out),pd.DataFrame(yearly)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--h1',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--first',type=int,default=2020)
    p.add_argument('--last',type=int,default=2026)
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    base,book=locked_schedule(a.h1)
    on=np.zeros(N,np.int8);side=np.zeros(N,np.int8)
    entr=np.zeros(N); entry_ns=np.zeros(N,np.int64);entry_spread=np.zeros(N)
    mae=np.zeros(N);mfe=np.zeros(N);mae_ns=np.zeros(N,np.int64);mfe_ns=np.zeros(N,np.int64)
    realized=np.zeros(N);peak_closed=np.zeros(N);dd_closed=np.zeros(N)
    peak_mark=np.zeros(N);dd_mark=np.zeros(N);min_equity=np.zeros(N)
    closed_n=np.zeros(N,np.int64)
    dims=(N,MAXTR)
    rec_entry_ns=np.zeros(dims,np.int64);rec_exit_ns=np.zeros(dims,np.int64)
    rec_side=np.zeros(dims,np.int8);rec_entry=np.zeros(dims);rec_exit=np.zeros(dims)
    rec_mae=np.zeros(dims);rec_mfe=np.zeros(dims)
    rec_mae_ns=np.zeros(dims,np.int64);rec_mfe_ns=np.zeros(dims,np.int64)
    rec_spread=np.zeros(dims);rec_cost=np.zeros(dims)
    rec_reason=np.zeros(dims,np.int8);rec_stop_slippage=np.zeros(dims)
    prevhour=np.full(1,-1,np.int64);prevns=np.zeros(1,np.int64)
    last_quote=np.zeros(2);stats=np.zeros(1,np.int64)
    starts=np.zeros(N,np.int64);skipbusy=np.zeros(N,np.int64)
    skipspread=np.zeros(N,np.int64);skiplate=np.zeros(N,np.int64)
    prov=[]
    for yr in range(a.first,a.last+1):
        for mo in range(1,11 if yr==2026 else 13):
            mm=f'{mo:02}'
            url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{yr}/{mm}/Exness_XAUUSD_Raw_Spread_{yr}_{mm}.zip'
            dest=out/f'{yr}_{mm}.zip'
            sha,size=download(url,dest)
            rows=0
            with zipfile.ZipFile(dest) as archive:
                fail=archive.testzip()
                if fail:raise ValueError('Zip CRC failed '+str(fail))
                for mem in archive.namelist():
                    if not mem.lower().endswith('.csv'):continue
                    with archive.open(mem) as reader:
                        for df in pd.read_csv(reader,usecols=['Timestamp','Bid','Ask'],chunksize=500000):
                            t=pd.to_datetime(df.Timestamp,utc=True,errors='coerce')
                            ok=t.notna()&df.Bid.notna()&df.Ask.notna()
                            ns=t[ok].astype('int64').to_numpy(np.int64)
                            if len(ns)==0:continue
                            if np.any(ns[1:]<ns[:-1]) or (prevns[0]>0 and ns[0]<prevns[0]):
                                raise ValueError('Exness source ticks unordered '+url)
                            tick_chunk(ns,df.Bid[ok].to_numpy(np.float64),
                                df.Ask[ok].to_numpy(np.float64),book,base,
                                on,side,entr,entry_ns,entry_spread,
                                mae,mfe,mae_ns,mfe_ns,
                                realized,peak_closed,dd_closed,peak_mark,dd_mark,min_equity,
                                closed_n,rec_entry_ns,rec_exit_ns,rec_side,rec_entry,
                                rec_exit,rec_mae,rec_mfe,rec_mae_ns,rec_mfe_ns,
                                rec_spread,rec_cost,rec_reason,rec_stop_slippage,
                                prevhour,prevns,last_quote,stats,starts,skipbusy,
                                skipspread,skiplate)
                            rows+=len(ns)
            dest.unlink(missing_ok=True)
            prov.append(dict(year=yr,month=mo,url=url,sha256=sha,source_zip_bytes=size,raw_ticks=rows))
            print('MONTH_DONE',yr,mm,'ticks',rows,'total_ticks',int(stats[0]),
                  'TP10_SL10_closed',int(closed_n[0]),'TP1_SL10_closed',int(closed_n[9]),
                  'TP10_SL1_closed',int(closed_n[18]),flush=True)

    data=[]
    for q in range(N):
        for j in range(int(closed_n[q])):
            entry=rec_entry_ns[q,j];exit=rec_exit_ns[q,j]
            data.append(dict(setting_idx=q,TP_USD=float(TP[q]),SL_USD=float(SL[q]),
                direction='BUY' if rec_side[q,j]==1 else 'SELL',
                entry_utc=str(pd.Timestamp(entry,unit='ns',tz='UTC')),
                exit_utc=str(pd.Timestamp(exit,unit='ns',tz='UTC')),
                exit_year=int(pd.Timestamp(exit,unit='ns',tz='UTC').year),
                entry_price=float(rec_entry[q,j]),
                exit_price=float(rec_exit[q,j]),
                entry_spread_USD=float(rec_spread[q,j]),
                exit_reason='TP' if rec_reason[q,j]==1 else 'SL',
                MAE_USD=float(rec_mae[q,j]), MFE_USD=float(rec_mfe[q,j]),
                MAE_time_utc=str(pd.Timestamp(rec_mae_ns[q,j],unit='ns',tz='UTC')),
                MFE_time_utc=str(pd.Timestamp(rec_mfe_ns[q,j],unit='ns',tz='UTC')),
                holding_hours=float((exit-entry)/3.6e12),
                raw_bid_ask_gross_USD=float(rec_cost[q,j]+FEE),
                net_usd_0p01lot=float(rec_cost[q,j]),
                stop_gap_overshoot_USD=float(rec_stop_slippage[q,j]),
                commission_USD=.07,extra_execution_assumption_USD=.15))
    trades=pd.DataFrame(data)
    trades.to_csv(out/'ALL_19_SETTINGS_EXACT_TRADE_BY_TRADE_MAE_MFE.csv',index=False)
    grid,yearly=grid_results(trades,None,starts,dd_closed,dd_mark,skipbusy,skipspread,on)
    grid.to_csv(out/'ALL_19_SETTINGS_TRAIN_OOS_FINAL_SUMMARY.csv',index=False)
    yearly.to_csv(out/'ALL_19_SETTINGS_YEARLY_TP_SL_PNL.csv',index=False)
    ex=excursions_summary(trades)
    ex.to_csv(out/'TP_WINNER_MAE_AND_SL_LOSER_MFE_QUANTILES_THRESHOLD.csv',index=False)
    histogram=[]
    for (tp,sl),g in trades.groupby(['TP_USD','SL_USD'],sort=False):
        for outcome,metric in [('TP','MAE_USD'),('SL','MFE_USD')]:
            v=g.loc[g.exit_reason==outcome,metric].to_numpy(float)
            for low in range(0,10):
                count=int(np.sum((v>=low)&(v<low+1)))
                histogram.append(dict(TP_USD=tp,SL_USD=sl,exit_reason=outcome,metric=metric,
                    excursion_min_USD=low,excursion_max_exclusive_USD=low+1,
                    count=count,percent=float(100*count/len(v)) if len(v) else None))
            count=int((v>=10).sum())
            histogram.append(dict(TP_USD=tp,SL_USD=sl,exit_reason=outcome,metric=metric,
                excursion_min_USD=10,excursion_max_exclusive_USD=None,
                count=count,percent=float(100*count/len(v)) if len(v) else None))
    pd.DataFrame(histogram).to_csv(out/'ALL_19_SETTINGS_MAE_MFE_1USD_HISTOGRAM.csv',index=False)
    openpositions=[]
    for q in range(N):
        if on[q]:
            px=last_quote[0] if side[q]==1 else last_quote[1]
            openpositions.append(dict(TP_USD=float(TP[q]),SL_USD=float(SL[q]),
                entry_utc=str(pd.Timestamp(entry_ns[q],unit='ns',tz='UTC')),
                entry=float(entr[q]),last_actual_exit_quote=float(px),
                unrealized_after_cost_excluding_swap=float(side[q]*(px-entr[q])-FEE),
                MAE_to_date=float(mae[q]),MFE_to_date=float(mfe[q])))
    audit=dict(source_start=a.first,source_end=a.last,
        tick_count=int(stats[0]),original_MSS_scheduled_H1=int(np.count_nonzero(book)),
        settings=[dict(tp=float(t),sl=float(s)) for t,s in zip(TP,SL)],
        independent_one_position_per_setting=True,no_time_exit=True,
        actual_stop_tp_quote_fill_first_tick=True,
        bid_ask_spread_included=True,
        per_trade_round_trip_commission_usd=.07,
        per_trade_additional_assumed_execution_cost_usd=.15,
        historical_swap_available=False,
        swaps_included=False,
        actual_weekend_gaps=True,
        margin_stopout_simulated=False,
        price_units='USD per XAU ounce. pip/point sizes depend on MT4 broker symbol digits.',
        mark_to_market_max_drawdown_USD=[float(x) for x in dd_mark],
        closed_curve_max_drawdown_USD=[float(x) for x in dd_closed],
        open_positions_not_forced_closed=openpositions,
        rows=int(len(trades)),source_zip_sha256=prov)
    (out/'EXECUTION_SOURCE_AND_DRAWDOWN_AUDIT.json').write_text(json.dumps(audit,indent=2))
    head=grid[(grid.period=='ALL_2020_2026')].sort_values('net_after_spread_commission_extra',ascending=False)
    print('FINAL_ALL_19',head[['TP_USD','SL_USD','trades','TP_hits','SL_hits','TP_pct','net_after_spread_commission_extra','pathwise_full_max_marked_DD']].to_json(orient='records'),flush=True)
    print('REPLAY_DONE',json.dumps(dict(total_ticks=int(stats[0]),total_trades=int(len(trades)),
              open_positions=openpositions)),flush=True)

if __name__=='__main__': main()
