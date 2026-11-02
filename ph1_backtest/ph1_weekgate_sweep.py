import argparse
from pathlib import Path
import ph1_remote_backtest as b

# Reuse the exact same engine; only entry-week gating/configurations change.
# friday_mode: 0=current; 1=no new Friday; 2=no new Fri + Thu>=18 UTC; 3=no new Fri + Thu>=12 UTC.
b.CONFIGS = [
    ("BASE_W10",               0, 0, 0, 0, 1, 1),
    ("BASE_FRI",               1, 0, 0, 0, 1, 1),
    ("BASE_THU18",             2, 0, 0, 0, 1, 1),
    ("BASE_THU12",             3, 0, 0, 0, 1, 1),
    ("D4_FRI",                 1, 4, 2, 0, 2, 1),
    ("D4_THU18",               2, 4, 2, 0, 2, 1),
    ("D4_THU12",               3, 4, 2, 0, 2, 1),
    ("D5_FRI",                 1, 5, 2, 0, 2, 1),
    ("D5_THU18",               2, 5, 2, 0, 2, 1),
    ("D5_THU12",               3, 5, 2, 0, 2, 1),
    ("D3_FRI",                 1, 3, 2, 0, 2, 1),
    ("D3_THU12",               3, 3, 2, 0, 2, 1),
]

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',required=True)
    a=ap.parse_args()
    months=list(range(1,13)) if a.year==2025 else list(range(1,11))
    b.run_period(a.year, months, Path(a.outdir))
