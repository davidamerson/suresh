import argparse
from pathlib import Path
import ph1_remote_backtest as b

b.CONFIGS = [
    ("BASE_W10",            0,0,0,0,1,1),
    ("FRI_NO_NEW_W10",      1,0,0,0,1,1),
    ("D3_CONVEX_C2_FRI",    1,3,2,0,2,1),
    ("D4_CONVEX_C2_FRI",    1,4,2,0,2,1),
    ("D5_CONVEX_C2_FRI",    1,5,2,0,2,1),
    ("D6_CONVEX_C2_FRI",    1,6,2,0,2,1),
]

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--year',type=int,required=True);ap.add_argument('--outdir',required=True);a=ap.parse_args()
    months=list(range(1,13)) if a.year==2025 else list(range(1,11))
    b.run_period(a.year,months,Path(a.outdir))
