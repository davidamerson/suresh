# Exploratory high-only H1 breakout BUY TP80/SL40 — seven-year baseline and adverse slippage stress

**Final audited result, November 5, 2026.** GitHub Actions run https://github.com/davidamerson/suresh/actions/runs/41971217147 **completed successfully in all seven annual matrix jobs**.

## Selection rule

At each Sydney (08 local), Tokyo (09), London (08), New York (08) market session, wait for completion of first H1 Bid reference bar. Enter **BUY** on first subsequent Bid tick strictly above the stored H1 High, at then executable Ask. **If H1 Low breaks FIRST, record that first-break opportunity as used and do not enter later even if High breaks.** Only one first-break signal per session opening. 0.01 lot (1oz), Gold TP $8.00 (user diagram 80 pips), SL $4.00 (user diagram 40 pips) from executed entry price, no take-profit improvements assumed; stops can gap. No withdrawals, fixed lot and independently reset $1,000 start per calendar year. Four regionally time-zoned session windows with historical DST, raw Exness Bid/Ask monthly quote data from 2020 Jan29 to 2026 Oct29, source ZIP archive SHA256 recorded.

- BASE: historical Bid/Ask spread + model $0.07 roundtrip commission, no extra slippage.
- STRESS: identical strategy plus Gold **$0.05 unfavorable price per side**, meaning entry and exit separately, so an adverse roundtrip execution increment of up to approximately $0.10 per 0.01 lot if fill timing unchanged.

## Results

| Model | Opened | Closed | TP count | SL count | Win % | Loss % | Sum annual economic P/L USD | Year-end open positions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Base | 3378 | 3376 | 1175 | 2201 | 34.80% | 65.20% | **$271.334** | 2 |
| Stress | 3378 | 3376 | 1144 | 2232 | 33.89% | 66.11% | **$-100.599** | 2 |

**Stress reduced simulated annual profit/loss sum by $371.933**, flipping a positive in-sample base result to negative. This failure of modest adverse-execution sensitivity prevents calling it a robust profitable system. All annual P/L are individually restarted simulations, NOT a continuously funded $1,000 balance across seven years.

## Annual economic P/L breakdown

| Year | Base TP / SL | Base win % | Base economic P/L | Stress TP / SL | Stress win % | Stress economic P/L |
|---:|---:|---:|---:|---:|---:|---:|
| 2020* | 171 / 324 | 34.55% | $19.068 | 167 / 328 | 33.74% | $-29.612 |
| 2021 | 146 / 317 | 31.53% | $-140.392 | 144 / 319 | 31.10% | $-164.413 |
| 2022 | 154 / 303 | 33.70% | $-19.237 | 151 / 306 | 33.04% | $-56.379 |
| 2023 | 168 / 321 | 34.36% | $12.518 | 163 / 326 | 33.33% | $-46.477 |
| 2024 | 193 / 333 | 36.69% | $163.657 | 185 / 341 | 35.17% | $69.945 |
| 2025 | 203 / 337 | 37.59% | $228.760 | 197 / 343 | 36.48% | $157.256 |
| 2026* | 140 / 266 | 34.48% | $6.960 | 137 / 269 | 33.74% | $-30.919 |
| **Total** | **1175 / 2201** | **34.80%** | **$271.334** | **1144 / 2232** | **33.89%** | **$-100.599** |

*Partial source coverage 2020 Jan29 onward, 2026 through Oct29.*

## Side-specific independent replay cross-check

The original two-direction momentum TP80/SL40 model showed 3,376 closed High-break BUY tickets, 1,175 TP wins, and seven-year realized P/L **+$271.738** on its High-break subgroup. The separate **HIGH-ONLY** BASE run reproduced **exactly the same** closed tickets, wins and realized P/L (+$271.738) from actual quotes. However, two open High trades mark-to-market at year endpoints, making economic P/L **+$271.334** on annual restarts.

In the adverse +0.05 per-side STRESS the win count declined to 1,144 and annual economic P/L became **−$100.599**. Margins in these hypothetical simulations had zero modeled rejections; they do not certify broker stopout behavior.

This High-only experiment was selected *after scanning 40 combined strategies and their High/Low subgroups* on the same years: **strong in-sample multiple-comparison bias**. Even the no-extra-slip positive result is NOT a proven out-of-sample or live edge. Spread and commission are included; swaps, dynamic leverage margin, broker fill priority, network latency and all real market behaviors are not exhaustively modelled.

## Audit and source code

- Workflow: https://github.com/davidamerson/suresh/actions/runs/41971217147
- Source: https://github.com/davidamerson/suresh/blob/h1-reverse-vs-breakout-symmetric-40-20261105/ph1_backtest/h1_high_only_momentum_tp80_sl40_stress.py
- Annual artifacts: `H1-High-Only-Buy80SL40-Stress-YEAR`, with `summary.csv`, `individual_trades.csv`, `by_side_summary.csv`, `daily_realized_PnL.csv`, `sessions.csv`, `provenance.json` and `execution.log`, normally limited to 30-day retention.
