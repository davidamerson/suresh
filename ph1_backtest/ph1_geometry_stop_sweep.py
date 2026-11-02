import argparse
from pathlib import Path
import ph1_remote_backtest as b

# danger_mode=3 is injected by workflow as a geometry circuit breaker:
# once both sides have expanded to `danger_depth`, liquidate whole basket and stop the day.
b.CONFIGS = [
    ("GSTOP1",      0, 1, 3, 0, 1, 1),
    ("GSTOP2",      0, 2, 3, 0, 1, 1),
    ("GSTOP3",      0, 3, 3, 0, 1, 1),
    ("GSTOP4",      0, 4, 3, 0, 1, 1),
    ("GSTOP5",      0, 5, 3, 0, 1, 1),
    ("GSTOP6",      0, 6, 3, 0, 1, 1),
    ("GSTOP8",      0, 8, 3, 0, 1, 1),
    ("GSTOP10",     0,10, 3, 0, 1, 1),
    ("FRI_GSTOP2",  1, 2, 3, 0, 1, 1),
    ("FRI_GSTOP3",  1, 3, 3, 0, 1, 1),
    ("FRI_GSTOP4",  1, 4, 3, 0, 1, 1),
    ("FRI_GSTOP5",  1, 5, 3, 0, 1, 1),
    ("THUF_GSTOP2", 4, 2, 3, 0, 1, 1),
    ("THUF_GSTOP3", 4, 3, 3, 0, 1, 1),
    ("THUF_GSTOP4", 4, 4, 3, 0, 1, 1),
    ("THUF_GSTOP5", 4, 5, 3, 0, 1, 1),
]

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--year',type=int,required=True);ap.add_argument('--outdir',required=True);a=ap.parse_args()
    months=list(range(1,13)) if a.year==2025 else list(range(1,11))
    b.run_period(a.year,months,Path(a.outdir))
