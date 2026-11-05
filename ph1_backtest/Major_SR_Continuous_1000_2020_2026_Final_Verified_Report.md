# XAUUSD Major S/R TP90/SL90 — $1,000 ONE continuous account, 2020–2026

**Verified at 2026-11-05.** This is a completed raw-tick simulated backtest of one account, NOT seven $1,000 annual restarts. It deliberately keeps the *causal Major Support/Resistance level selection, high resistance BUY / low support SELL, TP90=Gold $9 and SL90=Gold $9, fixed 0.01 lot (1 troy oz)* of the original successful research. Exness XAUUSD Raw Spread archived Bid/Ask quotes, model $0.07 round-trip 0.01-lot commission, no additional capital and **zero withdrawals**.

## Definitive answer

**Yes: the historical single-account backtest remained profitable after duplicate suppression, Friday flattening, stronger early-closure rules, and conservative modeled swap/margin scenarios.** However it was not a verbatim historical recreation of account-specific daily swaps, news-related HMR or actual live fills, which are unavailable; costs and weekend restrictions below are transparent assumptions, not false claims of broker accuracy.

The most conservative unambiguously weekend-free tested schedule (all Thursday after 12 UTC flat, no Friday trades) ended at:
- **$1,795.162 equity, +$795.162** with conditional swap-free status and normal model 1:2000.
- **$1,742.662 equity, +$742.662** with modeled charge $0.50/0.01-lot per standard rollover (Wednesday triple), and 1:100 account leverage imposed all-hours as an HMR worst-case stress.
- 533 closed orders including 300 TP, 208 SL, 25 time-forced exits. TP/SL-only success rate 300/(300+208) = **59.0551%**.
- **Zero carried positions past Friday weekly close verified by individually checking every trade's UTC entry/exit**, zero modeled margin-call episodes, margin rejections or stop-out liquidations. No positions remained open at final cutoff.

The less restrictive, **Friday noon UTC + Thursday noon before public Friday-holiday** schedule (observed US federal Friday holidays plus Good Friday, known ex ante) yielded:
- **$1,885.442 equity, +$885.442** in swap-free normal model.
- **$1,818.442 equity, +$818.442** with $0.50/0.01-lot per standard overnight and all-hours 1:100 leverage.
- 670 trades: 367 TP, 259 SL, 44 time-forced exits; TP/SL-only winning rate **58.6262%**.
- **Zero positions carried past Friday weekly close verified from every ticket's timestamps**; no margin/stop-out failures. Both are deliberately early-close sensitivity policies, not verified exact Exness historical holiday market hours.

## Comparison across all replay profiles

| Rule | Orders | Closed TP | Closed SL | Time-forced exits | Simulated final equity | Net P/L | Worst continuous drawdown |
|---|---:|---:|---:|---:|---:|---:|---:|
| No duplicate suppression, Fri19 UTC, swap-free, 1:2000 | 1,901 | 1,051 | 757 | 93 | $3,612.499 | +$2,612.499 | $225.247 |
| One order per **unique tick** for overlapping sessions, Fri19, swap-free, 1:2000 | 964 | 528 | 393 | 43 | $2,195.860 | +$1,195.860 | $141.611 |
| At most **one order per S/R boundary per UTC day**, Fri19, swap-free, 1:2000 | 748 | 413 | 303 | 32 | $1,967.649 | +$967.649 | $110.614 |
| Same day/level suppression + $0.10 standard night modeled swap, Fri19 | 748 | 413 | 303 | 32 | $1,953.649 | +$953.649 | $110.714 |
| Same day/level suppression + $0.50 standard night swap, 1:100 leverage, Fri19 | 748 | 413 | 303 | 32 | $1,897.649 | +$897.649 | $112.510 |
| Same day/level suppression + extra $0.05 adverse execution/side, Fri19 | 748 | 411 | 305 | 32 | $1,937.032 | +$937.032 | $110.748 |
| **Fri12, preholiday Thu12, swap-free, 1:2000; zero weekend exposure** | 670 | 367 | 259 | 44 | $1,885.442 | +$885.442 | $104.876 |
| **Fri12, preholiday Thu12, $0.50 modeled swap, 1:100; zero weekend exposure** | 670 | 367 | 259 | 44 | $1,818.442 | +$818.442 | $111.376 |
| **All Thu12 flat / Friday off, swap-free, 1:2000; zero weekend exposure** | 533 | 300 | 208 | 25 | $1,795.162 | +$795.162 | $90.173 |
| **All Thu12 flat / Friday off, $0.50 modeled swap, 1:100; zero weekend exposure** | 533 | 300 | 208 | 25 | $1,742.662 | +$742.662 | $93.173 |

**Important Friday exception audit**: the initial Fri19 model had **three** positions spanning a Friday market closure because of holidays/early close:
- Jul 2–6, 2020 (July 3 market holiday)
- Dec 31, 2020–Jan 3, 2021 (New Year early close)
- Nov 25–28, 2022 (post-Thanksgiving early close).
The first Fri12/Thu19 sensitivity still contained ONE early-Thursday-close exception on Dec 31, 2020. The FINAL Fri12/preholiday-Thu12 and the final all-Thu12/no-Friday profiles were re-run through all 296.7m ticks and had **exactly zero** carried positions across the Friday 22:00 UTC audit checkpoint. Do not promote older Fri19 scenarios as completely weekend-flat.

## One continuous account yearly equity — final conservative variants

| Year | Holiday-aware Fri12 / Thu12 swap-free | Same + $0.50-night & 1:100 | Every Thu12 close, Friday off, swap-free | Every Thu12 close, Friday off + $0.50-night & 1:100 |
|---|---:|---:|---:|---:|
| Starting balance | $1,000.000 | $1,000.000 | $1,000.000 | $1,000.000 |
| 2020* | $964.418 | $956.918 | $1,013.661 | $1,008.161 |
| 2021 | $1,018.346 | $996.346 | $1,056.046 | $1,041.046 |
| 2022 | $1,224.167 | $1,184.667 | $1,253.283 | $1,223.283 |
| 2023 | $1,436.197 | $1,381.697 | $1,416.786 | $1,374.786 |
| 2024 | $1,539.451 | $1,474.451 | $1,461.954 | $1,411.454 |
| 2025 | $1,750.508 | $1,684.008 | $1,631.444 | $1,579.444 |
| 2026* | **$1,885.442** | **$1,818.442** | **$1,795.162** | **$1,742.662** |

*2020 starts January 29 due first available archive; 2026 ends Nov 5, 09:12:23.770 UTC (raw quote feed), rather than full calendar years.* Values are equity (marked, not annual reset); annual net changes may be negative despite whole-run profit. Original best strategy's $2,313.793 was a sum of separately restarted annual accounts and **cannot** be directly interpreted as the continuous $1,000 account's performance.

## Model fidelity, limitations and audit

1. Entry unchanged: at the end of first completed local opening H1 for Sydney 08, Tokyo 09, London 08, NY 08, freeze nearest qualifying resistance/support based on **previous completely closed UTC weekly high/low** and **confirmed 2-left 2-right UTC daily swing high/low**. Trade one real Bid crossing, higher resistance BUY at Ask, lower support SELL at Bid. This is a particular fixed objective definition of Major S/R, **not all hand-drawn S/R zones**.
2. Duplicate prevention is an additional risk constraint requested by user: exact-tick duplicate removed in one profile; more restrictive one level per UTC day in chosen profile. Suppression removes losing and winning events indiscriminately, not by future outcome. Time-forced exits are first observed available Bid/Ask after scheduled cutoff; no fictitious favorable fills.
3. Exness Raw Spread documentation currently specifies approx 30% margin call and 0% stopout and XAUUSD HMR leverage as low as 1:100. These are modeled as margin-call logger, 0%-stopout liquidation check, and **all-hours 1:100 extreme stress**. No exact historical account-by-account HMR event timeline was available. All tested portfolios survived without modeled margin calls, rejections or forced stopouts; stress max margin roughly $67.662.
4. Exness swaps: XAUUSD can be swap-free depending on the trader's Personal Area status. Historical daily XAUUSD long/short rates for this particular account over all 2020–26 were not supplied or available. The +$0.50 charge **is an assumed CASH DEBIT per 0.01 lot** at each ordinary Mon–Thu rollover; Wednesday triple; aligned to Exness advertised summer 21 UTC/winter 22 UTC. These are not historical actual rates and could underestimate or overestimate real fees. A higher actual swap cost could erase the edge.
5. Friday market closure: exact historical holiday hours unavailable; **Fri12 UTC/holiday Thu12 UTC** and especially **every Thu12 UTC** are conservative rules to eliminate weekend carry. The latter sacrifices trading opportunities but verifies sensitivity to forced closure.
6. No untouched multi-year forward trading record, no broker order-fill ledger, no full historical broker swap-rate series, no broker-side stop-order queue priority, no intraday event HMR reconstruction, no annual resets, no profit withdrawals, no martingale or lot adjustments. Historical profitability ≠ guarantee of future performance.
7. Raw source: **84 archives, 296,709,207 processed raw quotes**, Jan 29 2020 – Nov 5 2026. 2026 Nov 05 daily ZIP is live-updated, so compressed source SHA-256 **changed between run times** as additional newer records arrived, even though records processed **through the fixed cutoff** had the same count, first tick and final tick timestamps. Source URLs/bytes/SHA256 in each artifact's `provenance.json`. Earlier 83 source ZIPs retained matching hashes across runs. Do not falsely state all 84 immutable ZIP snapshots had identical SHA across runs.

## GitHub audit links

- Baseline continuous 9 profiles (success): https://github.com/davidamerson/suresh/actions/runs/42023634780
- Early-close exploratory sensitivity (success, but 1 holiday exception): https://github.com/davidamerson/suresh/actions/runs/42026657580
- **Final ZERO-weekend-carry holiday-aware and all-Thursday-noon continuous replay (success)**: https://github.com/davidamerson/suresh/actions/runs/42028767817
- Same-setup code: https://github.com/davidamerson/suresh/blob/major-sr-continuous-1000-dedup-friday-swap-hmr-20261105/ph1_backtest/major_sr_continuous_single_1000.py
- Final strict weekend code: https://github.com/davidamerson/suresh/blob/major-sr-continuous-1000-dedup-friday-swap-hmr-20261105/ph1_backtest/major_sr_continuous_earlier_holiday_and_thursday_noon.py
- GitHub Actions downloadable artifacts with `model_summary.csv`, `continuous_annual_equity.csv`, `ticket_ledger.csv`, `provenance.json`, and `execution.log`. Retention 30 days.

### Source specifications
- Exness Raw Spread account: https://get.exness.help/hc/en-us/articles/17537767270556-Raw-Spread-account
- Exness Gold commodities: https://get.exness.help/hc/en-us/articles/17854173039388-Commodities
- Exness HMR: https://get.exness.help/hc/en-us/articles/20618327917596-Higher-Margin-Requirements-HMR
- Exness overnight swap conventions: https://get.exness.help/hc/en-us/articles/360014709151-About-swap
- Exness swap-free status: https://get.exness.help/hc/en-us/articles/4402341895570-Swap-free-status
