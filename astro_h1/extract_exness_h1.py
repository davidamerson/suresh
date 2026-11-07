"""Build causal UTC H1 Bid candles from real Exness XAUUSD Raw Spread 2020-Jan through 2026-Oct.
No sampling. Streaming ZIP/CSV, sorted nanosecond quotes; monthly ZIP hashes.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd,requests
from numba import njit

@njit
def tick_update(t,b,a,s,arr):
    for k in range(len(t)):
        h=t[k]//3600000000000
        if h<0 or not np.isfinite(b[k]) or not np.isfinite(a[k]) or a[k]<b[k] or b[k]<=0.:continue
        if s[0]<0:
            s[0]=h;s[1]=t[k];s[2]=t[k];s[3]=b[k];s[4]=b[k]
            s[5]=b[k];s[6]=b[k];s[7]=a[k];s[8]=a[k];s[9]=1.
        elif h>s[0]:
            idx=int(s[10])
            if idx>=arr.shape[0]:raise ValueError("More H1 candles than allocated")
            for j in range(10):arr[idx,j]=s[j]
            s[10]+=1.
            s[0]=h;s[1]=t[k];s[2]=t[k];s[3]=b[k];s[4]=b[k]
            s[5]=b[k];s[6]=b[k];s[7]=a[k];s[8]=a[k];s[9]=1.
        elif h==s[0]:
            s[2]=t[k]
            if b[k]>s[4]:s[4]=b[k]
            if b[k]<s[5]:s[5]=b[k]
            s[6]=b[k];s[8]=a[k];s[9]+=1.
        else:raise ValueError("Strictly ordered source required; hour moved backward")

def download(url,p):
    hs=hashlib.sha256();size=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with p.open("wb") as f:
            for x in r.iter_content(chunk_size=1<<20):
                if x:f.write(x);hs.update(x);size+=len(x)
    if not zipfile.is_zipfile(p):raise RuntimeError("Not ZIP: "+url)
    return size,hs.hexdigest()

def main(out,first=2020,last=2026):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    s=np.zeros(11,dtype=np.float64);s[0]=-1.
    # float64 nanosecond integers up to 1.8e18 lose 1-100 ns, but hourly
    # and minute offset exact to within <0.001 seconds; store as nanoseconds
    # rounded precision once, and no intrahour forecasting uses nanosecond times.
    arr=np.empty((65000,10),dtype=np.float64)
    total=0;provenance=[];last_timestamp=-1
    for y in range(first,last+1):
        months=range(1,13) if y<2026 else range(1,11)
        for m in months:
            mm=f"{m:02}"
            url=f"https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{y}/{mm}/Exness_XAUUSD_Raw_Spread_{y}_{mm}.zip"
            zip_path=out/f"{y}_{mm}.zip"
            print("DOWNLOAD",y,mm,url,flush=True)
            nbytes,sha=download(url,zip_path)
            count=0;mn=None;mx=None
            with zipfile.ZipFile(zip_path) as z:
                bad=z.testzip()
                if bad:raise RuntimeError("Archive CRC failure "+bad)
                for name in z.namelist():
                    if not name.lower().endswith(".csv"):continue
                    with z.open(name) as fd:
                        for df in pd.read_csv(fd,usecols=["Timestamp","Bid","Ask"],chunksize=500000):
                            tstamp=pd.to_datetime(df.Timestamp,utc=True,errors="coerce")
                            good=tstamp.notna()&df.Bid.notna()&df.Ask.notna()
                            t=tstamp[good].astype("int64").to_numpy(dtype=np.int64)
                            if len(t)==0:continue
                            if np.any(t[1:]<t[:-1]) or t[0]<last_timestamp:raise ValueError("Nonmonotone archive "+url)
                            last_timestamp=int(t[-1])
                            bids=df.Bid[good].to_numpy(np.float64)
                            asks=df.Ask[good].to_numpy(np.float64)
                            tick_update(t,bids,asks,s,arr)
                            count+=len(t);total+=len(t)
                            if mn is None:mn=int(t[0])
                            mx=int(t[-1])
            zip_path.unlink(missing_ok=True)
            provenance.append(dict(year=y,month=m,url=url,archive_sha256=sha,
                                   zip_bytes=nbytes,rows=count,
                                   first_utc=str(pd.Timestamp(mn,unit="ns",tz="UTC")) if mn else "",
                                   last_utc=str(pd.Timestamp(mx,unit="ns",tz="UTC")) if mx else ""))
            print("MONTH_VERIFIED",y,mm,"rows",count,"total",total,"candles",int(s[10]),flush=True)
    if s[0]>=0:
        idx=int(s[10]);arr[idx,:10]=s[:10];s[10]+=1
    col=["hour_epoch","first_quote_ns","last_quote_ns","bid_open","bid_high","bid_low","bid_close","ask_open","ask_close","tick_count"]
    result=pd.DataFrame(arr[:int(s[10]),:],columns=col)
    dt=pd.to_datetime(result.hour_epoch.astype("int64"),unit="h",utc=True)
    day=dt.dt.dayofweek
    first_delay=(result.first_quote_ns-result.hour_epoch*3.6e12)/1e9
    end_delay=((result.hour_epoch+1)*3.6e12-result.last_quote_ns)/1e9
    result["hour_utc"]=dt.astype(str)
    result["weekday"]=day
    result["complete"]=(day<=4)&(result.tick_count>=10)&(first_delay.between(-1,600))&(end_delay.between(0,600))
    result["body_gold_usd"]=result.bid_close-result.bid_open
    result["range_gold_usd"]=result.bid_high-result.bid_low
    result["open_spread_gold_usd"]=result.ask_open-result.bid_open
    result["close_spread_gold_usd"]=result.ask_close-result.bid_close
    result.to_csv(out/"all_h1_bid_candles.csv",index=False)
    market=result[result.complete]
    market.to_csv(out/"complete_monday_friday_h1_candles.csv",index=False)
    meta=dict(total_ticks=total,raw_H1_count=len(result),qualified_MonFri_H1_count=len(market),
              coverage_start=str(dt.iloc[0]),coverage_end=str(dt.iloc[-1]),
              total_qualified_positive=int((market.body_gold_usd>0).sum()),
              all_source_hashes=provenance,
              definition="UTC H1 BID first/last real quotes. Strict >=10 ticks, quote starts within 10m, last within 10m of hour end, Mon-Fri UTC; exclude partial weekend/holidays. Not the Mid chart.",
              next_phase="At hour first executable quote (before close) compute astronomical features; no future close used for entries")
    (out/"provenance.json").write_text(json.dumps(meta,indent=2))
    print("CANDLE_EXTRACTION_FINAL",json.dumps({k:v for k,v in meta.items() if k!="all_source_hashes"}),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="results/astro_h1")
    a=p.parse_args();main(a.out)
