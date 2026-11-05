# VERIFIED — XAUUSD Major S/R TP/SL ONLY, zero Friday forced exits, positions held through weekends (2020–2026)

**Test completed 5 November 2026**, independently audited against the actual GitHub Actions downloaded `model_summary.csv`, full `ticket_ledger.csv`, `continuous_annual_equity.csv`, `open_positions_at_cutoff.csv` and tick-source `provenance.json`.

[**Successful full seven-year GitHub Actions replay**](https://github.com/davidamerson/suresh/actions/runs/42050760343), Numba/pandas causal engine implementation: [`major_sr_tp_sl_only_weekend_hold_2020_2026.py`](https://github.com/davidamerson/suresh/blob/major-sr-tp-sl-only-weekend-hold-20261105/ph1_backtest/major_sr_tp_sl_only_weekend_hold_2020_2026.py).

## Exactly what changed

The user now allows trades to remain OPEN during any Friday, weekend, holiday or across year-end, and asks that a trade be **closed only on Take Profit or Stop Loss**. Accordingly:
- **No Friday forced close. No Thursday holiday time exit. No Friday entry restrictions. No 6-hour losing-trade time stop. No year-end forced close.**
- Original fixed exit is TP or SL; BE and trailing are *causally adjusted stop-loss levels* and their close reasons are recorded as `BREAKEVEN_STOP` or `TRAILING_STOP`, NOT as full TP hit.
- **Raw executable Bid/Ask quote at first observed stop crossing**, including after weekend market reopen (possible stop gapping).
- Hypothetical equity zero would still trigger compulsory broker 0%-equity stopout; every one of 12 scenarios verified **ZERO broker stopout events**, hence in fact **ALL 12 scenarios had exactly TP/SL-only position exits**. Also 0 time exits, 0 forced Friday exits, 0 margin rejections, 0 open positions at Nov5 final cutoff, no synthetic closing marks.
- 0.01 lot per order (1oz), no capital added, no profits withdrawn, one continuous $1,000 account over **296,709,207 actual archived Exness XAUUSD Raw Spread Bid/Ask quotes**, 84 source ZIP snapshots Jan 29 2020 to Nov 05 2026 09:12:23.770 UTC. SHA-256, URLs, raw rows and first/last timestamps retained per source. Commission model = $0.07 per 0.01 lot complete roundtrip, actual historical observed spread.
- The original causal entry framework is unchanged: four opening first-completed regional H1 windows with DST, confirmed UTC 2L2R D1 swing and previous CLOSED UTC week high/low, resistance break BUY/support break SELL, all eligible sources (up to four per local opening), S/R zones within Gold $1 treated as same price zone, NO one-trade/day or one-trade/session cap. Same-zone reentry only after prior ticket has closed, an H1 bar closes back on prebreakout side by Gold $1 or $9 (given scenario), and a new true observed Bid tick recross. No future tick lookahead.
- Full TP9 / SL9 refers to **Gold price $9 / $9** (the user's 90 diagram pips); not the broker's official XAUUSD pip size.
- Swap-free profiles require an actually qualifying account; account-specific historical swap series is **unavailable**. Separately, clearly labeled stress profiles debit **$0.50 per 0.01 lot per ordinary rollover, Wednesday 3×** using a uniform model and impose 1:100 leverage all hours. Stress debits are hypothetical, not claims about Exness actual 2020–26 rates.
- The current (2026) broker documentation permits quotes jumping over stops and execution at next available price, with potential fills worse than the specified SL; this raw-quote engine simulates first-available historical quote, without broker queue latency.

## All 12 verified scenarios

| Model | Closed | TP | Hard SL | Modified SL | Monetary losing trades | Net profit USD | Max DD USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original $1 H1 rearm TP9/SL9 | 1165 | 639 | 526 | 0 | 526 | +$873.337 | $142.587 |
| $1 rearm TP9/SL6 | 1300 | 583 | 717 | 0 | 717 | +$778.516 | $120.698 |
| $1 rearm TP9/SL7 | 1248 | 604 | 644 | 0 | 644 | +$764.771 | $127.646 |
| $1 rearm BE at +4.5 | 1306 | 498 | 401 | 407 | 800 | +$719.198 | $128.933 |
| $1 rearm BE at +6 | 1248 | 554 | 449 | 245 | 692 | +$789.049 | $137.260 |
| $1 rearm trail at +6 / gap4 | 1248 | 389 | 449 | 410 | 450 | +$683.322 | $173.193 |
| $9 H1 rearm TP9/SL9 | 793 | 454 | 339 | 0 | 339 | +$958.890 | $98.253 |
| $9 rearm BE at +6 | 793 | 370 | 271 | 152 | 422 | +$813.185 | $89.186 |
| $9 rearm trail at +6 / gap4 | 793 | 266 | 271 | 256 | 272 | +$719.626 | $93.332 |
| Stress: $1 rearm TP9/SL9, $0.5 swap+1:100 | 1165 | 639 | 526 | 0 | 526 | +$736.337 | $155.816 |
| Stress: $9 rearm TP9/SL9, $0.5 swap+1:100 | 793 | 454 | 339 | 0 | 339 | +$868.390 | $102.753 |
| Stress: $9 rearm BE6, $0.5 swap+1:100 | 793 | 370 | 271 | 152 | 422 | +$736.685 | $93.686 |

All 12 net P/L are from **ONE initial $1,000 account running continuously** with no withdrawals. Model max drawdown includes floating mark-to-market losses. All 12 models end with **0 open positions**, hence equity=cash at Nov05 historical cutoff.

**Ranking and interpretation:**
- **Highest net simulated P/L:** $9 H1-rearm TP9SL9, **+$958.890** on 793 tickets, 454 full TP vs 339 hard SL, TP fraction **57.2509%**, max drawdown **$98.253**. On the earlier Friday/holiday forced-close test, SAME $9 rearm rule was **+$786.785** on 735 tickets, 402 TP, 304 hard SL plus 29 forced Friday exits: a $172.105 gain in this historical replay. The new version ALSO lets trades enter later on Fridays, so the gain is NOT solely due to removing forced exits.
- **Lower drawdown among main historical favorites:** $9 rearm + BE SL activation after +Gold $6, **+$813.185** net, max drawdown **$89.186**, 370 full TP, 271 initial hard SL, **152 modified SL exits** (not winners simply because they were stop-modified). Its original Friday-forced version was **+$730.873**, max DD $86.736, and 735 tickets.
- **Original rearm $1 TP9SL9:** **+$873.337**, 1,165 tickets, 639 full TP, 526 hard SL, max DD $142.587, versus previous forced-Friday **+$708.148** on 1,067 tickets.
- Under +$0.50 synthetic per-rollover charge and all-hours 1:100 margin risk, unforced-weekend $9 TP9SL9 remains **+$868.390**, with cumulative $90.50 synthetic swap debits; corresponding BE6 rearm9 is **+$736.685**, with $76.50 synthetic debits. All stress variants have ZERO modeled margin-call, rejection or stopout events; actual history-specific HMR and swap are not verified.

## Weekend audit, from exact entry/exit timestamps

A trade counts here if its actual UTC entry is earlier than a weekly **Friday 22:00 UTC** checkpoint and its actual exit later, irrespective of ordinary/holiday gold closure. This is a uniform **audit benchmark**, not a claim to reconstruct exact broker market-close time for every week.

| Model | Tickets spanning ≥1 Friday22 checkpoint | TP | Hard SL | Modified SL | Sum ticket net P/L, before swap |
|---|---:|---:|---:|---:|---:|
| Original rearm $1 | **37** | 19 | 18 | 0 | **−$19.324** |
| Stronger rearm $9 | **28** | 16 | 12 | 0 | +$33.853 |
| Stronger rearm $9 + BE6 | **23** | 12 | 6 | 5 | +$52.526 |

**IMPORTANT GAP-LOSS CASE on 22–24 May 2026:** original $1 rearm cohort opened **SELL 4,511.304 on Fri May 22 19:02:48.991 UTC** with intended **SL 4,520.304** (Gold $9 above entry). It closed at observed **Ask 4,545.756 on Sun May 24 22:01:30.097 UTC**: **−$34.522** on only 0.01 lot including modeled commission. This demonstrates **a stop loss set $9 away can realize far more than $9 when the market reopens beyond the stop**, even though no Friday time exit is used. The primary $9-rearm cohort's worst single hard SL was **−$11.589**, and BE6 $9-rearm **−$11.360**, across these archived years; that is NOT a guarantee about future gap losses or live execution.

## Year-end equity, exactly one account with floating mark

| Year end | Original $1 rearm, TP9SL9 | $9 rearm TP9SL9 | $9 rearm + BE after +$6 | $9 rearm + synthetic swap $0.50 and 1:100 |
|---|---:|---:|---:|---:|
| Start | $1,000.000 | $1,000.000 | $1,000.000 | $1,000.000 |
| 2020* | $936.251 | $1,012.394 | $1,013.543 | $1,001.894 |
| 2021 | $1,014.880 | $1,152.417 | $1,156.074 | $1,122.417 |
| 2022 | $1,242.775 | $1,334.407 | $1,319.448 | $1,278.907 |
| 2023 | $1,531.905 | $1,562.360 | $1,476.358 | $1,489.860 |
| 2024 | $1,681.217 | $1,661.598 | $1,531.674 | $1,576.598 |
| 2025 | $1,815.970 | $1,838.565 | $1,718.989 | $1,749.565 |
| 2026* | **$1,873.337** | **$1,958.890** | **$1,813.185** | **$1,868.390** |

*2020 partial data Jan29–Dec31; 2026 Jan1–Nov05 UTC cutoff. Some year-end snapshots have OPEN tickets: equity includes quoted unrealized P/L; the accounts do NOT restart or close positions at year-end. Only at the final 2026 cutoff all 12 models happen to have zero tickets open.*

## Matched comparison to Friday-forced-exit historical test

| Same signal/risk definition | With Friday forced | No Friday forced, Friday new trades permitted | Difference |
|---|---:|---:|---:|
| $1 rearm TP9SL9 | +$708.148 | +$873.337 | **+$165.189** |
| $9 rearm TP9SL9 | +$786.785 | +$958.890 | **+$172.105** |
| $9 rearm + BE6 | +$730.873 | +$813.185 | **+$82.312** |

The new run also admits Friday trade opportunities omitted by the older version. Therefore the table tests a **complete no-Friday-restriction policy**, not a surgical controlled change to *exits only* while holding Friday entry prohibition fixed.

## Data quality, model selection and conclusion

The old TP9SL9 plus stronger rearm9 parameters were explored on 2020–26 itself; despite each trade being executed causally without selection by its future result, these years are **not untouched independent future evidence**. Live execution can include unexpected slippage, broker queues, changes in margin requirements, account swaps, and genuine gap events worse than observed in the limited history.

**The exact user-requested experiment succeeds:** with no Friday/time forced exits and trades carried across weekend until their actual TP or SL quotes, the benchmark original and strongest rearm9 setups still had positive end-of-test net simulated P/L. The best observed one-continuous-account result is **+$958.890** (swap-free assumed), versus **+$868.390** under the specified synthetic carry-cost and HMR stress. Drawdown/worst gap and broker-realization risk must accompany this profitability claim.

## Primary audit links and evidence

- New GitHub Actions successful replay: https://github.com/davidamerson/suresh/actions/runs/42050760343
- New source: https://github.com/davidamerson/suresh/blob/major-sr-tp-sl-only-weekend-hold-20261105/ph1_backtest/major_sr_tp_sl_only_weekend_hold_2020_2026.py
- GitHub Actions artifact `MajorSR-TP-SL-Only-WeekendHold-2020-2026`: `model_summary.csv`, `ticket_ledger.csv`, `continuous_annual_equity.csv`, `open_positions_at_cutoff.csv` (empty at last tick), `provenance.json` (84 source ZIP SHA256), `execution.log`.
- Previous Friday-closure backtest: https://github.com/davidamerson/suresh/actions/runs/42043857036
- Exness stop-loss docs: https://get.exness.help/hc/en-us/articles/360017263680-Setting-stop-loss-SL-and-take-profit-TP
- Exness swap docs: https://get.exness.help/hc/en-us/articles/360014709151-About-swap
