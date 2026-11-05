# XAUUSD Major S/R TP90/SL90 — Verified causal loss-reduction experiments

**Completed November 5, 2026.** GitHub Actions run **SUCCESS**: https://github.com/davidamerson/suresh/actions/runs/42043857036

**Scope:** the user's proven historical candidate with NO LOOK-AHEAD at trade level: archived Exness XAUUSD Raw Spread Bid/Ask tick data, **296,709,207 quotes**, 84 source monthly/daily ZIP input snapshots from Jan 29 2020 through Nov 05 2026 09:12:23.770 UTC. Exact source ZIP SHA256/months and timestamps in `provenance.json`. Full historical tick replays of **ten PREDECLARED variants**. One continuous USD $1,000 account, 0.01 lot=1oz per order, no withdrawals, $0.07/roundtrip fee, existing causal Major S/R source and first-hour regional-opening rule, four sessions with local DST, initial original Gold $9 TP and SL (user diagram 90/90 pips), all independent daily/week higher-timeframe levels and H1 revalidated recrosses, S/R zones within Gold $1 regarded as same zone. No artificial per-day entry limit; multiple different-zone trades can overlap. Same conservative Friday noon and preholiday Thursday noon flattening. **All tested models assume account qualifies for swap-free**; account-specific historical Exness swaps, event-specific HMR and broker fill latencies remain unmodelled. Initial leverage 1:2000 with margin checks. All ten tests reported **zero modelled margin rejections, stopout liquidations and positions left open**.

A changing November 05 provider ZIP initially failed a download-integrity check; the successful rerun verified ZIP central directory and CRC and included the valid day-05 daily data through the exact comparison cutoff. Baseline reproducibility confirmed: **1,067 tickets, 558 TP, 465 hard SL, 44 Friday forced exits, +$708.148, max DD $222.741**, exact match to previous full seven-year 1,067-ticket baseline.

## Predeclared causal risk-control treatments

1. Locked original TP9 / SL9 Gold, no stop changes (benchmark).
2. Fixed initial SL Gold **$6** versus unchanged TP $9; actual next available quote might exceed SL in a gap.
3. Fixed initial SL Gold **$7** versus unchanged TP $9.
4. After favorable maximum executable quote excursion reaches **+$4.50 Gold**, advance stop to entry ± **$0.07/oz modeled fee** (net about $0 if fill exactly). Broker tick gaps may cause a small loss.
5. Same break-even logic but activate **only after +$6 Gold**.
6. Start trailing after +$6 favorable excursion with **Gold $4 trail distance** from executable-quote maximum favorable excursion; TP remains $9.
7. If a trade has been open at least **six hours** AND its current executable P/L is negative, exit immediately on current quote instead of awaiting TP or SL.
8. Previously independently predeclared stronger **H1 re-entry confirmation**: full H1 closes Gold **$9 back on the origin side** of the same S/R zone (instead of Gold $1), previous same-zone order closed, then wait for a genuine tick recross. Unlimited trades per day and repeated trades remain allowed. **This changes only re-entry requirements**, not S/R level selection or TP9/SL9.
9. Stronger rearm9 plus BE at +$6.
10. Stronger rearm9 plus $4 trailing from +$6.

Each model is replayed tick-by-tick separately (not simply rewriting previously losing trade P/L); model cash, equity, re-entry opportunities, spread/commission and prices recalc after its own exits.

## Ten-model audited summary

| Variant | Closed | TP | Hard SL | Other timed/protective exits* | Actual negative-net tickets | Avg loss on negative-net tickets | Net P/L USD | Max drawdown USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE TP9/SL9 | 1067 | 558 | 465 | 44 | 488 | $-8.848 | +$708.148 | $222.741 |
| SL6 TP9 | 1184 | 514 | 633 | 37 | 649 | $-6.047 | +$708.353 | $151.714 |
| SL7 TP9 | 1140 | 533 | 566 | 41 | 586 | $-7.001 | +$699.839 | $155.295 |
| BE after +4.5 | 1190 | 437 | 349 | 404 | 728 | $-4.500 | +$663.966 | $169.706 |
| BE after +6 | 1139 | 489 | 392 | 258 | 628 | $-5.829 | +$743.771 | $199.045 |
| Trail +6 gap4 | 1139 | 347 | 392 | 400 | 415 | $-8.798 | +$652.614 | $215.588 |
| Time cut 6h underwater | 1221 | 524 | 393 | 304 | 679 | $-6.104 | +$572.668 | $191.487 |
| REARM $9 base | 735 | 402 | 304 | 29 | 321 | $-8.800 | +$786.785 | $121.491 |
| REARM $9 + BE $6 | 735 | 331 | 240 | 164 | 393 | $-5.713 | +$730.873 | $86.736 |
| REARM $9 + trail +6 gap4 | 735 | 241 | 240 | 254 | 256 | $-8.746 | +$670.833 | $95.600 |

*Other exits include Friday closes, near-breakeven protective exits, trailing partial-profit exits and underwater time stops. Hard SL hits are NOT the count of all monetary losses. For example, a BE stop triggered at a price slightly worse than commission-inclusive zero can create a negative trade, while a protective trailing stop may create a positive exit even though not TP.*

### Primary goal A: fewer FULL hard-stop-loss tickets and improved profit

**REARM Gold $9 H1-close revalidation**: 304 hard SL hits (versus 465 baseline, **161 fewer / 34.6% fewer**); 321 actual monetary negative tickets vs 488 baseline; maximum historical drawdown **$121.491 versus $222.741** (**45.46% lower**), while annual-net continuous account profit **+$786.785 versus +$708.148**. Best combined net P/L among 10 predeclared examples on this *in-sample* history. Also trades fewer tickets (735 vs 1,067), giving up some potentially profitable repeated opportunities. Crucially this is not a complete ban on same-level re-entries or one-per-day cap: registry can rearm after an observed H1 close Gold $9 back on origin side and then another observed tick cross. It had genuine same-zone reentries.

### Primary goal B: minimize max drawdown while preserving net profit

**REARM Gold $9 plus break-even after MFE +$6**: 240 hard SL hits vs baseline 465 (**225 fewer / 48.4% fewer**); 137 protective BE stops averaged **−$0.046 each** due to next-tick executable quote gaps. Unlike a naive classification, **393 actual negative-net trade tickets** (not 240) because most near-zero BE stops have tiny negative P/L, versus baseline 488 actual negatives. Mean actual negative-ticket loss **−$5.713** vs original **−$8.848**, combined losses total **−$2,245.235** vs **−$4,317.826**, net profit **+$730.873** vs **+$708.148**, and max historical equity drawdown **$86.736** vs **$222.741** (**61.06% lower**). Worst marked equity $938.075 vs baseline $796.711. The trade-off versus REARM9 alone: net profit **$55.912 LESS**, drawdown **$34.755 LESS**, with 64 fewer hard SL hits. User can choose based on risk tolerance, but future performance unproved.

### Primary goal C: smaller initial SL dollar loss without lowering overall net P/L (historical)

TP9 / SL6: average monetary loss on all negative-ticket exits **−$6.047** vs **−$8.848**, max DD $151.714 vs $222.741, nominal single stop $6.07 instead of $9.07 (plus potential tick gaps), net P/L +$708.353 roughly baseline's +$708.148. However number of hard SL hits INCREASED from 465 to 633 and number of actual negative tickets from 488 to 649. This is smaller *each* loss, not fewer losing trades.

### BE and trail traps

- Original $1 H1 rearm plus break-even after favorable +$6: profit +$743.771, max DD $199.045; 216 protective BE exits average −$0.044 owing to tick gaps. Full hard SL 392 but actual negative tickets 628; **don't call these trades winners**.
- Earlier BE activation at +$4.5 made net profit worse (+$663.966). 362 BE stops included tiny negative fills.
- Trailing after +$6 with gap $4 reduced actual negative-ticket count (415 versus baseline 488) but also reduced combined net profit to $652.614, because many prior full TP hits became partial wins. More green trades does not imply better net expectancy.
- Exit after six hours if underwater: net only +$572.668 and 679 negative tickets. Not suitable based on this particular history.
- Combined REARM9/trailing gave 256 actual monetary negative tickets, max DD $95.600, net +$670.833. It sacrifices net P/L relative to both rearm9 alone and rearm9/BE6.

## Annual realized P/L from ONE continuous cash account (not seven $1k restarts)

| Year | BASE TP9/SL9 | SL6 TP9 | BE after +$6 | REARM9 BASE | REARM9 + BE at +$6 |
|---|---:|---:|---:|---:|---:|
| 2020* | $-154.116 | $-94.690 | $-135.274 | $-74.687 | $-46.312 |
| 2021 | $8.342 | $47.278 | $17.724 | $62.120 | $62.775 |
| 2022 | $247.926 | $173.001 | $212.596 | $214.627 | $206.353 |
| 2023 | $193.359 | $181.439 | $154.958 | $169.237 | $116.391 |
| 2024 | $171.611 | $139.650 | $127.089 | $121.222 | $95.318 |
| 2025 | $154.816 | $197.316 | $234.232 | $197.107 | $207.460 |
| 2026* | $86.210 | $64.359 | $132.446 | $97.159 | $88.888 |

*Partial 2020 from Jan29, partial 2026 to Nov5. Some annual P/Ls are negative even when the full sample is positive; the account is never reset. Exness account-specific daily swap, HMR schedule, order latency/rejections are still not historical facts available to this model.*

## Practical Exness deployment caution

Exness official docs: stop orders can be filled at NEXT available quote, not guaranteed at nominal stop; `https://get.exness.help/hc/en-us/articles/360017263680-Setting-stop-loss-SL-and-take-profit-TP`. Exness trailing stops on MT4/5 are client-terminal features; the terminal must remain running or use a VPS: `https://get.exness.help/hc/en-us/articles/360014744199-Trailing-stops`. Our dynamic BE/trailing computations assume stop changes are accepted with no network delay and no special stop-level constraints, which may be optimistic.

## Evidence limits and model-selection warning

**This experiment did NOT look ahead at individual trade outcomes to decide stops.** However the baseline TP90/SL90 and its S/R definition were originally selected by repeatedly testing the SAME 2020–26 historical dataset. Now comparing ten protective stop variants is ALSO in-sample multiple testing, even though their parameters were fixed before this runner started. A high net-profit or low DD among them **must not be sold as independently proven future performance**. The early Nov 2026 new-price segment contains only a handful of unique entries and does not provide adequate forward validation. A future genuine forward test and broker Demo EA implementation should freeze ONE or TWO hypotheses instead of endlessly retuning historical stop levels.

## Audit pointers

- Successful Actions 10-model run: https://github.com/davidamerson/suresh/actions/runs/42043857036
- Verified source code: https://github.com/davidamerson/suresh/blob/major-sr-loss-reduction-risk-controls-20261105/ph1_backtest/major_sr_loss_reduction_risk_variants_2020_2026.py
- Artifact `MajorSR-TP90-LossReduction-10Variant-2020-2026` includes every closed-ticket entry/exit `ticket_ledger.csv`, `model_summary.csv`, continuous yearly equities, `provenance.json` (84 source ZIP SHA256), execution logs. 0 rejected margins or model stopouts; 0 remaining positions at the end.
- Baseline comparison original all-independent-entry (confirmed exactly): https://github.com/davidamerson/suresh/actions/runs/42035171874
