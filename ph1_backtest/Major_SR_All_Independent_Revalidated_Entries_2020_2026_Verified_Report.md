# XAUUSD: ALL causally independent Major S/R crossings and same-level revalidations (2020–2026)

**Verified 2026-11-05.** Complete GitHub Actions run: https://github.com/davidamerson/suresh/actions/runs/42035171874, **SUCCESS**. All results below are independently audited from downloaded `model_summary.csv`, `ticket_ledger.csv`, `continuous_annual_equity.csv` and `provenance.json`. This is a simulation, not a broker/live-fill statement.

## Hypothesis specified BEFORE this run

Test whether the known TP90/SL90 system remains profitable when EVERY causally distinct, *within-the-defined-system* confirmed resistance/support breakout is eligible. **Do NOT impose one trade per day, one trade per regional opening, or one trade for life of an S/R level.** Never use future trade P/L to filter entries. Preserve the earlier winning strategy's data inputs and management: $1,000 **one continuous account**, profit never withdrawn, no extra deposits, **0.01 lot = 1 troy oz**, historical Exness Raw Spread Bid/Ask, $0.07 modeled roundtrip commission, Major Resistance tick-cross → BUY, Major Support tick-cross → SELL, both Gold $9 TP and Gold $9 SL (user's 90 diagram pips), exact historical regional first H1 at Sydney 08, Tokyo 09, London 08, New York 08 in local DST-aware time. Freeze **all causally eligible source levels** at end of each completed regional-opening H1: most recently *confirmed* 2L2R UTC D1 swing high and low, and most recent *fully completed UTC weekly* high and low (maximum 2 Resistances + 2 Supports per regional opening). No manual future-chart level selection. This includes all opportunities **inside this preexisting source definition**; it is not a claim to detect every possible subjectively drawn historical market S/R level.

### Fully objective definition of a separate/revalidated entry

A new genuine observed Bid tick cross of an eligible frozen level can trigger a ticket. Two same-direction S/R prices within **Gold $1.00** count as **one S/R zone**; a quote flicker or regional-session overlap in that same zone does not create another trade. A previous trade in that same zone must be **closed**, and a later **fully completed UTC H1 bar** must have closed at least **Gold $1.00** back on the origin side (below Resistance or above Support) before the subsequent real Bid recross can open another ticket. That can occur multiple times **on the same day**, in the same session, and even within hours. Different independent S/R zones farther than $1.00 apart can run simultaneously, subject to margin. No per-day cap, no lookahead, and S/R registry persists across days, months and years.

A separate, **pre-specified** conservative revalidation version requires an H1 close **Gold $9.00** on the prebreak side, so the sensitivity to the new rearm rule is visible. Another control uses only the original nearest S/R candidate per direction, but with the same $1 rearm. This is NOT optimization over historical performance; results for all conditions are disclosed.

### Financial modelling constraints

- Swap-free applies **only if account status qualifies**, not to every Exness Raw Spread XAUUSD account. $0.50 per standard overnight rollover per 0.01 lot (Wednesday triple) is a disclosed synthetic debit, **NOT** actual 2020–2026 historical account-specific swap rates.
- Model 30% Exness margin-call notification, 0% stop-out, 1:2000 margin reference; independently stress 1:100 leverage **at all hours**, not false claim to model exact historical HMR events. Exact broker fills, account-specific dynamic swaps, real order queue, holiday variations, server-time D1 definitions and some slippage remain uncertain.
- Early closure policy Fri 12:00 UTC, and Thu 12:00 UTC before known public observed-Friday holidays, alternatively all Thu 12:00 and no Friday trades. First actual archived Bid/Ask fill after cutoff, not synthetic price. Every ticket's actual timestamps checked: no weekend carry in any scenario.

## Main final answer

**YES**, the expanded causal event enumeration on a continuous one-$1,000 account remained historically profitable, **but it was NOT more profitable than the original daily-restricted rule**. More trades increased risk/drawdown and substantially increased losing trades, showing that not every allowed entry offers equal expectancy.

| Replay rule | Opened = Closed | TP | SL | Time-forced exits | TP/SL win % | Final account equity | Net P/L | Worst continuous drawdown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **All 4 S/R source candidates, $1 H1 rearm, swap-free, Fri12 holiday-aware** | 1,067 | 558 | 465 | 44 | 54.5455% | **$1,708.148** | **+$708.148** | $222.741 |
| Same all-level $1 rearm, **synthetic $0.50 overnight swap and 1:100 HMR stress** | 1,067 | 558 | 465 | 44 | 54.5455% | $1,592.648 | +$592.648 | $253.741 |
| Same all-level $1 rearm, **additional adverse $0.05 entry AND exit slippage** | 1,067 | 552 | 471 | 44 | 53.9589% | $1,595.409 | +$595.409 | $233.322 |
| All 4 levels, $1 H1 rearm, **every Thu12 close & Friday OFF** | 880 | 464 | 388 | 28 | 54.4601% | $1,618.452 | +$618.452 | $174.662 |
| All 4 levels, **$9 confirmed H1 rearm** not $1, swap-free Fri12 | 735 | 402 | 304 | 29 | 56.9405% | $1,786.785 | +$786.785 | $121.491 |
| Original nearest-source selection only, $1 H1 rearm, swap-free Fri12 | 1,013 | 524 | 445 | 44 | 54.0764% | $1,587.333 | +$587.333 | $213.626 |

Across **all six profiles**:
- **0 modeled stop-outs**, **0 modeled margin rejections**, **0 margin-call events**; **0 open tickets** at end-of-test; **0 tickets spanning a Friday 22:00 UTC weekly close** in audited ticket ledger.
- The primary all-level $1 rearm accepted **1,067 distinct executed ticket entries**, from **347 historically registered S/R price zones**, of which **720 were genuine revalidated repeated trades** after a previous ticket in that zone had already closed. Post-run ticket audit verified **0 repeated entries without an earlier closed same-zone ticket** and **0 same-zone concurrent open overlaps**, in EACH of six model profiles.
- **235 UTC days had >= 2 orders**, maximum **12 tickets in one day**; same-day same-price/side S/R repeated-ticket groups numbered **200**. The original per-day restriction is genuinely absent.
- Maximum simultaneous open independent orders: **2**, observed naturally, not an imposed per-account cap.
- All four sources contributed entries: confirmed D1 resistance 284, confirmed D1 support 279, completed-week support 255, completed-week resistance 249 for the primary case. (Some event candidates within Gold $1.00 are clustered as one effective S/R zone.)
- **173,503 eligible crossing attempts were suppressed** after registry evaluation as unarmed repeat/active-zone duplicates; they represent flickering/overlapping quote signals, **not 173,503 independent valid opportunities**. Total raw candidate tick-cross attempts 174,570; filled tickets 1,067.
- Because positions trade Gold $9/$9, the ledger trade P/L is consistent with the continuous account equity **after netting swap debits** and with end-of-test zero open tickets.

## Head-to-head with the PRIOR tested one-S/R-per-day system (same account and risk hours)

| Restriction | Preexisting single account result | New expanded event result | Change |
|---|---:|---:|---:|
| **Holiday-aware Fri12/preholiday Thu12, swap-free, 1:2000** | 670 tickets, +$885.442, max DD $104.876 | 1,067 tickets, +$708.148, max DD $222.741 | **+397 tickets; −$177.294 profit; +$117.865 max DD** |
| **Every Thu12 flat / no Friday, swap-free, 1:2000** | 533 tickets, +$795.162, max DD $90.173 | 880 tickets, +$618.452, max DD $174.662 | **+347 tickets; −$176.710 profit; +$84.489 max DD** |

**Important:** The user-requested "every independent entry" approach was tested as designed. Its historical profit remained positive but **deteriorated** versus fewer entries under matched cost and Friday settings. Fewer trades do not imply hindsight-cherry-picking: the old restriction was an ex-ante mechanical rule; the new entries also use ex-ante mechanical rules, but have weaker average model expectancy. Do not silently switch to the $9 rearm just because it happened to show a better historical result; it is a predeclared stress/control variant and itself adds a new parameter requiring future validation.

## One continuous account year-end equity (no resets, no withdrawals)

| At year end | All-candidate $1 H1 rearm swap-free | Same with synthetic $0.50 overnight + all-hours 1:100 leverage |
|---|---:|---:|
| Start | $1,000.000 | $1,000.000 |
| 2020* | $845.884 | $833.384 |
| 2021 | $854.226 | $819.226 |
| 2022 | $1,102.152 | $1,037.152 |
| 2023 | $1,295.511 | $1,211.011 |
| 2024 | $1,467.122 | $1,362.622 |
| 2025 | $1,621.938 | $1,509.938 |
| 2026* | **$1,708.148** | **$1,592.648** |

*Source begins Jan29 2020 and ends Nov05 2026 at 09:12:23.770 UTC. Notice large fall in 2020 and very small growth in 2021 under the more permissive entry strategy, despite longer-term recovery. Primary lowest realized/marked simulated equity **$796.711** (stress **$764.711**); future losses or macro regime changes could be much worse.*

## Why “independent” is defined narrowly

**Independent trade triggers** are rigorously separated by S/R price-zone, completed H1 rearm and closing the prior position, and session overlap is deduplicated. However **statistical independence of returns is NOT proved**: the same trend, risk regime, macro shock or gold liquidity episode can affect many distinct S/R events. Counting 1,067 broker tickets as 1,067 completely independent statistical experiments would overstate evidence.

The TP90/SL90 choice was **already selected from extensive tests on the 2020–2026 period**. This newer test freezes it and enumerates all user-requested entries without choosing trades based on future outcome, but cannot retroactively make 2020–2026 an untouched out-of-sample dataset. Further prospective data required.

## Audit and source

- Successful GitHub Actions 296,709,207 XAUUSD Bid/Ask tick replay: https://github.com/davidamerson/suresh/actions/runs/42035171874
- Full code: https://github.com/davidamerson/suresh/blob/major-sr-all-independent-repeat-levels-20261105/ph1_backtest/major_sr_every_independent_opportunity_2020_2026.py
- Repository branch: `major-sr-all-independent-repeat-levels-20261105`.
- Full downloadable GitHub artifact named `MajorSR-AllIndependentRepeated-2020-2026` with `model_summary.csv`, `continuous_annual_equity.csv`, `ticket_ledger.csv`, `provenance.json` (84 monthly/daily input ZIP SHA256, timestamps, source URLs), and `execution.log`.
- The user can also download that exact artifact from the chat-created attachment if available.
- Comparison baseline, zero weekend carry: https://github.com/davidamerson/suresh/actions/runs/42028767817
- Prior GitHub report: https://github.com/davidamerson/suresh/blob/major-sr-continuous-1000-dedup-friday-swap-hmr-20261105/ph1_backtest/Major_SR_Continuous_1000_2020_2026_Final_Verified_Report.md

## Final interpretation

The user's hypothesis that the S/R strategy can generate **many additional legitimate re-entries**, including several in one day and recurring at the same level, is **verified in the historical simulated feed**: 720 repeated valid entries and 235 multi-trade days.

The stronger hypothesis that **taking every such independent re-entry increases profitability** is **not supported by this 2020–2026 replay**: base net P/L fell $177.294 and max DD rose $117.865 versus the previous capped scheme, on matched Friday costs and a continuous $1,000 account.

The broadened system remains a candidate profitable strategy under tested simulation conditions, *not a guarantee of future results*. Additional costs are stress assumptions rather than complete historical broker event data.
