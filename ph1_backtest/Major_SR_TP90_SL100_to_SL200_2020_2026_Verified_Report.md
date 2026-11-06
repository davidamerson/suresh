# XAUUSD Major S/R TP90 vs SL100–SL200 — Verified 2020–2026 Full Tick Replay

**Verified 2026-11-06** from a successfully completed [GitHub Actions run](https://github.com/davidamerson/suresh/actions/runs/42141147633), with secondary independent validation from the archived `model_summary.csv`, `ticket_ledger.csv`, annual account snapshots and ZIP provenance report. The analysis is a historical simulation, not verified broker executions.

## Exact experiment requested

Discard the extra second 0.01 lot add-on completely. Run the SAME Major Support/Resistance single-entry TP90 strategy **separately** under user-specified SL levels **100, 110, 120, 130, 140, 150, 160, 170, 190, 200**. Treat the user's `S140` as `SL140`; **SL180 was not requested and was not tested**. Re-run original **SL90 as control**, so the runner holds **11 full independent portfolios**. **TP90 stays fixed** for each.

Keep absolutely unchanged from previous verified system:
- User's XAUUSD *diagram* pip measurement: 10 diagram pips = Gold **$1.00**. TP90 = Gold **$9.00**. SL90 = $9, SL100 = $10, SL190 = $19, SL200 = $20 of entry-price distance. Actual bid/ask spread and stop gaps affect financial result.
- Real archived Exness XAUUSD Raw Spread **Bid and Ask quote ticks**: **296,709,207 quotes**, 84 archived source ZIPs, **2020-01-29 00:00:00.952 UTC** to **2026-11-05 09:12:23.770 UTC**. Input ZIP source URLs, SHA256 hashes and observed tick coverage in `provenance.json`.
- Exactly the same major S/R opportunity rules: previous **fully completed UTC week** high/low, most recent confirmed **2-left,2-right D1 pivot** high/low, levels frozen after first fully completed **H1 candle** of Sydney 08, Tokyo 09, London 08 and New York 08 local opening with real timezone/DST, buy real tick cross above confirmed resistance at Ask, sell real tick cross below confirmed support at Bid. All causally eligible different sources allowed, not restricted to nearest. Close S/R sources within Gold **$1.00** form one duplicate zone. Same-zone reentry may be traded after the old order is CLOSED, a complete UTC H1 candle has closed **Gold $9.00** on prebreakout side, and a new observed true tick crossing arrives. Unlimited independent qualifying trades per day/session.
- No add-on orders, no martingale, no averaging, no break-even or trailing stops, one **0.01 lot (one troy ounce)** per entry. **$1,000 continuous account**, no withdrawals/deposits/annual equity reset, $0.07 modeled round-trip commission per 0.01 lot, observed Bid/Ask spreads.
- **NO Friday forced exits, no Thursday/holiday forced closes, NO Friday new-entry restriction; weekend and year-end carry permitted.** Trades close **only at TP or SL** on next actual archived executable Bid/Ask tick, including gaps (loss may exceed nominal SL). Any positions still open at cutoff would remain marked open, never force liquidated by the report.
- Swap-free assumed **conditionally** (only if account actually eligible), 1:2000 leverage reference and modeled free-margin constraints, modeled 0% equity broker stopout contingency. Historical account-specific actual swaps, variable historical Exness HMR, price queue/fill latency unavailable and NOT invented.

## Full 11-profile results verified against trade-by-trade realized P/L

| TP90 with SL | Completed trades | TP wins | SL losses | Win rate | Loss rate | Net profit USD | Final equity USD | Max DD USD | Worst realized single trade | Avg actual SL loss | Longest position holding (h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **SL90** (previous control) | 793 | 454 | 339 | 57.25% | 42.75% | +$958.890 | $1958.890 | $98.253 | −$11.589 | −$9.131 | 141.50 |
| **SL100** | 791 | 474 | 317 | 59.92% | 40.08% | +$1021.106 | $2021.106 | $120.398 | −$11.901 | −$10.132 | 141.50 |
| **SL110** | 788 | 487 | 301 | 61.80% | 38.20% | +$995.678 | $1995.678 | $132.996 | −$12.418 | −$11.140 | 141.50 |
| **SL120** | 784 | 500 | 284 | 63.78% | 36.22% | +$1019.687 | $2019.687 | $136.621 | −$12.799 | −$12.131 | 141.50 |
| **SL130** | 779 | 514 | 265 | 65.98% | 34.02% | +$1109.055 | $2109.055 | $151.614 | −$14.821 | −$13.136 | 141.50 |
| **SL140** | 774 | 520 | 254 | 67.18% | 32.82% | +$1054.405 | $2054.405 | $133.035 | −$14.821 | −$14.131 | 141.50 |
| **SL150** | 774 | 525 | 249 | 67.83% | 32.17% | +$902.609 | $1902.609 | $153.744 | −$32.861 | −$15.203 | 141.50 |
| **SL160** | 769 | 531 | 238 | 69.05% | 30.95% | +$883.612 | $1883.612 | $176.161 | −$32.861 | −$16.211 | 141.50 |
| **SL170** | 759 | 540 | 219 | 71.15% | 28.85% | +$1048.368 | $2048.368 | $148.855 | −$32.861 | −$17.232 | 173.51 |
| **SL190** | 743 | 550 | 193 | 74.02% | 25.98% | +$1202.160 | $2202.160 | $176.404 | −$32.861 | −$19.219 | 247.15 |
| **SL200** | 740 | 552 | 188 | 74.59% | 25.41% | +$1130.155 | $2130.155 | $209.402 | −$32.861 | −$20.209 | 247.15 |

**Direct conclusions from this SAME historical sample:**
- The **highest net P/L** among all 11 variants is **TP90/SL190: +$1,202.160**, 550 full TP vs 193 hard SL, **74.02% win rate**, max historical equity drawdown **$176.404**.
- Previously tested original **TP90/SL90** returns **exactly +$958.890, 793 trades, 454 TP / 339 SL, max DD $98.253** — full independent baseline reproduction. Thus SL190 gave **+$243.270 more profit (+25.37%)**, but max DD rose **+$78.151 (+79.54%)**.
- **TP90/SL130**, a middle case, earned **+$1,109.055**, win rate **65.98%**, max drawdown **$151.614**. That is **+$150.165 net over original**, but DD **+$53.361**.
- **TP90/SL200** had the **highest win rate, 74.59%**, but lower net **+$1,130.155** versus SL190 and the **worst DD $209.402**. Higher winning rate is NOT equivalent to highest profit or lowest risk.
- On narrow risk efficiency metric `cumulative net profit / max historical dollar drawdown` for illustrative internal comparison: SL90 **9.76**, SL130 **7.32**, SL190 **6.82**. This simple ratio does NOT replace proper risk measures and is not a forward forecast. It makes clear wider stops give up drawdown efficiency.
- **Exposure durations and candidate counts changed causally** as SL widened: SL90 793 entries (432 repeat entries); SL190 **743 entries (382 repeat entries)**; SL200 740. Original common 361 unique effective S/R zones. Longer-staying positions block some valid same-zone re-entries; mechanically plugging larger SLs into the original 793-ticket ledger would NOT reproduce this experiment.
- All 11 ledgers independently summed and matched the 11 model-summary net P/Ls to within **$0.002**; ticket counts and TP/SL reasons matched. Across all 11, **8,494 completed trades, all exclusively TP or SL**, **zero Friday/time forced exits, zero broker stop-out events, zero modeled margin-call events, zero rejected margin entries, and zero positions left open at the dataset cutoff**. Max observed concurrent orders per model: 3.
- **Quote-jump and stop gap risk:** for SL150 through SL200, worst single realized 0.01lot loss was **−$32.861** despite a $15–$20 nominal stop. Ticket ledger verifies this case was **SELL 4021.705 entered 2026-07-14 06:40:30.884 UTC and exited at Ask 4054.496 on 2026-07-14 12:30:01.645 UTC**, an intraday quote jump (NOT a weekend event). The next recorded executable quote can cross far beyond planned SL in fast markets or across market closures. SL190 average realized loss was **−$19.219**, versus SL90 **−$9.131**.
- Break-even win probability for ideal nominal Gold +$9 TP and −$19 SL is **19/(19+9) ≈ 67.86% BEFORE real spreads, commissions and gaps**; observed historical SL190 TP fraction **74.02%**. That does not guarantee forward expectancy.

## Selected continuous annual year-end EQUITY (one initial $1,000 per portfolio; never reset)

| Year-end | SL90 control | SL130 | SL190 | SL200 |
|---|---:|---:|---:|---:|
| Start | $1,000.000 | $1,000.000 | $1,000.000 | $1,000.000 |
| 2020* | $1012.394 | $1023.247 | $973.257 | $947.252 |
| 2021 | $1152.417 | $1154.635 | $1115.090 | $1152.212 |
| 2022 | $1334.407 | $1388.651 | $1402.099 | $1419.173 |
| 2023 | $1562.360 | $1674.863 | $1661.669 | $1665.192 |
| 2024 | $1661.598 | $1768.908 | $1789.564 | $1769.192 |
| 2025 | $1838.565 | $1957.942 | $2022.902 | $1967.287 |
| 2026* | $1958.890 | $2109.055 | $2202.160 | $2130.155 |

*2020 is partial starting January 29, and 2026 partial through November 5 UTC. Accounts are NOT closed or reset at calendar-year ends; several year-end equities include UNREALIZED OPEN position marks. For instance at 2020 year-end SL190 account equity **$973.257**, SL200 **$947.252**, which is lower than the original $1,000.*

## Critical limitation — past fitted parameters are NOT a clean future-proof test

The user's core Major S/R and TP90 plus strong $9 H1 rearm were previously selected after extensive trials on *these very same years*. Even though every individual trade was decided without future price information, comparing 11 stop distances and picking the best based on 2020–26 net P/L is still **in-sample multiple testing**. SL190 could be the historical best by chance. It must be frozen before a genuinely new, future, untouched dataset or demo forward trading can test the difference from SL90/SL130 fairly.

An Exness-specific account's 2020–2026 swaps, high-margin requirement changes and actual live order execution slippage are unknown. The main models assume eligible swap-free status, use archived provider Bid/Ask and model $0.07 roundtrip commission. Under non-swap-free conditions or larger market-opening gaps the ranking can change.

## Auditability and reproducing full test

- [Verified full GitHub Actions run](https://github.com/davidamerson/suresh/actions/runs/42141147633) and attached artifact `MajorSR-TP90-WiderSL100to200-2020-2026`, with:
  - `ticket_ledger.csv`: 8,494 ticket-level entry/exit timestamps, session, buy/sell, source S/R, net after modeled commission, prior reentry flag;
  - `model_summary.csv`: all 11 model P/L and risk/entry counters;
  - `continuous_annual_equity.csv`: annual no-reset marked cash/equity and open ticket count;
  - `open_positions_at_cutoff.csv`: empty in this run;
  - `provenance.json`: 84 source ZIP URLs, source SHA256, quote counts and coverage;
  - `execution.log`: downloaded archives and full year-end/final model tables.
- [Exact GitHub Python source](https://github.com/davidamerson/suresh/blob/major-sr-tp90-sl100-to-sl200-sweep-20261106/ph1_backtest/major_sr_tp90_sl100_to_sl200_weekend_hold_2020_2026.py).
- Original prior TP90/SL90 replay benchmark [verified run](https://github.com/davidamerson/suresh/actions/runs/42071221763).

**Interpretation:** The user's wider-SL experiment produced genuinely more profitable historical candidates (especially SL190), but with a meaningful increase in maximum drawdown and worst individual losing trades, while remaining in-sample. No claim of guaranteed future profit.
