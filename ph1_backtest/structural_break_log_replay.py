import argparse, json
from pathlib import Path
import pandas as pd
import numpy as np
import requests

URL='https://raw.githubusercontent.com/lightblue888/xauusd-structural-break-paper/refs/heads/main/data/v10_realticks_trades.csv'
START=1000.0; TARGET=20.0; WITHDRAW=10.0

def main(outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True)
    r=requests.get(URL,timeout=60); r.raise_for_status(); (out/'source.csv').write_bytes(r.content)
    d=pd.read_csv(out/'source.csv')
    print('COLUMNS',list(d.columns),flush=True)
    print('DTYPES',d.dtypes.astype(str).to_dict(),flush=True)
    print('HEAD',d.head(5).to_dict('records'),flush=True)
    print('ROWS',len(d),flush=True)
    # Save structural audit; a second-pass replay can use the discovered fields.
    audit={'columns':list(d.columns),'dtypes':d.dtypes.astype(str).to_dict(),'rows':len(d),'head':d.head(5).to_dict('records')}
    (out/'audit.json').write_text(json.dumps(audit,indent=2,default=str))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',required=True); a=ap.parse_args(); main(a.outdir)
