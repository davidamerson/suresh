# XAUUSD Major Trend Change (H4 market structure shift) — 10 RR3:1 models, verified raw tick backtest

**Completed 6 November 2026.** [Full successful GitHub Actions run](https://github.com/davidamerson/suresh/actions/runs/42182181198). [Exact causal code](https://github.com/davidamerson/suresh/blob/major-trend-h4-structure-change-rr3-10models-20261106/ph1_backtest/h4_major_trend_change_rr3_ten_variants_2020_2026.py).

## User's request and honest interpretation of undefined "Major Trend Change"

The user explicitly replaces the old Major Support/Resistance breakout ENTRY mechanism with a **Major Trend Change** entry mechanism, testing exactly ten ratio-3-to-1 TP/SL combinations: TP30/SL10, TP60/SL20, TP90/SL30, TP120/SL40, TP150/SL50, TP180/SL60, TP210/SL70, TP240/SL80, TP270/SL90, TP300/SL100.

A discretionary major trend reversal has no universal single rule. BEFORE running the backtest, we locked ONE objective, strictly causal H4 market structure shift (MSS) definition:

1. Construct UTC H4 bars from the actual observed **Bid** ticks. Strict **2-left 2-right** pivot highs/lows require five **COMPLETELY CLOSED** H4 candles. No pivot is confirmed in advance; the last two fully closed H4 bars after a pivot make it eligible.
2. Require a previously established major **uptrend** with two successively **higher confirmed H4 swing highs and higher confirmed H4 swing lows**, or major **downtrend** with two successively **lower confirmed H4 swing highs and lower confirmed H4 swing lows**.
3. A prior DOWNTREND changes to bullish only if a **fully closed H4 Bid candle closes ABOVE the most recent PREVIOUSLY confirmed H4 swing HIGH**, with the immediately previous completed H4 close at/below that high. Buy at the actual first available **Ask** price of the NEXT H4 bar (same event, no signal-chasing).
4. A prior UPTREND changes to bearish only if an H4 Bid candle closes BELOW the most recent PREVIOUSLY confirmed H4 swing LOW, with previous H4 close at/above that low. Sell at the next H4 period's first observed **Bid**.
5. Flip the recorded trend regime only when the above opposite market structure break happens. A new same-direction entry requires a new, genuine opposite-to-next reversal. **No daily/weekly Support/Resistance breakout entry, no Sydney/Tokyo/London/New York first-hour entry logic**.
6. Overlapping positions permitted if genuine opposite H4 trend changes arise before old TP/SL positions close. No add-ons or averaging. Stop/target price decision always made using the actually observed executable side. Entries never use future prices.
7. This is **one testable proxy for 'major trend change,' not a claim that ALL trend reversals are represented**. Changing the trend definition after seeing these results would itself be another in-sample optimization.

User diagram-pip convention: **10 pips = Gold $1.00**, so TP30/SL10 is Gold TP+$3/SL-$1, and TP300/SL100 is TP+$30/SL-$10. Each individual ticket 0.01 lot = 1 oz XAUUSD, $0.07 modeled total commission, and spread derived from actual historical Bid/Ask.

## Data and account model

- **296,709,207** archived Exness Raw Spread XAUUSD real Bid/Ask quotes from **2020-01-29 00:00:00.952 UTC** through **2026-11-05 09:12:23.770 UTC**, parsed and streamed from **84 source ZIPs**, each exact URL and SHA-256 in artifact `provenance.json`.
- Ten individually simulated **single continuous $1,000 accounts**, one per strategy for the FULL period, no annual reset, no deposits, no withdrawals, and **fixed 0.01 lot per ticket**.
- All Friday trading permitted, weekend/holiday positions carried, trade exits **ONLY** TP or SL. No forced Friday exits, no time exits, no break-even or trailing SL.
- 1:2000 initial leverage and a modeled 0% equity broker stopout contingency; no stopouts, modeled margin calls or margin rejections occurred. Actual historical broker dynamic HMR, account-specific swap rates, order execution latency and broker-side queue priority not reproduced.
- **Swap-free assumption**, conditional on real account eligibility. A real swap-charging account could do worse. Nominal TP at exactly requested limit, stops execute at first available actual executable quote and can gap beyond intended stop.

## Full verified result matrix

| Model | Trades | TP | Hard SL | Win % | Continuous net P/L USD | Closing equity USD | Max equity drawdown USD | Worst marked equity USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TP30 / SL10 | 463 | 119 | 344 | 25.70% | −$30.061 | $969.939 | $39.393 | $968.561 |
| TP60 / SL20 | 463 | 123 | 340 | 26.57% | +$10.034 | $1010.034 | $90.655 | $953.348 |
| TP90 / SL30 | 463 | 115 | 348 | 24.84% | −$63.285 | $936.715 | $208.694 | $926.082 |
| TP120 / SL40 | 463 | 117 | 346 | 25.27% | −$33.031 | $966.969 | $171.325 | $952.463 |
| TP150 / SL50 | 463 | 114 | 349 | 24.62% | −$87.880 | $912.120 | $299.027 | $855.195 |
| TP180 / SL60 | 463 | 107 | 356 | 23.11% | −$263.065 | $736.935 | $428.294 | $707.212 |
| TP210 / SL70 | 463 | 111 | 352 | 23.97% | −$185.423 | $814.577 | $487.602 | $642.607 |
| TP240 / SL80 | 463 | 107 | 356 | 23.11% | −$328.298 | $671.702 | $665.858 | $535.375 |
| TP270 / SL90 | 463 | 110 | 353 | 23.76% | −$255.284 | $744.716 | $659.818 | $565.003 |
| TP300 / SL100 | 463 | 113 | 350 | 24.41% | −$161.775 | $838.225 | $660.893 | $506.385 |

**9/10 strategies historically lost money**, despite the nominal 3:1 risk/reward and more than six years of raw quotes. The lone positive setup, **TP60/SL20**, ended +$10.034 (1.0034% total on initial account), with maximum continuous equity DD **$90.655** (~9% of initial account), TP123 / SL340, win rate **26.5659%** across **463 distinct H4 major reversal signals**.

That razor-thin positive result is NOT an established trading edge; the in-sample result is easily erased by swaps/slippage/uncertainty, and a 3:1 system's nominal breakeven rate is 25% *before* costs and gaps.

Especially weak historical model **TP240/SL80** lost **$328.298** and suffered **$665.858** max equity DD. The highest raw win percentage among ten is TP60/SL20 at 26.57%, not remotely close to the earlier S/R setup win percentages; these are **completely different entry strategies and RR setups**, so avoid misleading direct win-rate comparisons.

## Trade audit

- **All ten portfolios** have **EXACTLY 463 IDENTICAL entry events**, as confirmed by sorting each original ticket's UTC entry, executable entry price, side and exact prior confirmed H4 pivot level and comparing equality across all models. Raw ticket ledger has **4,630** finished tickets: **232 BUY reversals and 231 SELL reversals per model**.
- Ticket-level realized P/L for all ten models individually sums exactly to their model-summary net P/L; there are no unaccounted open tickets at the end.
- All ten have **0 Friday/time-forced exits**, **0 modeled margin rejected trades**, **0 modeled margin call notices**, **0 modeled stopout events**, and **0 end-of-period open positions**. Max simultaneously held positions **one** for short TP/SL models and **two** for larger stops/targets.
- Even when a model records a TP win, it may lose after real costs depending on execution/fee conventions; here TP net model P/L is exact nominal Gold target less $0.07 fee.
- Trades per calendar UTC year for TP60/SL20: 2020 57, 2021 74, 2022 72, 2023 70, 2024 59, 2025 72, 2026 partial 59. TP60/SL20 net trade P/L by *entry year*: 2020 −$31.861, 2021 +$53.954, 2022 +$58.205, 2023 −$21.233, 2024 −$4.071, 2025 −$30.577, 2026 −$14.383. In this dataset every trade is ultimately closed, but a year-end open ticket can shift the timing of account equity compared to grouping by entry year. **2023–2026 entry-year P/L all negative for this 'best' model**.

## Continuous account year-end equity, illustrative main and worst

| Year end | TP30/SL10 | TP60/SL20 (single historical positive) | TP240/SL80 (largest loss) |
|---|---:|---:|---:|
| Starting balance | $1,000.000 | $1,000.000 | $1,000.000 |
| 2020 (partial) | $973.255 | $968.139 | $1,145.739 |
| 2021 | $980.348 | $1,022.093 | $926.639 |
| 2022 | $977.203 | $1,076.064 | $773.362 |
| 2023 | $982.761 | $1,059.065 | $611.667 |
| 2024 | $998.718 | $1,054.994 | $582.043 |
| 2025 | $980.437 | $1,024.417 | $639.720 |
| 2026 (to Nov05) | **$969.939** | **$1,010.034** | **$671.702** |

The 2022 year-end equity $1,076.064 for TP60/SL20 fell to only $1,010.034 in 2026. This is NOT a stable upward historical equity trajectory. Some year-end values may mark open tickets, and no year-end forced close or reset occurs.

## Research interpretation and forward-testing caution

The strict confirmed-H4-reversal idea did **NOT** show the robust positive expectancy in these specific ten 3:1 RR setups over this historical quote period. It produced many false reversals/failed followthroughs and net losses in nine of ten variants. The user should not deploy it on live capital based on this result.

No claim that *all* trend-change systems fail: trend change could be operationally defined using D1 instead of H4, additional reversal strength, structure displacement, volatility normalization, or retest, but changing filters to improve these *same* historical outcomes would introduce multiple testing/in-sample overfit and requires honest future/out-of-sample verification.

The previous Major S/R system TP90/SL90 had +$958.890 simulated net (under its own entirely different, much more frequent entry/exit rules), while the previous Major S/R TP90/SL190 obtained +$1,202.160. Those prior profits cannot be directly attributed to the trend-change strategy and do not provide independent validation of it.

## Reproduce and audit

- [Successful Actions 10 model tick replay](https://github.com/davidamerson/suresh/actions/runs/42182181198)
- [Full Python implementation, uses proven downloader/analytics with entirely REPLACED entry engine](https://github.com/davidamerson/suresh/blob/major-trend-h4-structure-change-rr3-10models-20261106/ph1_backtest/h4_major_trend_change_rr3_ten_variants_2020_2026.py)
- Artifact: `XAUUSD-H4MajorTrendChange-RR3-10Models-2020-2026`, includes `ticket_ledger.csv` with all entry/exit and H4 trigger pivot levels, `model_summary.csv`, `continuous_annual_equity.csv`, `provenance.json` with all 84 SHA256, `execution.log`, `open_positions_at_cutoff.csv` (empty).
