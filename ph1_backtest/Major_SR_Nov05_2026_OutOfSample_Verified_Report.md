# Out-of-sample November 5, 2026 XAUUSD Major S/R Trading System Review

**Audit execution:** [GitHub Actions successful run](https://github.com/davidamerson/suresh/actions/runs/42002283333) at 2026-11-05T09:26 UTC. The existing fixed Major S/R rules were not re-optimized for the new quote data.

## User screenshot inspection
- User-supplied MetaTrader 4 Exness-Trial9 Demo XAUUSD H1 screenshot, Market Watch ~09:12:24, 5 Nov 2026, show Bid **4133.161**, Ask **4133.241**, spread **0.080** gold price, last candle H1 OHLC **4126.823 / 4134.984 / 4124.848 / 4133.161**. Visible hand-drawn blue horizontal line near **4040.150** is NOT the calculated algorithmic major S/R level.
- Screenshot is from a **Demo XAUUSD** quote server, whereas the independent historical test is an archived **Raw Spread** quote feed. Prices and fills may differ. The quote stream itself ends at **2026-11-05 09:00:59.281000+00:00** with Bid **4126.649** and Ask **4126.729**, around 11 minutes earlier than the screenshot. No claims about subsequent ticks.
- The verified available S/R structure at that feed cutoff was previous completed UTC week High **4083.044**, Low **3870.055**, latest confirmed 2L2R daily High **4083.044**, Low **3870.055**. Current gold is already above those prior resistance levels; **no fresh untriggered resistance breakout** was established at the final available tick. There is **NO verified live/new entry** from this still screenshot.

## Truly unseen tick-replay window

- Training/research had previously ended **Oct 29, 2026 23:59:59 UTC**; enabled hypothetical trades ONLY after **2026-10-30 00:00:00 UTC**.
- Warm-up October 1–29 data was used ONLY to seed prior completed UTC weeks and confirmed 2L2R daily pivots, with zero warm-up orders.
- Oct 30 raw ticks from full October monthly ZIP, Nov 1–4 ticks from November partial monthly ZIP, Nov 5 raw ticks from separately updated Nov 05 DAILY ZIP, no duplicated day-05 ticks between two archives. The last daily file contained quotes until **2026-11-05 09:00:59.281000+00:00**. This is an *as-of* snapshot, not proof of data availability through the screenshot.
- **1,480,901 new ticks** since October 30; **7,055,606 total tick records including October warm-up**, all real Bid/Ask.
- Two previously selected strategies (not chosen using Nov outcomes) replayed without rule changes: MOMENTUM EQ TP90/SL90 (Gold $9.00/$9.00); MOMENTUM 2:1 TP100/SL50 (Gold $10.00/$5.00), both BUY on actual frozen Resistance cross, SELL on Support cross, first observed tick-cross per local session opening after its first H1 completes; 0.01 lot =1 oz, model $0.07 commission/roundtrip, no withdrawals, initial notional $1,000 (not user's real Demo $197.11).
- Four original regional opening windows can overlap and place **multiple orders on exactly the same observed tick**. The original simulator permits these overlaps; they are **not independent forecasts**.

## Headline outcomes using the ORIGINAL multiple-session order rule

| Selected system | Opened | Closed | TP Wins | SL Losses | Closed win rate | Simulated realized P/L | Open as of tick cutoff |
|---|---:|---:|---:|---:|---:|---:|---:|
| TP90/SL90 | 7 | 7 | 7 | 0 | 100% | **+$62.51** | 0 |
| TP100/SL50 | 7 | 7 | 6 | 1 | 85.71% | **+$54.505** | 0 |

All entries and exits in the uploaded GitHub artifact's `individual_trades.csv`. Model commissions and original Bid/Ask quoted spread included. No swap or broker-specific demo server execution guarantees.

## Exact unique entry events (deduplicated by same timestamp, side and fill)

| Date and entry UTC | Boundary | Side | Executed entry price | TP90/SL90 exit and result | Number of overlapping session orders |
|---|---:|---|---:|---|---:|
| 2026-10-30 07:49:20.856000+00:00 | 3975.495 | SELL | 3975.390 | 3966.390 TP / +$8.93 | 3 |
| 2026-10-30 10:47:36.248000+00:00 | 3975.495 | SELL | 3975.493 | 3966.493 TP / +$8.93 | 1 |
| 2026-11-05 00:30:17.961000+00:00 | 4083.044 | BUY | 4083.210 | 4092.210 TP / +$8.93 | 3 |

**These 7 separate broker orders represent ONLY 3 unique tick entry moments and 2 distinct S/R levels**, not seven independent market opportunities.
- Unique-tick, one-ticket-only hypothetical: EQ 3/3 TP, +$26.79; 2:1 2/3 TP, +$14.785.
- If limiting to one ticket per calendar-day *and boundary level*, even the Oct30 10:47 recross trade is excluded: EQ 2 TP, +$17.86, RR2 2 TP, +$19.86. These what-if totals are simple filtering of exact trade ledgers, NOT a separate rerun with portfolio/margin-aware trade suppression, but all original trades are individually independently executed in the simulator with no remaining open tickets.

## Additional quote stress outcomes

Both selected strategies tested with unfavorable price slippage +Gold $0.05 or $0.10 **per side**, in addition to the historical Bid/Ask spread and $0.07 fee:
- 1:1 TP90SL90: all 7 TP, 0 SL, net +$62.510 under base and both modeled stresses (the execution-cost assumptions affect the trigger timing and could change future outcomes).
- 2:1 TP100SL50: 6 TP, 1 SL, net +$54.505 base, +$54.453 with $0.05/side, +$54.505 with $0.10/side. Differences come from tick gap/fill triggers; do not interpret a small positive difference in simulated net from higher slippage as guaranteed better execution.

## Decision and limitations

**Observed and simulated:** the preselected high-timeframe S/R strategy worked on this newly available, small post-Oct29 sample, including the Nov5 resistance breakout around 00:30 UTC. However the sample has just 3 distinct entry timestamps and two level-specific opportunities, far too small to validate the strategy as consistently profitable on new future data. Historical Nov trade outcomes were viewed after market movement, so this is an out-of-prior-test-date *historical forward check*, not a real-time prospective fill record.

**As-of screenshot:** at 09:00:59 UTC the last Raw Spread Bid was 4126.649, already above prior completed-week high 4083.044. The previously eligible Resistance BUY entry at 4083.21 at 00:30 UTC hit TP at 4092.21 long before this screenshot. No new entry can be inferred from screenshot's price 4133.161 without a new frozen eligible resistance and a fresh tick-cross. Mark status **NO TRADE / WAIT** under strictly verified available data, not an order recommendation.

The user screenshot is a Demo feed; archive is indicative quote feed, not proof of live execution. Read Exness's official tick-history caveat. Historical D1/W1 structure uses UTC candles, not necessarily the user's MT4 server's day/week boundaries.

## Byte-level source provenance

- `oct2026`: 5,910,062 processed quote rows, ZIP SHA256 `a131b2c531a58c5e4470f9b65afea4d7894816d7c7bfd580dba70dbe877dc981`; interval 2026-10-01 00:00:00.036000+00:00 through 2026-10-30 20:57:59.352000+00:00
- `nov_monthly_before_day05`: 981,892 processed quote rows, ZIP SHA256 `ed181642b29a1357d684763e203623d313ab76981135b0e8dfc12d08472fe834`; interval 2026-11-01 23:01:30.232000+00:00 through 2026-11-04 23:59:59.908000+00:00
- `nov05_daily`: 163,652 processed quote rows, ZIP SHA256 `858235088950c151b6b9f85ec1e5c19f6fdfedc7bc91c9592b99a376f8ec564f`; interval 2026-11-05 00:00:00.722000+00:00 through 2026-11-05 09:00:59.281000+00:00

## Reproducibility and artifacts
- GitHub Actions run: https://github.com/davidamerson/suresh/actions/runs/42002283333
- Source: https://github.com/davidamerson/suresh/blob/nov2026-major-sr-outsample-20261105/ph1_backtest/nov2026_major_sr_outsample_until_screenshot.py
- Artifacts contain precise `individual_trades.csv`, `summary.csv`, `by_side_summary.csv`, `sessions.csv`, `provenance.json` and `execution.log`.
- Branch `nov2026-major-sr-outsample-20261105`.
