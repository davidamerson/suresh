import argparse
from pathlib import Path
import ph1_remote_backtest as b

# Corrected candidate sweep.
# Weekend new entries are blocked by the workflow injection while weekend ticks remain
# available for market/H1 continuity. 2026 is truncated to the user's original Oct-29 data.
# friday_mode: 0 original; 1 no new Friday; 2 no Fri + Thu>=18; 4 no Thu/Fri.
# danger_mode 1 = stop adding after balanced-depth danger trigger.
# danger_mode 2 = range-pause + convex outer extension + N-tick confirmation.
# convex_kind 0 = Fibonacci-like 2,3,5,8...; 1 = arithmetic 2,3,4,5...
b.CONFIGS = [
    ("BASE_W10",                  0, 0, 0, 0, 1, 1),
    ("FRI_NO_NEW_W10",            1, 0, 0, 0, 1, 1),
    ("THU18_FRI_W10",             2, 0, 0, 0, 1, 1),
    ("NO_THU_FRI_W10",            4, 0, 0, 0, 1, 1),

    ("D3_STOPADD_FRI",             1, 3, 1, 0, 1, 1),
    ("D4_STOPADD_FRI",             1, 4, 1, 0, 1, 1),
    ("D5_STOPADD_FRI",             1, 5, 1, 0, 1, 1),

    ("D3_CONVEX_C2_FRI",           1, 3, 2, 0, 2, 1),
    ("D4_CONVEX_C2_FRI",           1, 4, 2, 0, 2, 1),
    ("D5_CONVEX_C2_FRI",           1, 5, 2, 0, 2, 1),
    ("D6_CONVEX_C2_FRI",           1, 6, 2, 0, 2, 1),

    ("D3_CONVEX_C3_FRI",           1, 3, 2, 0, 3, 1),
    ("D4_CONVEX_C3_FRI",           1, 4, 2, 0, 3, 1),
    ("D5_CONVEX_C3_FRI",           1, 5, 2, 0, 3, 1),

    ("D4_ARITH_C2_FRI",            1, 4, 2, 1, 2, 1),
    ("D5_ARITH_C2_FRI",            1, 5, 2, 1, 2, 1),

    ("D4_CONVEX_C2_THU18",         2, 4, 2, 0, 2, 1),
    ("D5_CONVEX_C2_THU18",         2, 5, 2, 0, 2, 1),
    ("D4_CONVEX_C2_NO_THU_FRI",    4, 4, 2, 0, 2, 1),
    ("D5_CONVEX_C2_NO_THU_FRI",    4, 5, 2, 0, 2, 1),
]

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--year',type=int,required=True); ap.add_argument('--outdir',required=True)
    a=ap.parse_args()
    months=list(range(1,13)) if a.year==2025 else list(range(1,11))
    b.run_period(a.year, months, Path(a.outdir))
