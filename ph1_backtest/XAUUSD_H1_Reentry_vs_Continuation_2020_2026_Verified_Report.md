# XAUUSD H1 breakout: first range re-entry versus first +$0.50 extension

**Verified historical research dated 5 November 2026 (Asia/Colombo).**
**Completed GitHub Actions 7-year replay:** https://github.com/davidamerson/suresh/actions/runs/41894719216

## Predefined causal event classification

For the first **completed** H1 after Sydney 08:00, Tokyo 09:00, London 08:00, and New York 08:00 in their *respective local timezones*, preserve the completed Bid High and Bid Low. Upon first observed subsequent Bid breakout, start ONE episode per session opening. The FIRST of two observed outcomes classifies the episode and produces exactly one independent hypothetical trade:
- **Range re-entry FIRST:** after high break, first observed Bid **inside inclusive [H1 Low, H1 High]** -> SELL at current Bid. After low break, first inside -> BUY at current Ask. Entry is on the observed return; not retrospectively on the initial break.
- **Continuation FIRST:** after high break, Bid reaches **H1 High + Gold $0.50** before re-entry -> BUY at current Ask. After low break, Bid reaches **H1 Low − Gold $0.50** first -> SELL at current Bid. If first breakout quote already exceeds the extension threshold, classification and entry occur on that quote.
- Once either event fires, **ignore the other type**, even if it happens later. Signals expire at the next same-session opening; missing completed H1 has no invented signal. Consecutive quotes across monthly file boundaries use persistent state.
- The $0.50 extension threshold is a **research definition, not proof of genuine market acceptance**. No claim about continuous volume/limit order book is made.
- TP **10 trader diagram pips = Gold $1.00**, SL **5 diagram pips = Gold $0.50**, both measured from that event-time executable entry (NOT from the first initial breakout). Official Exness 1 pip = Gold $0.01; different units.
- Exness XAUUSD Raw Spread, actual archived Bid/Ask quotes, 0.01 lot = 1 oz, model $0.07 round-trip commission, no extra slippage in base. Stress variants add adverse $0.05 price per side. 1:2000 example margin and separate annual starting $1,000 balances; **no profit withdrawals**, no averaging, no forced Friday closure. TP closed immediately at fixed limit; SL filled at available quote with possible gap loss. All trade results historical hypothetical fills, not verified live execution.
- Date coverage **2020 Jan 29 onward**, **2026 through Oct 29**, archived **295,225,516** quote records; no fabricated months.

## First-event classification by year

| Year | First regional H1 breaks | Re-entry before extension | Extension before re-entry | Re-entry % | Extension % |
|---|---:|---:|---:|---:|---:|
| 2020* | 903 | 644 | 259 | 71.32% | 28.68% |
| 2021 | 964 | 754 | 210 | 78.22% | 21.78% |
| 2022 | 967 | 768 | 199 | 79.42% | 20.58% |
| 2023 | 963 | 793 | 170 | 82.35% | 17.65% |
| 2024 | 969 | 814 | 155 | 84.00% | 16.00% |
| 2025 | 959 | 726 | 233 | 75.70% | 24.30% |
| 2026* | 805 | 551 | 254 | 68.45% | 31.55% |
| **Total** | **6530** | **5050** | **1480** | **77.34%** | **22.66%** |

Event-by-side totals: high breaks 3378 -> re-entry 2630 / extension 748; low breaks 3152 -> re-entry 2420 / extension 732. There were **zero unresolved first-break episodes** under this observed history and event rule.

## Strategy trade results (TP10 / SL5)

| Year | Re-entry TP / SL | Re-entry win % | Re-entry net P/L | Continuation TP / SL | Continuation win % | Continuation net P/L |
|---|---:|---:|---:|---:|---:|---:|
| 2020* | 154 / 490 | 23.91% | $-186.304 | 61 / 198 | 23.55% | $-110.333 |
| 2021 | 230 / 524 | 30.50% | $-97.684 | 63 / 147 | 30.00% | $-27.971 |
| 2022 | 247 / 521 | 32.16% | $-78.943 | 51 / 148 | 25.63% | $-40.386 |
| 2023 | 255 / 538 | 32.16% | $-80.864 | 41 / 129 | 24.12% | $-38.491 |
| 2024 | 272 / 542 | 33.42% | $-70.109 | 45 / 110 | 29.03% | $-23.545 |
| 2025 | 241 / 485 | 33.20% | $-67.880 | 85 / 148 | 36.48% | $-8.199 |
| 2026* | 157 / 394 | 28.49% | $-113.563 | 81 / 173 | 31.89% | $-35.937 |
| **Total** | **1556 / 3494** | **30.81%** | **$-695.347** | **427 / 1053** | **28.85%** | **$-284.862** |

For re-entry trade, win rate 30.81%, loss rate 69.19%. For first-extension trade, win rate 28.85%, loss rate 71.15%. In all 7 annual models, both base strategies have negative modeled economic P/L. Annual P/L totals each sum seven **independently initialized $1,000 yearly accounts**, not one continuous 7-year portfolio. Avoid combining these separate annual economic P/L series into a fictional single account balance.

## Cost stress (+Gold $0.05 adverse execution per side)

| Branch | Main TP % | Stress TP count | Stress TP % | Stress modeled annual P/L sum |
|---|---:|---:|---:|---:|
| Re-entry fade | 30.81% | 1238 / 5050 | 24.51% | $-1182.837 |
| Extension trend | 28.85% | 355 / 1480 | 23.99% | $-402.275 |

Nominal exact TP payout on one 0.01 lot: +$0.93 after fee; exact SL: −$0.57, implying an ideal break-even rate of 38% before adverse stop gaps, swaps, or additional execution costs. Both chosen entry branches fall below 38% on the seven-year model, and cost stress worsens performance.

## Interpretation and limits

1. Under this **specified Gold $0.50 extension-versus-return definition**, price returned inside the H1 reference range first in roughly 77.34% of first-break episodes. This is a statistic of that short-term path structure **not** a tradable win rate or proof that a full price reversal will follow.
2. Entering at first re-entry gave only 30.81% TP success at the chosen $1 TP/$0.50 SL, negative net simulated returns; entering after +$0.50 extension also negative.
3. A different extension threshold ($0.25/$1.00), holding horizon, confirmation (e.g., two completed M1 closes inside/outside), higher-timeframe context, spread filter, or alternative TP/SL may change results. These variants were NOT tested in this run; treat any subsequent search as exploratory and validate on genuinely future data and with multiple-testing precautions.
4. The source is historical broker *quote* data, not actual fills, centralized volume, quote priority or real stop execution guarantee. Historical 2020–2026 have already been reviewed in repeated research and are **not pristine independent holdout years**.

## Audit trail
- Branch `h1-break-reentry-vs-extension-20261105`.
- Script https://github.com/davidamerson/suresh/blob/h1-break-reentry-vs-extension-20261105/ph1_backtest/h1_reentry_vs_extension_tick_2020_2026.py
- GitHub Actions https://github.com/davidamerson/suresh/actions/runs/41894719216
- Individual per-year output artifacts named `H1-Reentry-vs-Extension-YEAR` contain `summary.csv`, `individual_trades.csv`, `sessions.csv`, `daily_realized_PnL.csv`, `provenance.json` (with archive URL/SHA-256), and `execution.log` (retention-limited).
- All 7 annual matrix jobs completed successfully. In both main branches and their stress variants, no margin-rejected orders or year-end open positions; all 6,530 classified episodes yielded their corresponding finished simulated order.
- Numbers transcribed and aggregated directly from original successful per-year GitHub Actions execution logs.

