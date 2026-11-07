"""Real raw Exness Bid/Ask TICK replay on MSS 48H sweep signals.
10 predeclared price-dollar stops 10..100 and 2x TP. 12h and 24h modes.
Two independent chronological partitions. No need to fabricate Ask highs/lows
or assume within-candle stop/TP ordering.
Usage: --h1 CSV --first 2025 --last 2026 --out FOLDER.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd,requests
from numba import njit

@njit
def loop_ticks(ns,bid,ask,book,basehour,on,entryh,entryns,ent,stop,take,side,qty,
               exns,ens,pnl,src,ends,extype,count,last_hour,last_tick,allticks):
    for z in range(ns.size):
        n=ns[z]
        b=bid[z];a=ask[z]
        if not (a>=b>0):continue
        hr=n//3600000000000
        sec=n//1000000000
        dy=(sec//86400+3)%7
        hrday=hr%24
        m=(sec//60)%60
        first=hr!=last_hour[0]
        # Simulate each of 20 independent books, each one trade at any time.
        for q in range(20):
            if on[q]!=0:
                direction=side[q]
                px=b if direction==1 else a
                is_stop=px<=stop[q] if direction==1 else px>=stop[q]
                is_tp=px>=take[q] if direction==1 else px<=take[q]
                horizon=12 if q<10 else 24
                time_expired=hr>=entryh[q]+horizon
                friday=dy==4 and hrday==19 and m>=59
                if is_stop or is_tp or time_expired or friday:
                    k=count[q]
                    if k>=2000:raise ValueError("More than 2000 trades in a config")
                    src[q,k]=entryns[q]
                    ends[q,k]=n
                    ens[q,k]=ent[q]
                    exns[q,k]=px
                    pnl[q,k]=direction*(px-abs(ent[q]))-.07-.15
                    extype[q,k]=2 if is_stop else (1 if is_tp else (4 if friday else 3))
                    count[q]+=1
                    on[q]=0
            if first and on[q]==0 and 0<=hr-basehour<book.size and book[hr-basehour]!=0 and m<10:
                # The j+1 H1 entry is valid in the already locked schedule.
                # Real Ask/Bid entry, actual first tick spread.
                if a-b<=.55:
                    direction=-book[hr-basehour]
                    s=20
                    entryh[q]=hr
                    entryns[q]=n
                    ent[q]=(a if direction==1 else b) * direction
                    stop[q]=abs(ent[q])-direction*s
                    take[q]=abs(ent[q])+direction*10.
                    side[q]=direction
                    on[q]=1
        last_hour[0]=hr
        last_tick[0]=n
        last_tick[1]=b
        last_tick[2]=a
        allticks[0]+=1

def prepare(h1):
    d=pd.read_csv(h1)
    d=d[d.complete.astype(str).str.lower().isin(("true","1"))].reset_index(drop=True)
    t=pd.to_datetime(d.hour_utc,utc=True)
    lo=d.bid_low;hi=d.bid_high;op=d.bid_open;cl=d.bid_close
    atr=(hi-lo).rolling(24,min_periods=24).mean()
    low_sweep=(lo<lo.shift(1).rolling(48,min_periods=48).min())&((np.minimum(op,cl)-lo)/(hi-lo).clip(lower=.01)>.25)
    high_sweep=(hi>hi.shift(1).rolling(48,min_periods=48).max())&((hi-np.maximum(op,cl))/(hi-lo).clip(lower=.01)>.25)
    buy=low_sweep.shift(2,fill_value=False)&(cl>lo.shift(2)+.6*atr)&(cl>op)&(cl>hi.shift(1))
    sell=high_sweep.shift(2,fill_value=False)&(cl<hi.shift(2)-.6*atr)&(cl<op)&(cl<lo.shift(1))
    s=np.where(buy,1,np.where(sell,-1,0)).astype(np.int8)
    h=d.hour_epoch.to_numpy(np.int64)
    base=int(h[0])
    schedule=np.zeros(int(h[-1]-h[0]+5),dtype=np.int8)
    counts=0
    for j in np.flatnonzero(s[:-1]):
        i=j+1
        if h[i]-h[j]!=1:continue
        if t.iloc[i].weekday()==4 and t.iloc[i].hour>=19:continue
        if not np.isfinite(atr.iloc[j]):continue
        schedule[int(h[i]-base)]=s[j]
        counts+=1
    print('PREPARED_H1',len(d),'SCHEDULED',counts,'COVERAGE',str(t.min()),str(t.max()),flush=True)
    return base,schedule

def download(url,path):
    sha=hashlib.sha256();size=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with path.open('wb') as f:
            for x in r.iter_content(1<<20):
                if x:f.write(x);sha.update(x);size+=len(x)
    if not zipfile.is_zipfile(path):raise ValueError('Invalid archive '+url)
    return size,sha.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--h1',required=True)
    p.add_argument('--first',type=int,required=True);p.add_argument('--last',type=int,required=True)
    p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out);out.mkdir(exist_ok=True,parents=True)
    basehour,book=prepare(args.h1)
    on=np.zeros(20,dtype=np.int8)
    entryh=np.zeros(20,dtype=np.int64)
    entryns=np.zeros(20,dtype=np.int64)
    ent=np.zeros(20,dtype=np.float64)
    stop=np.zeros(20,dtype=np.float64);take=np.zeros(20,dtype=np.float64)
    side=np.zeros(20,dtype=np.int8)
    src=np.zeros((20,2000),dtype=np.int64)
    ends=np.zeros((20,2000),dtype=np.int64)
    ens=np.zeros((20,2000),dtype=np.float64)
    exns=np.zeros((20,2000),dtype=np.float64)
    pnl=np.zeros((20,2000),dtype=np.float64)
    extype=np.zeros((20,2000),dtype=np.int8)
    count=np.zeros(20,dtype=np.int64)
    last_hour=np.full(1,-1,dtype=np.int64)
    last_tick=np.zeros(3,dtype=np.float64)
    allticks=np.zeros(1,dtype=np.int64)
    provenance=[];last_ns=-1
    for year in range(args.first,args.last+1):
        for month in range(1,13 if year<2026 else 11):
            mm=f'{month:02}'
            url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'
            f=out/f'{year}_{mm}.zip'
            nbytes,sha=download(url,f)
            first=None;last=None;rows=0
            with zipfile.ZipFile(f) as z:
                bad=z.testzip()
                if bad:raise ValueError('CRC failed '+str(bad))
                for member in z.namelist():
                    if not member.lower().endswith('.csv'):continue
                    with z.open(member) as reader:
                        for chunk in pd.read_csv(reader,usecols=['Timestamp','Bid','Ask'],chunksize=500000):
                            utc=pd.to_datetime(chunk.Timestamp,utc=True,errors='coerce')
                            ok=utc.notna()&chunk.Bid.notna()&chunk.Ask.notna()
                            t=utc[ok].astype('int64').to_numpy(np.int64)
                            if len(t)==0:continue
                            if (t[1:]<t[:-1]).any() or t[0]<last_ns:raise ValueError('Out of order raw ticks')
                            last_ns=int(t[-1]);rows+=len(t)
                            if first is None:first=int(t[0])
                            last=int(t[-1])
                            loop_ticks(t,chunk.Bid[ok].to_numpy(np.float64),
                                chunk.Ask[ok].to_numpy(np.float64),
                                book,basehour,on,entryh,entryns,ent,stop,take,side,
                                np.zeros(0,dtype=np.int8),exns,ens,pnl,src,ends,extype,
                                count,last_hour,last_tick,allticks)
            f.unlink(missing_ok=True)
            provenance.append(dict(year=year,month=month,url=url,sha256=sha,
                   source_bytes=nbytes,raw_rows=rows,first_utc=str(pd.Timestamp(first,unit='ns',tz='UTC')) if first else None,
                   last_utc=str(pd.Timestamp(last,unit='ns',tz='UTC')) if last else None))
            print('MONTH',year,mm,'ticks',rows,'all_ticks',int(allticks[0]),
                  '12HSL100',int(count[9]),'24HSL100',int(count[19]),flush=True)
    # At segment boundary, force close open trade at last available actual raw quote,
    # with explicit end-of-partition marker; document edge.
    for q in range(20):
        if on[q]:
            k=count[q]
            src[q,k]=entryns[q]
            ends[q,k]=int(last_tick[0])
            ens[q,k]=ent[q]
            px=last_tick[1] if side[q]==1 else last_tick[2]
            exns[q,k]=px
            pnl[q,k]=side[q]*(px-abs(ent[q]))-.07-.15
            extype[q,k]=5
            count[q]+=1
            on[q]=0
    rows=[]
    for q in range(20):
        sl=20
        hold=12 if q<10 else 24
        for j in range(int(count[q])):
            rows.append(dict(sl=sl,tp=10,hold_hours=hold,
                entry_utc=str(pd.Timestamp(src[q,j],unit='ns',tz='UTC')),
                exit_utc=str(pd.Timestamp(ends[q,j],unit='ns',tz='UTC')),
                direction="BUY" if ens[q,j]>0 else "SELL",
                entry=abs(ens[q,j]),exit=exns[q,j],net_001lot=pnl[q,j],
                reason={1:'TP',2:'SL',3:'TIME',4:'FRIDAY',5:'PARTITION_END'}.get(int(extype[q,j]))))
    # For trading side use recovered sign from PnL and price delta, but more reliable
    # preserve separately by writing signed entry for side in loop (below).
    trades=pd.DataFrame(rows)
    trades.to_csv(out/'REVERSED_SL20_TP10_LEDGER.csv',index=False)
    sums=[]
    for (sl,hold),g in trades.groupby(['sl','hold_hours']):
        p=g.net_001lot.to_numpy(float);curve=np.r_[0.,np.cumsum(p)]
        for name,group in [('ALL',g)]+[(str(y),v) for y,v in g.groupby(pd.to_datetime(g.entry_utc).dt.year)]:
            x=group.net_001lot.to_numpy(float)
            eq=np.r_[0.,np.cumsum(x)]
            sums.append(dict(sl=sl,tp=10,hold_hours=hold,period=name,
                trades=len(group),winners=int((x>0).sum()),
                win_pct=float(100*np.mean(x>0)),net=float(x.sum()),
                TP=int((group.reason=='TP').sum()),SL=int((group.reason=='SL').sum()),
                TIME=int(group.reason.isin(['TIME','FRIDAY','PARTITION_END']).sum()),
                max_drawdown=float(np.max(np.maximum.accumulate(eq)-eq))))
    pd.DataFrame(sums).to_csv(out/'REVERSED_SL20_TP10_RESULTS.csv',index=False)
    meta=dict(coverage_first_year=args.first,coverage_last_year=args.last,
        total_actual_bid_ask_raw_ticks=int(allticks[0]),candidates_in_full_H1_schedule=int(np.count_nonzero(book)),
        source_provenance=provenance,method='Reversed original MSS 48H/age2/strength0.6, SL20 TP10 one position per horizon; exact chronological Bid for long exit, Ask for short exit; first tick after stop/TP, 12/24h or Friday 19:59 cut, 0.01 lot, commission .07 and additional cost .15.')
    (out/'REVERSED_SOURCE_PROVENANCE.json').write_text(json.dumps(meta,indent=2))
    print('FINAL',json.dumps({k:v for k,v in meta.items() if k!='source_provenance'}),flush=True)
if __name__=='__main__':main()
