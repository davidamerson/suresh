# VERIFIED — XAUUSD Major S/R: add second same-direction trade at adverse 80 pips, TP180/SL10

**Completed and audited 5 November 2026.** [Successful GitHub Actions run](https://github.com/davidamerson/suresh/actions/runs/42076799361). [Exact source code](https://github.com/davidamerson/suresh/blob/major-sr-adverse80-add-second-tp180-sl10-20261105/ph1_backtest/major_sr_adverse80_two_order_basket_2020_2026.py).

## User hypothesis and locked assumptions

- Gold dollar-price units use user **diagram pip**: 10 pips = Gold **$1.00**, 80 pips = **$8**, 90 pips = **$9**, 180 pips = **$18**. Not to be confused with some terminal-specific official XAUUSD point/pip notation.
- Preserve prior profitable Major S/R causal first-entry strategy: first completed local-opening H1 of Sydney 08, Tokyo 09, London 08, New York 08 (DST aware); freeze previous fully completed UTC weekly high/low and most recent confirmed 2L2R UTC daily swing high/low; buy actual Bid resistance tick cross (fill Ask), sell actual Bid support tick cross (fill Bid); eligible sources include all separate qualifying confirmed levels, with Gold $1 clustering to avoid duplicate same-zone entries. Existing strong Gold **$9 confirmed full H1 rearm** of same level, no one-per-day cap. These original entry rules are NOT retuned after seeing outcome.
- First original trade 0.01 lot/1 troy ounce, TP Gold +$9 and initial SL Gold −$9. Each root of the experiment starts with an unchanged 0.01 lot.
- If still-open first trade's **executable quote** (Bid on long, Ask on short) moves **Gold −$8**, yet has not touched its −$9 SL, then enter exactly **ONE** additional same-direction 0.01 lot at ACTUAL historical buy Ask or sell Bid quote; child's own TP Gold **+$18** / SL Gold **−$1** from child's actual entry fill. Trigger is *after actual tick is observed*; no mythical fill at Gold -$8 if quote jumps straight past original stop.
- All archives real observed Exness XAUUSD Raw Spread Bid/Ask prices from Jan29 2020 to Nov05 2026 **09:12:23.770 UTC**, **296,709,207** quote records from **84 SHA256-audited source ZIPs**; model commission **$0.07 per 0.01-lot ticket**. $1,000 ONE uninterrupted simulated account, no deposits/withdrawals, account equity marked continuously, original 1:2000 leverage with modeled margin rules and 0% broker-stopout contingency, full weekend/holiday carry, no Friday/time-forced closures. Swap-free assumed only CONDITIONALLY (historical user-specific actual swaps unknown).
- Critical mathematical issue: If first BUY at 4000, child entered ideally near 3992, original TP90=4009, child TP180=4010. **Both exact, simultaneously filled TP orders are impossible** without modifying one nominal TP or running them independently. Accordingly FOUR distinctly disclosed variants were separately replayed, all decided BEFORE seeing results:
  1. Original without second trade (benchmark).
  2. Each order keeps its OWN TP/SL; independent fills. May result in one TP and other SL and non-simultaneous closure.
  3. Synchronized basket: when child exists, close BOTH at original TP90 (child effective TP is ~170 diagram pips) or EITHER SL (both tickets force-close at next executable Bid/Ask quote).
  4. Synchronized basket: when child exists, hold BOTH until child TP180 (first effective TP ~100 diagram pips) or EITHER SL. This is closest to user's requested **child TP180 and synchronized close**, but *changes the first position's nominal TP90 to a basket-managed target after the add-on*.
- In both synchronized variants, first-only trades are exited at original +$9/−$9 TP/SL. Each ticket charged commission; no magic zero-spread fill. Stop may gap beyond requested level.

## Complete results: audited portfolio / per-ticket P&L

| Setup | First-entry orders | Add-on orders | Total closed orders | TP tickets | SL tickets | Basket paired TP | Basket paired SL | Net P/L (USD) | Continuous final equity (USD) | Max DD (USD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Original TP90/SL90 **no addon** | 793 | 0 | 793 | 454 | 339 | – | – | **+$958.890** | $1,958.890 | **$98.253** |
| Add at -80: OWN first TP90/SL90 + OWN child TP180/SL10 | 793 | **359** | 1,152 | 475 | 677 | 21 (but orders independent) | 336 (independent) | **+$958.469** | $1,958.469 | **$112.311** |
| Add at -80: **basket both exit at first TP90** | 793 | **359** | 1,152 | 475 | 677 | **22 / 359** | **337 / 359** | **+$968.640** | $1,968.640 | **$111.272** |
| Add at -80: **basket both exit at second TP180** | 793 | **359** | 1,152 | 473 | 679 | **21 / 359** | **338 / 359** | **+$977.400** | $1,977.400 | **$112.858** |

Note the "TP tickets" for a paired TP win counts TWO simultaneous positions. The **basket group success rate** is the more honest conditional measure: **22/359 = 6.13%** for first TP90 basket, **21/359 = 5.85%** for second TP180 basket. **SL group rate** correspondingly 93.87% and 94.15%. The independent version has **21 both TP, 336 both SL, and 2 mixed (original TP and child SL)**; only 91/359 independent pairs happened to close at an identical UTC timestamp, so independent mode does NOT satisfy user's request that both orders always close together.

### Main result: does the added second position improve first-only strategy?

- Own TP/SL independent: **−$0.421 net P/L vs baseline**, while max DD **+$14.058** worse.
- Synchronized TP at first TP90: **+$9.750** net P/L vs baseline (**+1.02% relative historical profit**); max DD increased **+$13.019** (**+13.25% relative original max DD**).
- Synchronized TP at second TP180: **+$18.510** net P/L vs baseline (**+1.93% historical profit**); max DD increased **+$14.605** (**+14.87% relative original max DD**).
- In the two basket variants 359/359 actual paired family tickets were checked to have **exactly the SAME exit UTC timestamp and the SAME TP or SL reason** (zero basket desynchronization).
- All variants **793 IDENTICAL original S/R entries** in exact UTC timestamp, entry fill, session, direction, and source, despite the different add-on exits. No selective skipping of losing roots. Every variant had **zero Friday/time exits, zero modeled stopouts, zero margin-call events and margin rejections, and zero open positions at last quote**.
- Maximum concurrent order count original **3**, with add-ons **4**. Margin requirement remains under modeled initial capital. The historically observed worst single-ticket loss remained approximately **−$11.589**, but basket losses are the sum of TWO tickets and should not be confused with single-ticket worst loss.
- Basket group worst realized negative P/L was approximately **−$10.944**; one child + one root can together have greater exposure than original single ticket. The exact worst single group is different from intratrade floating drawdown.

## Why almost all add-on baskets lose

A STRICT matched-entries audit of the 793 original root tickets and 359 triggered add-ons proves:
- Among **454 original TP90 winners**, only **23** (5.07%) were previously at adverse Gold -$8 before eventually reaching +$9. Under tighter SL80 they would have stopped.
- Among **339 original SL90 losers**, **336** (99.12%) reached adverse -$8 on an executable tick before being stopped; the remaining 3 gapped/otherwise reached original stop without valid in-between child entry.
- Thus **359 actual qualifying add-on events = 336 original losing setups + 23 original eventual winners**. This is why the second trade is placed overwhelmingly in unfavorable initial conditions. Of 23 originally recovered winners, synchronized original-TP basket succeeded in 22 and stopped 1 extra original winner; synchronized second-TP basket succeeded in only 21 and stopped 2 extra originally winning parents.
- The child order's extra profit on rare major reversals narrowly counterbalanced the frequent child's $1 stop loss, but improvement after 7 years was SMALL compared to added drawdown and possible swap/slippage fragility.

### Year-end equity comparison (one $1000 account per setup, no yearly reset)

| Year end | Original | Independent orders | First TP90 synchronized basket | Second TP180 synchronized basket |
|---|---:|---:|---:|---:|
| 2020* | $1,012.394 | $963.285 | $991.459 | $955.893 |
| 2021 | $1,152.417 | $1,073.350 | $1,104.833 | $1,071.959 |
| 2022 | $1,334.407 | $1,279.812 | $1,310.885 | $1,286.201 |
| 2023 | $1,562.360 | $1,532.126 | $1,544.179 | $1,525.817 |
| 2024 | $1,661.598 | $1,652.621 | $1,662.648 | $1,652.524 |
| 2025 | $1,838.565 | $1,815.220 | $1,823.653 | $1,819.663 |
| 2026* | **$1,958.890** | $1,958.469 | $1,968.640 | **$1,977.400** |

**Crucial robustness warning**: at the end of **2025** BOTH baskets were still less profitable than baseline (−$14.912 and −$18.902, respectively); their tiny lifetime advantage appeared **only during partial 2026**. It is inappropriate to call this robust historical outperformance of the original strategy.

## Extra modeled swap sensitivity — based on completed ticket ledgers (NOT new full replay)

If the account is *NOT actually swap-free*, applying a purely hypothetical debit of $0.50 per 0.01 lot per standard overnight rollover, Wednesday triple, to the actual fixed ticket-ledger holding intervals yields:
- Baseline weighted rollovers **181**, nominal synthetic debit **$90.50**, adjusted net **+$868.390**.
- Independent add-on weighted rollovers **202**, debit **$101.00**, adjusted net **+$857.469**.
- First-TP basket weighted rollovers **199**, debit **$99.50**, adjusted net **+$869.140**.
- Second-TP basket weighted rollovers **201**, debit **$100.50**, adjusted net **+$876.900**.

These figures are **ledger-only cost sensitivities**, not separately margin-aware/replayed synthetic-swap portfolios and not historical account-specific Exness swap rates. Under this assumed debit, second-TP basket improves baseline by only **+$8.510** across seven partial/full calendar years, while assuming otherwise unchanged fills and entries. A different actual swap/slippage environment could erase this edge.

## Verification & limitations

- The user-specified test is performed with real historical bid/ask quotes and causal setup criteria. It does not pick out the 23 future-recovering trades in advance; the same child action is taken for all 359 observed adverse -8 triggers, including 336 of the original losing trades.
- Historical quote replay ≠ broker-certified execution. Real 2020–2026 account-specific swap, exact historical dynamic HMR schedule, stop limit modifications and service-side order delay unavailable; no actual future profit guarantee.
- The base TP90/SL90 plus H1 rearm9 were chosen from multiple 2020–26 historical explorations. The latest experiment was predeclared as these 4 simulations, but is still IN SAMPLE. Do not endlessly tweak TP/basket thresholds to the same history and claim out-of-sample verification.
- Source archive URL/ZIP SHA256 for every archive in downloadable run artifact `provenance.json`. Exact first/child ticket paths and TP/SL in `ticket_ledger.csv`. Annual continuous balances in `continuous_annual_equity.csv`, and summary and execution log available as part of workflow artifact.

**Research interpretation:** the hypothesis that rare deeply adverse winners recover is confirmed (23/454 first winners), and a second position can sometimes capture extra reversal profit. However, the proposed additional order is mostly triggered on future losers; on this historical sample, *strict independent own-TP/SL exits add no net edge*, while synchronized baskets add only $9.75–$18.51 before actual historical swaps, and their max DD is 13–15% worse. Keep the original locked strategy as benchmark and treat the paired strategy as speculative until prospective validation on unseen future trading.
