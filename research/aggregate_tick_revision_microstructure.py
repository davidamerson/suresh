"""Reproducible, no-lookahead Exness XAUUSD Raw Spread full-history M1 quote features.

Downloads each source archive directly in GitHub Actions and saves 1-minute actual
Bid/Ask OHLC and exact first-tick executable quotes. Minute-level first-passage
analysis and candidate sampling are done independently after both yearly runs.
This preserves every raw tick's contribution to minute extrema and enables an
audited second pass on any within-minute outcome ambiguity.

2025: Jan-Dec inclusive. 2026: Jan 1-Oct 29 inclusive (agreed common cutoff).
"""
import argparse,hashlib,json,zipfile,datetime,os,time
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from numba import njit

NAN=float('nan')
MIN_NS=60_000_000_000
ORIGIN=lambda y: pd.Timestamp(f'{y}-01-01T00:00:00Z').value
STOP_2026=pd.Timestamp('2026-10-29T23:59:59.999999999Z').value

@njit
def aggreg(ts,bid,ask,origin, bars,counts, spmin,spmax,up,down,flat,up_amp,down_amp,sq_move,spread_widen):
    for k in range(len(ts)):
        t=ts[k];b=bid[k];a=ask[k]
        if not(np.isfinite(b) and np.isfinite(a) and b>0 and a>=b):
            continue
        i=(t-origin)//MIN_NS
        if i<0 or i>=len(bars):continue
        s=a-b
        if counts[i]==0:
            # b_o,b_h,b_l,b_c, a_o,a_h,a_l,a_c, first tick's seconds,
            # last tick's seconds
            bars[i,0]=b;bars[i,1]=b;bars[i,2]=b;bars[i,3]=b
            bars[i,4]=a;bars[i,5]=a;bars[i,6]=a;bars[i,7]=a
            bars[i,8]=(t-origin-i*MIN_NS)/1e9
            bars[i,9]=(t-origin-i*MIN_NS)/1e9
            spmin[i]=s;spmax[i]=s
        else:
            prev_bid=bars[i,3]
            prev_spread=bars[i,7]-bars[i,3]
            delta=b-prev_bid
            if delta>0:
                up[i]+=1
                up_amp[i]+=delta
            elif delta<0:
                down[i]+=1
                down_amp[i]-=delta
            else:
                flat[i]+=1
            sq_move[i]+=delta*delta
            if s>prev_spread:
                spread_widen[i]+=1
            if b>bars[i,1]:bars[i,1]=b
            if b<bars[i,2]:bars[i,2]=b
            bars[i,3]=b
            if a>bars[i,5]:bars[i,5]=a
            if a<bars[i,6]:bars[i,6]=a
            bars[i,7]=a
            bars[i,9]=(t-origin-i*MIN_NS)/1e9
            if s<spmin[i]:spmin[i]=s
            if s>spmax[i]:spmax[i]=s
        counts[i]+=1

def get(url,path):
    sha=hashlib.sha256();size=0
    with requests.get(url,stream=True,timeout=(30,300)) as response:
        response.raise_for_status()
        with open(path,'wb') as f:
            for c in response.iter_content(1024*1024):
                if c:
                    size+=len(c);sha.update(c);f.write(c)
    return size,sha.hexdigest()

def main(year,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    origin=ORIGIN(year)
    stop=pd.Timestamp(f'{year}-12-31T23:59:59.999999999Z').value if year==2025 else STOP_2026
    nmins=int((stop-origin)//MIN_NS)+1
    bars=np.full((nmins,10),np.nan,dtype=np.float64)
    counts=np.zeros(nmins,dtype=np.int32)
    spmin=np.full(nmins,np.nan,dtype=np.float64)
    spmax=np.full(nmins,np.nan,dtype=np.float64)
    up=np.zeros(nmins,dtype=np.int32)
    down=np.zeros(nmins,dtype=np.int32)
    flat=np.zeros(nmins,dtype=np.int32)
    up_amp=np.zeros(nmins,dtype=np.float64)
    down_amp=np.zeros(nmins,dtype=np.float64)
    sq_move=np.zeros(nmins,dtype=np.float64)
    spread_widen=np.zeros(nmins,dtype=np.int32)
    provenance=[]
    rows=0
    invalid=0
    for m in range(1,13 if year==2025 else 11):
        mm=f'{m:02d}'
        name=f'Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip'
        url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/{name}'
        path=out/name
        print('DOWNLOAD',url,flush=True)
        nbytes,sha=get(url,path)
        used=0
        with zipfile.ZipFile(path) as z:
            for member in z.namelist():
                if not member.endswith('.csv'):continue
                with z.open(member) as f:
                    for chunk in pd.read_csv(f,usecols=['Timestamp','Bid','Ask'],chunksize=500000):
                        parsed=pd.to_datetime(chunk['Timestamp'],utc=True,errors='coerce')
                        mask=parsed.notna()&chunk['Bid'].notna()&chunk['Ask'].notna()
                        if year==2026 and m==10:
                            mask=mask & (parsed<=pd.Timestamp(STOP_2026,unit='ns',tz='UTC'))
                        invalid+=int(len(chunk)-mask.sum())
                        if not bool(mask.all()):
                            chunk=chunk.loc[mask];parsed=parsed.loc[mask]
                        if len(chunk)==0:continue
                        ts=parsed.astype('int64').to_numpy(np.int64)
                        bd=chunk['Bid'].to_numpy(np.float64)
                        ak=chunk['Ask'].to_numpy(np.float64)
                        aggreg(ts,bd,ak,origin,bars,counts,spmin,spmax,up,down,flat,up_amp,down_amp,sq_move,spread_widen)
                        rows+=len(chunk);used+=len(chunk)
        provenance.append(dict(month=m,url=url,sha256=sha,archive_bytes=nbytes,parsed_quotes=used))
        path.unlink(missing_ok=True)
        print(f'COMPLETE {year}-{mm}: ticks={used:,}; valid_minutes={np.count_nonzero(counts):,}',flush=True)
    bar_minute_start_ns=origin+np.arange(nmins,dtype=np.int64)*MIN_NS
    np.savez_compressed(out/'tick_microstructure_1min.npz',
                        bar_minute_start_ns=bar_minute_start_ns,quote_counts=counts,
                        up_quote_revisions=up,down_quote_revisions=down,
                        flat_quote_revisions=flat,positive_bid_movement_sum=up_amp,
                        negative_bid_movement_sum=down_amp,
                        bid_move_squared_sum=sq_move,spread_widen_count=spread_widen)
    n5=int(np.sum((counts>0)&(np.arange(nmins)%5==0)))
    meta=dict(year=year,first_utc='2025-01-01' if year==2025 else '2026-01-01',
              last_utc='2025-12-31' if year==2025 else '2026-10-29',
              input_archive_files=provenance,valid_quote_rows=rows,
              filtered_invalid_or_out_of_period_rows=invalid,
              minute_count=nmins,nonempty_minutes=int(np.count_nonzero(counts)),
              five_min_grid_candidate_times=n5,
              source='Original Exness public XAUUSD Raw Spread Bid/Ask zipped tick CSVs',
              OHLC_columns=['Bid_open','Bid_high','Bid_low','Bid_close',
                            'Ask_open','Ask_high','Ask_low','Ask_close',
                            'first_tick_second_in_minute','last_tick_second_in_minute'],
              note='No interpolated quotes, market gaps are NaN. All Bid and Ask OHLC computed tick-by-tick.',
              input_check='SHA256 of each archive provided.')
    meta['microstructure_measurement']='Within-minute Bid quote revision counts up/down/flat, amplitude and sum of squared Bid changes; widening dealer spreads. NOT traded volume or signed order flow. Across-minute first update is not assigned a sign.'
    (out/'microstructure_provenance.json').write_text(json.dumps(meta,indent=2))
    print('FINAL',json.dumps({k:v for k,v in meta.items() if k!='input_archive_files'}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--year',type=int,choices=[2025,2026],required=True)
    p.add_argument('--out',required=True)
    a=p.parse_args()
    main(a.year,a.out)
