import argparse
from pathlib import Path
import ph1_remote_backtest as b

# For these baseline configs danger_mode=0, so convex_kind is otherwise unused.
# The risk-cap workflow injects logic that interprets convex_kind >= 10 as a USD basket liquidation stop.
# friday_mode 1 = no new Friday baskets. Modes 4 and 7 are injected by workflow.
b.CONFIGS = [
    ("FRI_CAP25",    1, 0, 0, 25, 1, 1),
    ("FRI_CAP50",    1, 0, 0, 50, 1, 1),
    ("FRI_CAP75",    1, 0, 0, 75, 1, 1),
    ("FRI_CAP100",   1, 0, 0,100, 1, 1),
    ("FRI_CAP150",   1, 0, 0,150, 1, 1),
    ("FRI_CAP200",   1, 0, 0,200, 1, 1),
    ("NOTHUF_CAP25", 4, 0, 0, 25, 1, 1),
    ("NOTHUF_CAP50", 4, 0, 0, 50, 1, 1),
    ("NOTHUF_CAP75", 4, 0, 0, 75, 1, 1),
    ("NOTHUF_CAP100",4, 0, 0,100, 1, 1),
    ("MONTUE_CAP25", 7, 0, 0, 25, 1, 1),
    ("MONTUE_CAP50", 7, 0, 0, 50, 1, 1),
    ("MONTUE_CAP75", 7, 0, 0, 75, 1, 1),
    ("MONTUE_CAP100",7, 0, 0,100, 1, 1),
]

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',required=True)
    a=ap.parse_args()
    months=list(range(1,13)) if a.year==2025 else list(range(1,11))
    b.run_period(a.year, months, Path(a.outdir))
