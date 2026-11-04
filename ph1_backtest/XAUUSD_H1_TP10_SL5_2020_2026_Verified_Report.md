# XAUUSD Raw Spread H1 first-break TP10 SL5 — verified seven-year replay

**Completed on 2026-11-05 (Sri Lanka local date).**
**GitHub Actions verified successful run:** https://github.com/davidamerson/suresh/actions/runs/41891011968

## Exact rules (no withdrawals)

- Data: 295,225,516 actual archived Exness XAUUSD Raw Spread **Bid/Ask quotes** spanning **2020-01-29 through 2026-10-29**. Archived quotes, not executed live fills.
- Sydney (08:00), Tokyo (09:00), London (08:00), and New York (08:00), per **local** times with historical DST. Observe first completed H1 candle's Bid High and Bid Low for each session. First observed subsequent Bid tick strictly above High opens BUY at Ask; first strictly below Low opens SELL at Bid. One trade opportunity per regional session opening; may overlap across sessions.
- **Trader diagram pip**: Gold $0.10. TP **10 diagram pips = $1.00**; SL **5 diagram pips = $0.50**, measured from executed entry quote. Exness official pip is $0.01, NOT the same convention.
- Fixed 0.01 lot (1 oz), independent annual **$1,000** starting simulations, **all profits retained**, **no withdrawals**, example 1:2000 leverage. Immediately close when TP/SL triggered; no averaging/hedging; no Friday forced close in this precise branch.
- Real archived spread through executable Bid/Ask, + $0.07 modeled round-trip commission per 0.01 lot, no extra slippage in main variant. Stops execute at observed executable quote (may gap beyond SL); profit target capped at exactly target. No swap or dynamic high-margin restriction modeling.
- Independent stress variant adds **$0.05 adverse execution per side**.

## Results (main test)

| Year | Closed | TP win | SL loss | Win % | Loss % | Modeled annual net P/L |
|---|---:|---:|---:|---:|---:|---:|
| 2020* | 903 | 218 | 685 | 24.14% | 75.86% | $-293.577 |
| 2021 | 964 | 289 | 675 | 29.98% | 70.02% | $-130.435 |
| 2022 | 967 | 318 | 649 | 32.89% | 67.11% | $-84.982 |
| 2023 | 963 | 301 | 662 | 31.26% | 68.74% | $-109.420 |
| 2024 | 969 | 289 | 680 | 29.82% | 70.18% | $-132.238 |
| 2025 | 959 | 346 | 613 | 36.08% | 63.92% | $-42.599 |
| 2026* | 805 | 252 | 553 | 31.30% | 68.70% | $-119.274 |
| **Total** | **6530** | **2013** | **4517** | **30.83%** | **69.17%** | **$-912.525** |

*2020 begins Jan 29 and 2026 ends Oct 29.*

## Execution-cost stress

| Year | TP hits | SL hits | Win % with $0.05 adverse price per side | Net annual stress P/L |
|---|---:|---:|---:|---:|
| 2020 | 177 | 726 | 19.60% | $-370.921 |
| 2021 | 239 | 725 | 24.79% | $-206.952 |
| 2022 | 265 | 702 | 27.40% | $-166.181 |
| 2023 | 237 | 726 | 24.61% | $-206.745 |
| 2024 | 225 | 744 | 23.22% | $-230.798 |
| 2025 | 287 | 672 | 29.93% | $-132.908 |
| 2026 | 212 | 593 | 26.34% | $-184.818 |
| **Total** | **1642** | **4888** | **25.15%** | **$-1499.323** |

Nominal TP +$0.93 after commission and SL −$0.57 after commission (when stop fills at exact level). Theoretical break-even TP hit rate **38%** before gap losses/additional costs. The main tested rate **30.83%** is below it; every yearly net P/L negative. The adverse execution stress reduces the win rate to **25.15%**.

**Interpret annual net P/L correctly:** The $-912.525 is the sum of **seven separately restarted $1,000 annual simulations**, NOT a single continuous $1,000 account tracked across all seven years. No model margin rejections or active positions at year endpoints were recorded. Simulator outcomes are hypothetical and do not demonstrate actual broker fill quality.

## Audit trail

- Branch `h1-tp10-sl5-sevenyears-20261105` in `davidamerson/suresh`.
- Code: https://github.com/davidamerson/suresh/blob/h1-tp10-sl5-sevenyears-20261105/ph1_backtest/h1_firstbreak_tp10_sl5_2020_2026.py
- Full GitHub Actions run: https://github.com/davidamerson/suresh/actions/runs/41891011968
- Per-year GitHub Action artifacts: `summary.csv`, `individual_trades.csv`, `sessions.csv`, `daily_realized_PnL.csv`, `provenance.json`, `execution.log`. Artifacts normally have limited retention.
- Per-year results checked directly against successful GitHub Actions job logs for all seven years. Source base is prior independently verified TP10/SL10 raw-tick implementation; exact TP10/SL5 changes isolated in new branch.

