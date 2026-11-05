# XAUUSD first-H1 reverse breakout — high-break SELL TP10/SL5 through TP100/SL50; low-break BUY fixed TP10/SL10

**Research completed:** 5 November 2026 (Asia/Colombo). **GitHub Actions 7-year run status: success.**

**Validated execution:** https://github.com/davidamerson/suresh/actions/runs/41968836669

## Strategy and cost conventions

After the first complete H1 from Sydney 08:00 local, Tokyo 09:00 local, London 08:00 local, and New York 08:00 local (historical DST), store Bid High/Low. First subsequent Bid tick strictly ABOVE high triggers SELL executed at Bid. First Bid tick strictly BELOW low triggers BUY at Ask. Just one first break each regional opening. 0.01 lots (1 oz) with historically observed Exness XAUUSD Raw Spread Bid/Ask, $0.07 modeled round-trip commission per 0.01 lot, no extra simulated slippage for this study. Stops can gap beyond their nominal level, targets capped at requested limit. All profits retained, never withdrawn.

All 10 setups keep BUY TP10/SL10, corresponding to Gold price $1.00 each. On SELL, chosen TP/SL is 10/5, 20/10, 30/15, 40/20, 50/25, 60/30, 70/35, 80/40, 90/45, 100/50 user **diagram pips**. User's diagram pip is Gold $0.10 and should not be confused with the broker's own XAUUSD pip notation. Fixed lot and example leverage 1:2000; independent starting equity of $1,000 **each calendar year**, not one continuous seven-year $1,000 account. Source archive covers Jan 29 2020 to Oct 29 2026, **295,225,516** total quote rows, with individual ZIP source SHA256 in yearly artifacts. No Friday forced closure, no withdrawals or averaging.

## Seven-year primary comparison

All 10 saw 6,530 opening signals. Wider-distance SELL orders sometimes remained open at the end of a year, excluded from closed-trade hit-rate denominator but included as floating marked P/L in the economic total.

| # | High SELL TP/SL diagram pips | Low BUY TP/SL | Closed | TP | SL | Win rate | Loss rate | Combined annual economic P/L | Unclosed at annual endpoints |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10/5 | 10/10 | 6530 | 2239 | 4291 | 34.29% | 65.71% | $-1497.061 | 0 |
| 2 | 20/10 | 10/10 | 6530 | 2304 | 4226 | 35.28% | 64.72% | $-1655.577 | 0 |
| 3 | 30/15 | 10/10 | 6529 | 2344 | 4185 | 35.90% | 64.10% | $-1729.974 | 1 |
| 4 | 40/20 | 10/10 | 6529 | 2356 | 4173 | 36.09% | 63.91% | $-1856.058 | 1 |
| 5 | 50/25 | 10/10 | 6529 | 2359 | 4170 | 36.13% | 63.87% | $-2026.300 | 1 |
| 6 | 60/30 | 10/10 | 6528 | 2392 | 4136 | 36.64% | 63.36% | $-1912.701 | 2 |
| 7 | 70/35 | 10/10 | 6527 | 2410 | 4117 | 36.92% | 63.08% | $-1844.900 | 3 |
| 8 | 80/40 | 10/10 | 6527 | 2410 | 4117 | 36.92% | 63.08% | $-1962.808 | 3 |
| 9 | 90/45 | 10/10 | 6526 | 2429 | 4097 | 37.22% | 62.78% | $-1800.896 | 4 |
| 10 | 100/50 | 10/10 | 6526 | 2423 | 4103 | 37.13% | 62.87% | $-1978.683 | 4 |

**Minimum combined seven-annual loss:** SELL TP10/SL5 (-1497.061 USD). **Highest closed-trade win rate:** SELL TP90/SL45 (37.22%). **All ten have negative combined annual economic P/L.**

## Separate SELL and BUY legs

The invariant BUY leg accounts for **3152 closed**, **1354 TP**, **1798 SL**, **42.96% wins** and **$-779.270 realized annual sum**, in every variant.

| SELL TP/SL | SELL closed | SELL TP | SELL SL | SELL win rate | SELL realized P/L |
|---:|---:|---:|---:|---:|---:|
| 10/5 | 3378 | 885 | 2493 | 26.20% | $-717.791 |
| 20/10 | 3378 | 950 | 2428 | 28.12% | $-876.307 |
| 30/15 | 3377 | 990 | 2387 | 29.32% | $-950.384 |
| 40/20 | 3377 | 1002 | 2375 | 29.67% | $-1076.468 |
| 50/25 | 3377 | 1005 | 2372 | 29.76% | $-1246.710 |
| 60/30 | 3376 | 1038 | 2338 | 30.75% | $-1136.430 |
| 70/35 | 3375 | 1056 | 2319 | 31.29% | $-1072.774 |
| 80/40 | 3375 | 1056 | 2319 | 31.29% | $-1190.682 |
| 90/45 | 3374 | 1075 | 2299 | 31.86% | $-1027.008 |
| 100/50 | 3374 | 1069 | 2305 | 31.68% | $-1204.795 |

The 'SELL realized P/L' above excludes floating P/L from unresolved year-end SELL positions. The main *economic* P/L does not exclude it.

## Year-by-year net economic P/L in USD

Each yearly test is independently started at $1,000. 2020* starts Jan 29; 2026* ends Oct 29. These are NOT portions of one continuous compounded account.

| SELL TP/SL | 2020* | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/5 | $-445.62 | $-199.46 | $-177.84 | $-152.74 | $-125.56 | $-207.61 | $-188.22 |
| 20/10 | $-445.87 | $-197.74 | $-174.49 | $-221.96 | $-156.99 | $-257.23 | $-201.30 |
| 30/15 | $-478.51 | $-156.79 | $-164.31 | $-218.64 | $-226.59 | $-303.87 | $-181.26 |
| 40/20 | $-540.12 | $-211.47 | $-169.71 | $-216.97 | $-274.78 | $-267.88 | $-175.13 |
| 50/25 | $-622.53 | $-287.82 | $-149.75 | $-221.74 | $-316.18 | $-265.49 | $-162.79 |
| 60/30 | $-676.64 | $-298.46 | $-174.26 | $-203.14 | $-253.93 | $-261.51 | $-44.76 |
| 70/35 | $-670.55 | $-238.80 | $-201.32 | $-130.78 | $-278.21 | $-300.21 | $-25.03 |
| 80/40 | $-783.73 | $-275.99 | $-137.99 | $-89.40 | $-362.73 | $-310.10 | $-2.86 |
| 90/45 | $-787.74 | $-263.53 | $39.17 | $-154.97 | $-363.17 | $-275.34 | $4.68 |
| 100/50 | $-794.94 | $-295.33 | $120.32 | $-222.96 | $-534.22 | $-258.21 | $6.65 |

## Year-by-year closed-trade win percentages

| SELL TP/SL | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/5 | 23.26% | 35.27% | 36.40% | 37.18% | 38.29% | 33.37% | 35.78% |
| 20/10 | 27.13% | 37.14% | 38.16% | 36.14% | 38.18% | 33.58% | 36.27% |
| 30/15 | 27.80% | 38.63% | 38.88% | 37.49% | 37.25% | 33.68% | 37.27% |
| 40/20 | 27.69% | 37.69% | 38.99% | 38.11% | 37.15% | 35.14% | 37.52% |
| 50/25 | 27.35% | 36.86% | 39.40% | 38.42% | 37.25% | 35.56% | 37.76% |
| 60/30 | 27.46% | 37.07% | 39.19% | 38.88% | 38.49% | 35.87% | 39.38% |
| 70/35 | 28.16% | 37.90% | 38.99% | 39.71% | 38.49% | 35.66% | 39.38% |
| 80/40 | 27.72% | 37.69% | 39.61% | 40.12% | 37.98% | 35.77% | 39.38% |
| 90/45 | 28.16% | 37.90% | 40.99% | 39.60% | 38.18% | 36.18% | 39.25% |
| 100/50 | 28.49% | 37.80% | 41.41% | 39.19% | 37.25% | 36.39% | 39.13% |

## Comparison to earlier 1:1 SELL TP=SL research

Both these runs use exactly the **same high-break SELL and low-break BUY entry mechanics**, identical BUY TP10/SL10, market sessions, lot, annual $1,000, and quote archive; only SELL SL differs.

| High SELL TP | Old SELL SL (1:1) | New SELL SL (2:1) | Old overall win % | New overall win % | Old annual net sum | New annual net sum | New P/L improvement |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 10 | 5 | 42.99% | 34.29% | $-1580.110 | $-1497.061 | $83.049 |
| 20 | 20 | 10 | 44.36% | 35.28% | $-1679.678 | $-1655.577 | $24.101 |
| 30 | 30 | 15 | 45.00% | 35.90% | $-1728.529 | $-1729.974 | $-1.445 |
| 40 | 40 | 20 | 44.88% | 36.09% | $-2005.071 | $-1856.058 | $149.013 |
| 50 | 50 | 25 | 45.37% | 36.13% | $-1916.356 | $-2026.300 | $-109.944 |
| 60 | 60 | 30 | 45.44% | 36.64% | $-2012.938 | $-1912.701 | $100.237 |
| 70 | 70 | 35 | 45.62% | 36.92% | $-2014.196 | $-1844.900 | $169.296 |
| 80 | 80 | 40 | 45.39% | 36.92% | $-2385.119 | $-1962.808 | $422.311 |
| 90 | 90 | 45 | 45.39% | 37.22% | $-2537.157 | $-1800.896 | $736.261 |
| 100 | 100 | 50 | 45.58% | 37.13% | $-2455.472 | $-1978.683 | $476.789 |

Shorter SL reduced win percentages, but the combined annual economic P/L loss was *smaller* for **8 of 10** variants. Nevertheless **none** had positive combined annual economic P/L in the new 2:1 run. This is not evidence that positive future performance is guaranteed.

## Risk / drawdown

| SELL TP/SL | Max historical annual model drawdown (USD) | Lowest historical annual simulated equity from $1,000 |
|---:|---:|---:|
| 10/5 | $448.719 | $552.697 |
| 20/10 | $451.508 | $550.908 |
| 30/15 | $489.356 | $514.099 |
| 40/20 | $552.359 | $453.361 |
| 50/25 | $636.335 | $371.410 |
| 60/30 | $689.227 | $316.301 |
| 70/35 | $682.023 | $323.505 |
| 80/40 | $801.177 | $204.351 |
| 90/45 | $805.668 | $199.860 |
| 100/50 | $813.366 | $192.162 |

Largest-distance setups reduced robustness materially: TP100/SL50 had a minimum historical annual simulated equity of $192.16, compared with $552.70 for TP10/SL5. These are modeled quote-marked values without exhaustive broker stop-out and dynamic margin rules.

A SELL leg with TP distance D and SL distance D/2 has nominal break-even hit rate **(D/2 + 0.07)/(D + D/2)** at 0.01 lot (before gap/slippage); approximately 38% for TP10/SL5 and 33.8% for TP100/SL50. The fixed BUY TP10/SL10 has nominal break-even hit rate **53.5%**, but actual TP hits **42.96%**. Actual SELL win rates range from 26.20% to 31.86% in these ten variants, below their corresponding individual break-even needs. Net P/L also reflects stop gaps and commission.

## Implementation and provenance

- New branch: `h1-reverse-sell-rr2-10to100-buy10-20261105`
- Strategy code: https://github.com/davidamerson/suresh/blob/h1-reverse-sell-rr2-10to100-buy10-20261105/ph1_backtest/h1_reverse_high_sell_rr2_low_buy_fixed10_2020_2026.py
- Workflow run: https://github.com/davidamerson/suresh/actions/runs/41968836669
- Each of 7 annual job artifacts: `summary.csv`, `by_side_summary.csv`, `individual_trades.csv`, `sessions.csv`, `daily_realized_PnL.csv`, `provenance.json`, `execution.log`, normally 30-day retention.
- Cross-checked all **70 annual variant results and 140 side breakdown rows** directly against successful job execution logs. No modeled margin-rejected orders, though margin and stop-out reality is not exhaustively simulated.
- Historic research backtest and variants optimized on previously studied history; no untouched future holdout. This is hypothetical execution on archived quotes, not a forecast or a guaranteed profit system.
