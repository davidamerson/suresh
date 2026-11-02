import argparse
from pathlib import Path
import ph1_remote_backtest as b

b.CONFIGS=[("BASELINE_NOWITHDRAW",0,0,0,0,1,0)]

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--year',type=int,required=True);ap.add_argument('--outdir',required=True);a=ap.parse_args()
    months=list(range(1,13)) if a.year==2025 else list(range(1,11))
    b.run_period(a.year,months,Path(a.outdir))
