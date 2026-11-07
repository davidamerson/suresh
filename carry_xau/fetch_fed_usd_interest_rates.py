"""Retrieve public DAILY USD overnight secured rate SOFR, optionally other
Fed rate benchmarks, as input for a hypothetical institutional gold carry model.
No rate data fabricated. Date stamped and SHA-256 archived."""
from pathlib import Path
from io import BytesIO
import argparse, hashlib,json,requests,pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def fetch_series(s, series):
    urls=[
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}",
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?cosd=2020-01-01&coed=2026-10-30&id={series}"
    ]
    errs=[]
    for u in urls:
        try:
            resp=s.get(u,timeout=120);resp.raise_for_status()
            b=resp.content
            df=pd.read_csv(BytesIO(b))
            if len(df)<1000 and series=='SOFR':raise RuntimeError('too few rows')
            df.columns=[str(c).strip() for c in df.columns]
            date_col=next(c for c in df.columns if c.upper() in ('DATE','OBSERVATION_DATE'))
            val_col=series if series in df.columns else next(c for c in df.columns if c != date_col)
            v=pd.DataFrame(dict(date=pd.to_datetime(df[date_col]),rate_pct=pd.to_numeric(df[val_col],errors='coerce')))
            v=v[v.date.between('2020-01-01','2026-10-30')].dropna().sort_values('date')
            if len(v)<1000 and series=='SOFR':raise RuntimeError('too few filtered rate rows')
            return v,dict(source=u,sha256=hashlib.sha256(b).hexdigest(),rows=len(v),min_date=str(v.date.min()),max_date=str(v.date.max()))
        except Exception as e:errs.append(str(e))
    raise RuntimeError(series+': '+repr(errs))

def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    s=requests.Session()
    retry=Retry(total=2,backoff_factor=1,status_forcelist=[429,500,502,503,504])
    s.mount('https://',HTTPAdapter(max_retries=retry))
    meta={}
    for series in ('SOFR','DFF','DGS3MO'):
        try:
            v,m=fetch_series(s,series)
            v.to_csv(out/f"{series}_2020_2026.csv",index=False)
            meta[series]=m
            print('SOURCE_DOWNLOADED',series,json.dumps(m),flush=True)
        except Exception as e:
            meta[series]={'error':str(e)}
            print('SOURCE_FAILURE',series,str(e),flush=True)
    (out/'funding_source_provenance.json').write_text(json.dumps(meta,indent=2))
    if 'SOFR' not in meta or 'sha256' not in meta['SOFR']:raise RuntimeError('SOFR failed')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='results/gold_carry');main(p.parse_args().out)
