# XAUUSD major support/resistance: selected strongest 1:1 and 2:1 breakout stress test

**Verified 5 November 2026**. GitHub Actions **all 7 annual jobs success**: https://github.com/davidamerson/suresh/actions/runs/41973026963

This is a sensitivity analysis of configurations picked **after scanning 40 strategies**. It is *not* an independent out-of-sample discovery.

## Rules held constant
At Sydney 08:00, Tokyo 09:00, London 08:00 and New York 08:00 local sessions (historical timezone/DST), wait for first complete H1, freeze nearest previously known major resistance above last Bid and major support below last Bid. Level candidates: last **completed UTC week** H/L and most recently confirmed **2-left/2-right completed D1 fractal swing** H/L. First subsequent genuine observed Bid crossing of resistance from below triggers BUY at Ask; support from above triggers SELL at Bid. One first-cross opportunity per local opening. 0.01 lot=1 oz, archived Exness raw Bid/Ask spread, $0.07 round-trip 0.01 lot commission modelled, no withdrawals, one independent initial $1,000 account each calendar year, TP limit capped at target and SL at first executable quote (possible gap losses), no artificial lookahead.

Selected strategies: (A) BUY/SELL both **TP90/SL90 user diagram pips = Gold $9.00/$9.00**, (B) both **TP100/SL50 = Gold $10.00/$5.00**. Diagram pip Gold $0.10; different from formal broker pip. Stress additive per-side unfavorable execution price $0.05 and $0.10 for entries AND exits, including possible change in TP/SL hit rates. This is a model, not a live execution guarantee.

## Combined results across SEVEN separately restarted annual $1,000 simulations

| Setup | Extra adverse slippage per side | Closed trades | TP | SL | Win % | Sum annual economic P/L | Positive annual years |
|---|---:|---:|---:|---:|---:|---:|---:|
| Breakout TP90/SL90 | Gold $0.00 | 1920 | 1099 | 821 | 57.24% | $2313.793 | 7/7 |
| Breakout TP90/SL90 | Gold $0.05 | 1920 | 1093 | 827 | 56.93% | $2201.984 | 7/7 |
| Breakout TP90/SL90 | Gold $0.10 | 1920 | 1082 | 838 | 56.35% | $2002.543 | 7/7 |
| Breakout TP100/SL50 | Gold $0.00 | 1923 | 757 | 1166 | 39.37% | $1544.485 | 7/7 |
| Breakout TP100/SL50 | Gold $0.05 | 1923 | 751 | 1172 | 39.05% | $1450.569 | 7/7 |
| Breakout TP100/SL50 | Gold $0.10 | 1923 | 729 | 1194 | 37.91% | $1123.305 | 6/7 |

The normal-case original 40-model full replay is **exactly reproduced** for both selected baseline strategies (1,099 TP, 1,920 closed, +$2,313.793 annual P/L sum; and 757 TP, 1,923 closed, +$1,544.485). Consequently the stress paths are comparable to prior models with only additional unfavorable execution modeled.

## Per year EQ TP90/SL90 P/L including floating marks

| Year | Base $0 | Stress $0.05/side | Stress $0.10/side |
|---|---:|---:|---:|
| 2020* | $78.523 | $77.772 | $74.867 |
| 2021 | $151.569 | $132.773 | $133.336 |
| 2022 | $517.703 | $517.345 | $500.325 |
| 2023 | $752.986 | $735.710 | $644.718 |
| 2024 | $191.681 | $192.089 | $172.636 |
| 2025 | $354.742 | $353.792 | $353.041 |
| 2026* | $266.589 | $192.503 | $123.620 |

## Per year 2:1 TP100/SL50 P/L including floating marks

| Year | Base $0 | Stress $0.05/side | Stress $0.10/side |
|---|---:|---:|---:|
| 2020* | $115.344 | $100.156 | $100.083 |
| 2021 | $72.881 | $73.288 | $72.334 |
| 2022 | $153.452 | $153.437 | $111.404 |
| 2023 | $527.895 | $526.265 | $407.024 |
| 2024 | $73.603 | $13.492 | $-0.259 |
| 2025 | $349.743 | $335.169 | $246.101 |
| 2026* | $251.567 | $248.762 | $186.618 |

*2020 coverage Jan29 onward, 2026 through Oct29.*

## Interpretation, risk and next tests

1. Major S/R breakout is **unambiguously better on the selected backtest history** than simple first regional H1 candle High/Low breakout, given the precise level definition, session rule and cost assumptions.
2. The 1:1 TP90/SL90 strategy remains positive under both modeled slippage stress levels and in all 7 separate year tests. 2:1 TP100/SL50 remains positive under both stress levels on the aggregate; at +$0.10 per side, the 2024 annual model turns slightly negative ($-0.259).
3. Both signal definitions, S/R thresholds and TP/SL choices have been tested on the SAME 2020–26 research history. Multiple-testing bias remains despite stress survival. No untouched independent unseen future evaluation has been run; historical performance is not a trading guarantee.
4. Weekly/day structure uses UTC period boundaries, not NY-close D1; first source week in annual archive may lack prehistory. Prior week is taken from observed quote archive, not necessarily a complete historical pre-start calendar week. Multi-touch liquidity zones or retests are **not** tested. Be especially cautious with broker spread spikes, swap and market closure, dynamic margin requirements and latency; the model doesn't fully simulate all real-world costs.
5. Annual backtests restart $1,000 separately and never withdraw profit **within** each year. Values reported sum seven independently reset annual P/Ls, not the terminal balance from one compounded $1,000 account.

## Code and archived per-year audit
- Stress source: https://github.com/davidamerson/suresh/blob/h1-major-sr-40models-20261105/ph1_backtest/h1_major_sr_momentum_best2_slippage_stress.py
- Validated run: https://github.com/davidamerson/suresh/actions/runs/41973026963
- Per-year artifacts `H1-MajorSR-Momentum-Best2-Stress-YEAR` include summary.csv, individual_trades.csv, by_side_summary.csv, sessions.csv, provenance.json with monthly raw ZIP SHA256, and execution.log, typically retained for 30 days.
