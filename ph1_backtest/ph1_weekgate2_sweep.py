import argparse
from pathlib import Path
import ph1_remote_backtest as b

# Extended friday_mode is injected into the engine at workflow runtime:
# 4=no new Thu/Fri; 5=no new Wed>=18 or Thu/Fri; 6=no new Wed>=12 or Thu/Fri; 7=Mon-Tue new entries only.
b.CONFIGS = [
    ("BASE_NO_THU_FRI", 4, 0, 0, 0, 1, 1),
    ("BASE_WED18",      5, 0, 0, 0, 1, 1),
    ("BASE_WED12",      6, 0, 0, 0, 1, 1),
    ("BASE_MON_TUE",    7, 0, 0, 0, 1, 1),
    ("D5_NO_THU_FRI",   4, 5, 2, 0, 2, 1),
    ("D5_WED18",        5, 5, 2, 0, 2, 1),
    ("D5_WED12",        6, 5, 2, 0, 2, 1),
    ("D5_MON_TUE",      7, 5, 2, 0, 2, 1),
    ("D4A_NO_THU_FRI",  4, 4, 2, 1, 2, 1),
    ("D4A_WED18",       5, 4, 2, 1, 2, 1),
    ("D4A_WED12",       6, 4, 2, 1, 2, 1),
    ("D4A_MON_TUE",     7, 4, 2, 1, 2, 1),
]

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',required=True)
    a=ap.parse_args()
    months=list(range(1,13)) if a.year==2025 else list(range(1,11))
    b.run_period(a.year, months, Path(a.outdir))
