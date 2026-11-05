# Corrected symmetric H1 first-break analysis — 40 model comparison (2020–2026)

**Date verified:** 5 November 2026. **GitHub Actions:** Equal-RR run https://github.com/davidamerson/suresh/actions/runs/41970426842 and 2:1-RR run https://github.com/davidamerson/suresh/actions/runs/41970431204 — **all 14 annual matrix jobs success**.

## Exact user-corrected rules
Each of four families holds precisely equal price TP and SL rules for the HIGH and LOW signals **within the same variant**:
- REVERSE_EQ (10 configs): High breach **SELL**, Low breach **BUY**, both TP=SL=10/10, 20/20, ..., 100/100 user diagram pips.
- REVERSE_RR2 (10 configs): High breach **SELL**, Low breach **BUY**, both TP/SL=10/5, 20/10, ..., 100/50.
- MOMENTUM_EQ (10 configs): High breach **BUY**, Low breach **SELL**, both TP=SL=10/10, ..., 100/100.
- MOMENTUM_RR2 (10 configs): High breach **BUY**, Low breach **SELL**, both TP/SL=10/5, ..., 100/50.

At Sydney 08:00, Tokyo 09:00, London 08:00 and New York 08:00 local clock market opens (historical timezones/DST), capture first **completed** H1 Bid High and Low. First later Bid tick strictly above High/below Low produces *one* trade in chosen direction, once per regional opening, without lookahead. Four regional market sessions can overlap.

User diagram pip Gold $0.10 (so TP80 Gold $8.00 and SL40 Gold $4.00, not the platform's formal pip). Fixed 0.01 lot (1 oz); **Exness Raw Spread historical Bid/Ask** archive actual spreads, model **$0.07 roundtrip commission**, no *extra* modeled slippage, TP at limit, SL at first executable quote including adverse gaps. $1,000 annual starting balance **independently reset each year**, profits **never withdrawn within each annual simulation**, no martingale/lot escalation and no Friday forced close. 2020 source starts Jan 29, 2026 ends Oct 29; 295,225,516 quotes from archive with SHA256 provenance in per-job artifacts. No broker-accurate stopout/dynamic margin nor swaps modelled. P/L below is sum of separate annual economic P/Ls, NOT one continuously funded $1,000 across seven years.

All 280 annual strategy rows and all 560 annual high-vs-low rows were parsed from 14 successful raw execution logs; no modeled margin rejections or forced equity failures. Four previously independently verified baseline outcomes matched exactly:
- REVERSE_EQ TP10SL10: 2807/6530 TP, annual P/L −1580.110
- REVERSE_RR2 TP10SL5: 1729/6530 TP, annual P/L −1404.887
- MOMENTUM_EQ TP10SL10: 3085/6530 TP, annual P/L −951.872
- MOMENTUM_RR2 TP10SL5: 2013/6530 TP, annual P/L −912.525

## 1. Reverse 1:1 (high SELL; low BUY)
| TP/SL diagram pips | Closed | TP | SL | Win % | Loss % | Combined annual model P/L | Annual-end open |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/10 | 6530 | 2807 | 3723 | 42.99% | 57.01% | $-1580.110 | 0 |
| 20/20 | 6529 | 3014 | 3515 | 46.16% | 53.84% | $-1627.091 | 1 |
| 30/30 | 6529 | 3103 | 3426 | 47.53% | 52.47% | $-1608.028 | 1 |
| 40/40 | 6529 | 3102 | 3427 | 47.51% | 52.49% | $-1950.141 | 1 |
| 50/50 | 6529 | 3150 | 3379 | 48.25% | 51.75% | $-1802.138 | 1 |
| 60/60 | 6527 | 3154 | 3373 | 48.32% | 51.68% | $-1967.714 | 3 |
| 70/70 | 6526 | 3177 | 3349 | 48.68% | 51.32% | $-1875.244 | 4 |
| 80/80 | 6525 | 3178 | 3347 | 48.70% | 51.30% | $-2045.473 | 5 |
| 90/90 | 6523 | 3192 | 3331 | 48.93% | 51.07% | $-1948.837 | 7 |
| 100/100 | 6521 | 3222 | 3299 | 49.41% | 50.59% | $-1515.321 | 9 |

## 2. Momentum 1:1 (high BUY; low SELL)
| TP/SL diagram pips | Closed | TP | SL | Win % | Loss % | Combined annual model P/L | Annual-end open |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/10 | 6530 | 3085 | 3445 | 47.24% | 52.76% | $-951.872 | 0 |
| 20/20 | 6529 | 3180 | 3349 | 48.71% | 51.29% | $-911.763 | 1 |
| 30/30 | 6529 | 3207 | 3322 | 49.12% | 50.88% | $-924.997 | 1 |
| 40/40 | 6529 | 3244 | 3285 | 49.69% | 50.31% | $-745.488 | 1 |
| 50/50 | 6529 | 3200 | 3329 | 49.01% | 50.99% | $-1254.132 | 1 |
| 60/60 | 6527 | 3237 | 3290 | 49.59% | 50.41% | $-960.741 | 3 |
| 70/70 | 6527 | 3246 | 3281 | 49.73% | 50.27% | $-900.780 | 3 |
| 80/80 | 6525 | 3234 | 3291 | 49.56% | 50.44% | $-1172.363 | 5 |
| 90/90 | 6525 | 3230 | 3295 | 49.50% | 50.50% | $-1302.652 | 5 |
| 100/100 | 6520 | 3217 | 3303 | 49.34% | 50.66% | $-1603.091 | 10 |

## 3. Reverse 2:1 (high SELL; low BUY)
| TP/SL diagram pips | Closed | TP | SL | Win % | Loss % | Combined annual model P/L | Annual-end open |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/5 | 6530 | 1729 | 4801 | 26.48% | 73.52% | $-1404.887 | 0 |
| 20/10 | 6530 | 1833 | 4697 | 28.07% | 71.93% | $-1729.857 | 0 |
| 30/15 | 6529 | 1941 | 4588 | 29.73% | 70.27% | $-1742.312 | 1 |
| 40/20 | 6529 | 1974 | 4555 | 30.23% | 69.77% | $-1884.868 | 1 |
| 50/25 | 6529 | 2009 | 4520 | 30.77% | 69.23% | $-1943.378 | 1 |
| 60/30 | 6528 | 2042 | 4486 | 31.28% | 68.72% | $-1903.672 | 2 |
| 70/35 | 6527 | 2059 | 4468 | 31.55% | 68.45% | $-1934.226 | 3 |
| 80/40 | 6527 | 2072 | 4455 | 31.75% | 68.25% | $-1955.965 | 3 |
| 90/45 | 6526 | 2109 | 4417 | 32.32% | 67.68% | $-1604.143 | 4 |
| 100/50 | 6526 | 2109 | 4417 | 32.32% | 67.68% | $-1727.648 | 4 |

## 4. Momentum 2:1 (high BUY; low SELL)
| TP/SL diagram pips | Closed | TP | SL | Win % | Loss % | Combined annual model P/L | Annual-end open |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/5 | 6530 | 2013 | 4517 | 30.83% | 69.17% | $-912.525 | 0 |
| 20/10 | 6530 | 2087 | 4443 | 31.96% | 68.04% | $-886.120 | 0 |
| 30/15 | 6529 | 2124 | 4405 | 32.53% | 67.47% | $-847.863 | 1 |
| 40/20 | 6529 | 2145 | 4384 | 32.85% | 67.15% | $-798.051 | 1 |
| 50/25 | 6529 | 2135 | 4394 | 32.70% | 67.30% | $-928.414 | 1 |
| 60/30 | 6529 | 2145 | 4384 | 32.85% | 67.15% | $-906.636 | 1 |
| 70/35 | 6529 | 2144 | 4385 | 32.84% | 67.16% | $-966.253 | 1 |
| 80/40 | 6528 | 2195 | 4333 | 33.62% | 66.38% | $-404.810 | 2 |
| 90/45 | 6528 | 2143 | 4385 | 32.83% | 67.17% | $-1106.370 | 2 |
| 100/50 | 6526 | 2131 | 4395 | 32.65% | 67.35% | $-1325.024 | 4 |


## Four-family results, ranking and interpretation

| Family | Least negative 7-year sum model P/L | Win % of that model | TP/SL | Worst annual model drawdown of that model |
|---|---:|---:|---:|---:|
| REVERSE_EQ | $-1515.321 | 49.41% | 100/100 | $760.116 |
| MOMENTUM_EQ | $-745.488 | 49.69% | 40/40 | $281.340 |
| REVERSE_RR2 | $-1404.887 | 26.48% | 10/5 | $430.977 |
| MOMENTUM_RR2 | $-404.810 | 33.62% | 80/40 | $402.277 |

**Best by net P/L of all 40 models:** MOMENTUM_RR2 TP80SL40, $-404.810, 33.62% TP win rate, 2195 wins/4333 losses on 6528 closed positions (two unresolved at annual endpoints across all years). **None of the full two-direction, cost-adjusted models is profitable on combined annual simulated P/L.** Highest raw win rate across the 40 belongs to MOMENTUM_EQ TP70/SL70, 49.73%, but still negative $-900.780.

## Useful post-hoc breakout-side finding — NOT an independently validated strategy

In the least-negative two-direction MOMENTUM_RR2 TP80/SL40 run:
- **HIGH breach -> BUY**: 3376 closed, 1175 wins, 34.80% success, **+$271.738** seven-year sum of annual **realized only** P/L.
- **LOW breach -> SELL**: 3152 closed, 1020 wins, 32.36% success, **$-676.144** seven-year sum of annual realized P/L.
- Combined seven-year sum **$-404.810 economic** after accounting for $-0.404 year-end floating P/L. Two high-break trades unresolved at annual endpoints.
- This BUY-only subgroup was selected **after evaluating 40 models and both breakout sides**: its positive result is *in-sample and multiple-testing exposed*, not a verified forward profitable edge. A separate high-only independent replay under adverse slippage is pending/being run and must be considered before further judgment.

## Best full-model TP80/SL40 annual economic P/L

| Year | Opened | Closed | TP | SL | Win % | Economic annual P/L | Unclosed |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020* | 903 | 902 | 286 | 616 | 31.71% | $-272.393 | 1 |
| 2021 | 964 | 963 | 303 | 660 | 31.46% | $-300.974 | 1 |
| 2022 | 967 | 967 | 343 | 624 | 35.47% | $165.002 | 0 |
| 2023 | 963 | 963 | 319 | 644 | 33.13% | $-118.148 | 0 |
| 2024 | 969 | 969 | 328 | 641 | 33.85% | $-30.946 | 0 |
| 2025 | 959 | 959 | 348 | 611 | 36.29% | $256.787 | 0 |
| 2026* | 805 | 805 | 268 | 537 | 33.29% | $-104.138 | 0 |

*partial years. Individual annual model P/L may differ drastically; a few positive years are insufficient to establish an exploitable edge.*

## Source and audit
- Repository `davidamerson/suresh`, branch `h1-reverse-vs-breakout-symmetric-40-20261105`.
- Equal TP/SL source: https://github.com/davidamerson/suresh/blob/h1-reverse-vs-breakout-symmetric-40-20261105/ph1_backtest/h1_symmetric_reverse_vs_momentum_equal_tp_sl_2020_2026.py
- 2:1 TP/SL source: https://github.com/davidamerson/suresh/blob/h1-reverse-vs-breakout-symmetric-40-20261105/ph1_backtest/h1_symmetric_reverse_vs_momentum_rr2_2020_2026.py
- Full runs: https://github.com/davidamerson/suresh/actions/runs/41970426842 and https://github.com/davidamerson/suresh/actions/runs/41970431204.
- Per-year artifacts include full trade ledger, per-side summary, equity P/L, sessions, month URL and ZIP SHA256 provenance, source execution logs, normally retained 30 days.
- Exploratory test set has been repeatedly used over prior conversations; **no untouched out-of-sample test**; high-only subgroup sensitivity to slippage and stop gaps is important.

