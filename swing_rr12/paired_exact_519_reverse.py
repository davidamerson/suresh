"""Paired counterfactual: reverse EXACT original 519 Exness MSS trades at exact
original signal entry ticks, SL20/TP10, max12h/Friday. Uses every tick Bid and
Ask, tracks all overlapping reversed trades individually; original raw trade
LEDGER loaded from prior verified Actions artifact. The original single-position
constraint does not apply to the paired counterfactual (but standalone one-position
opposite strategy is independently tested in reversed_actual_tick_sl20_tp10.py).
"""
import argparse,hashlib,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd,requests
from numba import njit

@njit
def process(t,bid,ask,events,original_dir,ptr, active,an,ep,entryns,entryprice,
            exns,exprice,exitreason, last):
    n=len(events)
    for x in range(len(t)):
        ns=t[x]; b=bid[x]; a=ask[x]
        if not (np.isfinite(b) and np.isfinite(a) and a>=b>0): continue
        if ns<last[0]:raise ValueError("out-of-order exact ticks")
        last[0]=ns;last[1]=b;last[2]=a
        hour=ns//3600000000000
        epochsecs=ns//1000000000
        wd=(epochsecs//86400+3)%7
        h=hour%24;minute=(epochsecs//60)%60
        k=0
        while k<an[0]:
            j=active[k]
            side=-original_dir[j]
            px=b if side==1 else a
            stop=entryprice[j]-side*20.
            tp=entryprice[j]+side*10.
            hit_sl=px<=stop if side==1 else px>=stop
            hit_tp=px>=tp if side==1 else px<=tp
            expired=hour>=entryns[j]//3600000000000+12
            friday=wd==4 and h==19 and minute>=59
            if hit_sl or hit_tp or expired or friday:
                exns[j]=ns;exprice[j]=px
                exitreason[j]=2 if hit_sl else (1 if hit_tp else (4 if friday else 3))
                an[0]-=1
                active[k]=active[an[0]]
            else:k+=1
        while ptr[0]<n and events[ptr[0]]<=ns:
            j=ptr[0]
            ptr[0]+=1
            # The published original event timestamp must be present as actual
            # tick, except for submicrosecond CSV representation differences.
            if ns-events[j]>2_000_000:
                raise ValueError("Original original-entry tick not recovered within 2 milliseconds")
            side=-original_dir[j]
            entryns[j]=ns
            entryprice[j]=a if side==1 else b
            active[an[0]]=j
            an[0]+=1
            if an[0]>n:raise ValueError('active overflow')

def download(url,path):
    sha=hashlib.sha256();size=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with open(path,'wb') as f:
            for x in r.iter_content(1<<20):
                if x:f.write(x);sha.update(x);size+=len(x)
    if not zipfile.is_zipfile(path):raise ValueError('invalid ZIP')
    return size,sha.hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--orig',required=True)
    p.add_argument('--first',type=int,required=True)
    p.add_argument('--last',type=int,required=True)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(args.orig)
    df=df[(df.sl==10)&(df.hold_hours==12)].copy()
    df['original_order']=pd.to_datetime(df.entry_utc,utc=True)
    df=df[df.original_order.dt.year.between(args.first,args.last)].sort_values('original_order').reset_index(drop=True)
    evt=df.original_order.astype('int64').to_numpy(np.int64)
    side=np.where(df.direction=='BUY',1,-1).astype(np.int8)
    n=len(evt)
    ptr=np.zeros(1,np.int64)
    active=np.zeros(n,np.int64);an=np.zeros(1,np.int64)
    ep=np.zeros(n,np.int64);entryns=np.zeros(n,np.int64)
    entryprice=np.zeros(n,np.float64)
    exns=np.zeros(n,np.int64);exprice=np.zeros(n,np.float64);exitreason=np.zeros(n,np.int8)
    last=np.zeros(3,np.float64)
    last[0]=-1
    sources=[];rows_total=0
    for yr in range(args.first,args.last+1):
      for m in range(1,13 if yr<2026 else 11):
        mm=f"{m:02}"
        u=f"https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{yr}/{mm}/Exness_XAUUSD_Raw_Spread_{yr}_{mm}.zip"
        f=out/f"{yr}_{mm}.zip"
        size,sha=download(u,f)
        nr=0
        with zipfile.ZipFile(f) as z:
            bad=z.testzip()
            if bad:raise ValueError('CRC '+bad)
            for memb in z.namelist():
              if not memb.lower().endswith('.csv'):continue
              with z.open(memb) as fd:
                for chunk in pd.read_csv(fd,usecols=['Timestamp','Bid','Ask'],chunksize=500000):
                    utc=pd.to_datetime(chunk.Timestamp,utc=True,errors='coerce')
                    ok=utc.notna()&chunk.Bid.notna()&chunk.Ask.notna()
                    ts=utc[ok].astype('int64').to_numpy(np.int64)
                    if len(ts)==0:continue
                    if np.any(ts[1:]<ts[:-1]):raise ValueError('unordered source')
                    process(ts,chunk.Bid[ok].to_numpy(np.float64),
                            chunk.Ask[ok].to_numpy(np.float64),evt,side,ptr,active,an,
                            ep,entryns,entryprice,exns,exprice,exitreason,last)
                    nr+=len(ts);rows_total+=len(ts)
        f.unlink(missing_ok=True)
        sources.append({'source':u,'SHA256':sha,'size_bytes':size,'ticks':nr})
        print('MONTH',yr,mm,'SOURCE_TICKS',nr,'ENTRY_REPRODUCED',int(ptr[0]),'ACTIVE',int(an[0]),flush=True)
    if int(ptr[0])!=n:raise ValueError('Not all original entry events found')
    for k in range(int(an[0])):
        j=int(active[k])
        exns[j]=int(last[0])
        exprice[j]=float(last[1] if -side[j]==1 else last[2])
        exitreason[j]=5
    r=df.copy()
    r['reverse_direction']=np.where(side==1,'SELL','BUY')
    r['reverse_entry_utc']=pd.to_datetime(entryns,unit='ns',utc=True).astype(str)
    r['reverse_exit_utc']=pd.to_datetime(exns,unit='ns',utc=True).astype(str)
    r['reverse_entry']=entryprice
    r['reverse_exit']=exprice
    r['reverse_exit_reason']=[{1:'TP',2:'SL',3:'TIME',4:'FRIDAY',5:'PARTITION_END'}.get(int(k),'UNKNOWN') for k in exitreason]
    r['reverse_pnl_gross']=-side*(exprice-entryprice)
    r['reverse_net_001lot']=r.reverse_pnl_gross-.07-.15
    r['original_exit_reason']=r.reason
    r['original_net_001lot']=r.net_001lot
    r.to_csv(out/'ORIGINAL_519_PAIRED_REVERSED_SL20_TP10_EXACT_TICK.csv',index=False)
    ct=pd.crosstab(r.original_exit_reason,r.reverse_exit_reason)
    ct.to_csv(out/'ORIGINAL_EXIT_VERSUS_REVERSED_EXIT_CROSSTAB.csv')
    summary=dict(year_start=args.first,year_end=args.last,n_original_12H_trades=n,actual_tick_rows=rows_total,
        original_tp=int((r.original_exit_reason=='TP').sum()),original_sl=int((r.original_exit_reason=='SL').sum()),
        reverse_tp=int((r.reverse_exit_reason=='TP').sum()),reverse_sl=int((r.reverse_exit_reason=='SL').sum()),
        reverse_time=int((r.reverse_exit_reason=='TIME').sum()),
        reverse_friday=int((r.reverse_exit_reason=='FRIDAY').sum()),
        original_net=float(r.original_net_001lot.sum()),reverse_net=float(r.reverse_net_001lot.sum()),
        reverse_trade_win=int((r.reverse_net_001lot>0).sum()),reverse_trade_loss=int((r.reverse_net_001lot<0).sum()),
        note='Fixed exact original entry timestamps, each reversed candidate independently tracked, may overlap; see independent one-position run for executable EA behavior.',
        archive_provenance=sources)
    (out/'REVERSED_PAIRED_519_SUMMARY.json').write_text(json.dumps(summary,indent=2))
    print('FINAL_PAIRED_INVERSION',json.dumps({k:v for k,v in summary.items() if k!='archive_provenance'}),flush=True)
if __name__=='__main__':main()
