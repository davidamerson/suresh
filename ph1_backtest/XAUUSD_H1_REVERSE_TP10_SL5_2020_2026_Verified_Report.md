# XAUUSD REVERSE H1 Breakout TP10 / SL5 — seven-year confirmed backtest

**Report date:** 5 November 2026 (Sri Lanka). **Status:** All seven GitHub Actions matrix jobs completed successfully. 
**GitHub Actions:** https://github.com/davidamerson/suresh/actions/runs/41893101106

## Hypothesis

The original HIGH-break BUY / LOW-break SELL strategy had only 30.83% TP hits, but a low hit rate against an asymmetric $1 TP / $0.50 SL does **not** prove a directionally opposite price edge. This test checks the reverse-entry hypothesis directly, using new execution-side TP/SL calculations and actual Bid/Ask quotes.

## Strategy rules

- Exness XAUUSD Raw Spread monthly historical tick CSV `Timestamp, Bid, Ask`; 295,225,516 observed quotes. 2020 from Jan 29 only; 2026 through Oct 29 only.
- Regional market opens: Sydney 08:00 local, Tokyo 09:00, London 08:00, New York 08:00, using historical timezones and DST. Read each first **completed** H1 Bid candle high/low.
- **Reverse trigger**: first subsequent Bid quote strictly **above H1 High = SELL** at available Bid; first subsequent Bid quote strictly **below H1 Low = BUY** at available Ask. Exactly one first-break order opportunity per session opening; ignore subsequent breaks until next same-session open. Four sessions can overlap.
- TP **10 user diagram pips = Gold $1.00**; SL **5 user diagram pips = Gold $0.50**, *measured from actual reverse entry quote*, not simply complemented prior results. Official Exness pip = Gold $0.01 and is NOT this report's pip unit.
- Fixed 0.01 lot = 1 oz, annual starting balance **$1,000** independently reset per calendar year, example leverage 1:2000, profits retained; **no withdrawals**.
- Actual archived bid/ask for simulated entry and exits, modelled roundtrip commission $0.07 per 0.01 lot. No extra slippage for primary run; adverse +$0.05 per side variant separately. TP limit capped at exact target, SL at first observed executable quote including possible gaps. No discretionary close, no Friday forced close, no martingale, no averaged positions.
- Data are broker quote history not proven executed live fills; swaps, high margin requirements, network latency and requotes are not comprehensively modelled.

## Verified raw quote replay — primary run

| Year | Closed | TP (wins) | SL (losses) | Win % | Loss % | Annual model net P/L |
|---|---:|---:|---:|---:|---:|---:|
| 2020* | 903 | 144 | 759 | 15.95% | 84.05% | $-429.561 |
| 2021 | 964 | 249 | 715 | 25.83% | 74.17% | $-192.463 |
| 2022 | 967 | 269 | 698 | 27.82% | 72.18% | $-165.014 |
| 2023 | 963 | 273 | 690 | 28.35% | 71.65% | $-157.292 |
| 2024 | 969 | 302 | 667 | 31.17% | 68.83% | $-116.737 |
| 2025 | 959 | 261 | 698 | 27.22% | 72.78% | $-176.923 |
| 2026* | 805 | 231 | 574 | 28.70% | 71.30% | $-166.897 |
| **Total** | **6530** | **1729** | **4801** | **26.48%** | **73.52%** | **$-1404.887** |

*2020 partial from Jan29; 2026 partial through Oct29. The annual P/L is the total of seven **separate starting-$1,000 annual simulations** and is not one continuous portfolio's net.*

## Sensitivity, +$0.05 adverse execution per side

| Year | TP | SL | Win % | Net annual model P/L |
|---|---:|---:|---:|---:|
| 2020 | 113 | 790 | 12.51% | $-491.243 |
| 2021 | 188 | 776 | 19.50% | $-286.859 |
| 2022 | 201 | 766 | 20.79% | $-267.474 |
| 2023 | 209 | 754 | 21.70% | $-254.569 |
| 2024 | 234 | 735 | 24.15% | $-220.850 |
| 2025 | 210 | 749 | 21.90% | $-254.298 |
| 2026 | 187 | 618 | 23.23% | $-241.436 |
| **Total** | **1342** | **5188** | **20.55%** | **$-2016.729** |

## Direct apples-to-apples comparison (same entry signal, inverted order)

| Rule | TP | SL | Win % | Loss % | Sum of independent annual model net P/L |
|---|---:|---:|---:|---:|---:|
| Original breakout: High BUY / Low SELL | 2,013 | 4,517 | 30.83% | 69.17% | −$912.525 |
| **Reverse fade: High SELL / Low BUY** | **1,729** | **4,801** | **26.48%** | **73.52%** | **−$1,404.887** |

The reverse fade has **4.35 percentage points LOWER TP hit rate** and **$492.362 greater summed annual simulated loss** than the original directional breakout model, despite identical TP and SL price distances. Both models fail. One model's losing trade is not necessarily an immediate profit in the opposite model because stops/targets are asymmetric and spread and exit timing differ.

For 0.01 lot the nominal exact-limit TP nets **+$0.93**, and an exactly filled SL nets **−$0.57** after $0.07 commission. A theoretical TP hit rate of **38%** breaks even absent gap losses and unmodelled costs. The reverse run hit only **26.48%**, with adverse slippage run only **20.55%**.

## Provenance and implementation

- New branch: `h1-reverse-tp10-sl5-sevenyears-20261105`.
- Script: https://github.com/davidamerson/suresh/blob/h1-reverse-tp10-sl5-sevenyears-20261105/ph1_backtest/h1_firstbreak_reverse_tp10_sl5_2020_2026.py
- Workflow: https://github.com/davidamerson/suresh/blob/h1-reverse-tp10-sl5-sevenyears-20261105/.github/workflows/h1-firstbreak-reverse-tp10-sl5-sevenyears-20261105.yml
- Successful run: https://github.com/davidamerson/suresh/actions/runs/41893101106
- For each year, Actions artifact `H1-FADE-TP10-SL5-YEAR` includes `summary.csv`, `sessions.csv`, `individual_trades.csv`, `daily_realized_PnL.csv`, `provenance.json`, `execution.log`.
- All values were extracted from final, successful raw GitHub Actions job logs. Total tick count 295,225,516. Both variants report 6,530 closed trades, zero margin rejections, and no open positions at year-end.

**Research conclusion:** The tested immediate fade of first regional H1 break, TP10/SL5, **does not show a positive cost-adjusted advantage**. This historical result does not prove that all future reverse or filtered fade strategies fail, nor does the previous breakout loss rate demonstrate a general market direction bias.
