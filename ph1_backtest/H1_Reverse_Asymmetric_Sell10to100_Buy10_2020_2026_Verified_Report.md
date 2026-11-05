# XAUUSD Reverse H1 High-SELL TP/SL 10–100 and Low-BUY fixed 10/10: full verified comparison

**Research date:** 5 November 2026 (Sri Lanka time). **All 7 GitHub Actions jobs completed successfully:** https://github.com/davidamerson/suresh/actions/runs/41966274025

## Hypothesis and exact setup
10 independent variants with first completed local-market H1 high/low signal, only the high-break **SELL** target and stop vary in lockstep from 10 to 100 user diagram pips (Gold price from $1 to $10). The low-break **BUY TP10/SL10 stays exactly Gold $1/$1 in all 10**.

- Sessions: Sydney 08:00, Tokyo 09:00, London 08:00, New York 08:00, each local timezone with historical DST.
- After first complete H1 Bid candle, first subsequent observed **Bid above H1 high** triggers SELL at Bid; first **Bid below H1 low** triggers BUY at Ask. Only one initial break per session opening, 4 regional sessions can overlap.
- User diagram pip Gold **$0.10**, official Exness pip Gold **$0.01**. Never mix; a 100 diagram pip TP = Gold **$10**.
- Archived Exness XAUUSD Raw Spread `Timestamp,Bid,Ask` quotes; 2020 from Jan 29, 2026 through Oct 29; **295,225,516** quotes. Raw monthly ZIPs downloaded by GitHub Actions, SHA256 and monthly source info in per-year provenance.
- Fixed lot 0.01 = 1 oz, independent annual starting balances **$1,000 each**, example leverage 1:2000; **profits never withdrawn**. No martingale, no averaging, no early winning-ticket closure. TP fills at exact limit; SL at first observed executable quote (including gap losses). Historical executable Bid/Ask spread and **$0.07 commission** per 0.01-lot round-trip modelled; **no extra artificial slippage in this run**.
- This is a hypothetical quote replay, not proven actual live fills. No swap, network latency, true stop-out rule or dynamic broker margin regimes.

## Seven-year main comparison (2020–2026)

All variants start with 6,530 opened signals. Some SELL trades with wide TP/SL remain open at the end of a simulation year, and are **not** counted in TP/SL win percentages; their marked open P/L is included in the economic total P/L.

| Variant | High SELL TP/SL (diagram pips) | Low BUY TP/SL | Closed trades | TP | SL | Win % | Loss % | Combined yearly model economic P/L | Year-end open trades |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10/10 | 10/10 | 6530 | 2807 | 3723 | 42.99% | 57.01% | $-1580.110 | 0 |
| 2 | 20/20 | 10/10 | 6529 | 2896 | 3633 | 44.36% | 55.64% | $-1679.678 | 1 |
| 3 | 30/30 | 10/10 | 6529 | 2938 | 3591 | 45.00% | 55.00% | $-1728.529 | 1 |
| 4 | 40/40 | 10/10 | 6529 | 2930 | 3599 | 44.88% | 55.12% | $-2005.071 | 1 |
| 5 | 50/50 | 10/10 | 6529 | 2962 | 3567 | 45.37% | 54.63% | $-1916.356 | 1 |
| 6 | 60/60 | 10/10 | 6527 | 2966 | 3561 | 45.44% | 54.56% | $-2012.938 | 3 |
| 7 | 70/70 | 10/10 | 6526 | 2977 | 3549 | 45.62% | 54.38% | $-2014.196 | 4 |
| 8 | 80/80 | 10/10 | 6525 | 2962 | 3563 | 45.39% | 54.61% | $-2385.119 | 5 |
| 9 | 90/90 | 10/10 | 6523 | 2961 | 3562 | 45.39% | 54.61% | $-2537.157 | 7 |
| 10 | 100/100 | 10/10 | 6521 | 2972 | 3549 | 45.58% | 54.42% | $-2455.472 | 9 |

**Best by smallest summed simulated loss:** variant #1 (SELL10/SL10 and BUY10/SL10), $-1580.110.
**Best by TP hit rate:** variant #7 (SELL70/SL70, BUY10/SL10), 45.62% but $-2014.196.
**All ten models ended with negative combined seven-annual P/L; a higher win rate is not reliable profit.**

The sum of 7 annual economic P/Ls is **NOT** the performance of one continuous $1,000 account across 7 years. Each year is reset, all profits/losses kept *within that year's independent simulation*. For open positions, marked equity includes floating P/L, not imaginary closes.

## Separate high-break SELL vs low-break BUY

BUY side is invariant in all ten (all BUY orders closed under this run):
- 3152 BUY trades; 1354 TP vs 1798 SL; win **42.96%**, realized BUY P/L **$-779.270** summed across annual accounts.

| High SELL TP/SL | Closed SELL | SELL TP | SELL SL | SELL win % | SELL realized P/L | Combined annual economic P/L |
|---:|---:|---:|---:|---:|---:|---:|
| 10/10 | 3378 | 1453 | 1925 | 43.01% | $-800.840 | $-1580.110 |
| 20/20 | 3377 | 1542 | 1835 | 45.66% | $-900.088 | $-1679.678 |
| 30/30 | 3377 | 1584 | 1793 | 46.91% | $-948.939 | $-1728.529 |
| 40/40 | 3377 | 1576 | 1801 | 46.67% | $-1225.481 | $-2005.071 |
| 50/50 | 3377 | 1608 | 1769 | 47.62% | $-1136.766 | $-1916.356 |
| 60/60 | 3375 | 1612 | 1763 | 47.76% | $-1236.761 | $-2012.938 |
| 70/70 | 3374 | 1623 | 1751 | 48.10% | $-1242.164 | $-2014.196 |
| 80/80 | 3373 | 1608 | 1765 | 47.67% | $-1611.325 | $-2385.119 |
| 90/90 | 3371 | 1607 | 1764 | 47.67% | $-1767.294 | $-2537.157 |
| 100/100 | 3369 | 1618 | 1751 | 48.03% | $-1683.087 | $-2455.472 |

SELL profit/loss as listed above is **realized** and excludes floating P/L on unresolved SELL tickets. Combined economic P/L includes remaining open tickets marked at period end.

## Year-by-year economic P/L (each cell is an independent $1,000 annual simulation)

| High SELL TP/SL | 2020* | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/10 | $-463.25 | $-172.13 | $-196.16 | $-195.57 | $-140.63 | $-205.39 | $-206.99 |
| 20/20 | $-420.58 | $-197.83 | $-216.21 | $-210.56 | $-192.95 | $-235.61 | $-205.93 |
| 30/30 | $-549.33 | $-199.94 | $-208.06 | $-184.37 | $-192.69 | $-217.57 | $-176.56 |
| 40/40 | $-717.79 | $-225.03 | $-175.43 | $-127.18 | $-268.07 | $-271.79 | $-219.79 |
| 50/50 | $-709.85 | $-196.58 | $-66.16 | $-214.15 | $-334.86 | $-280.97 | $-113.79 |
| 60/60 | $-686.85 | $-232.62 | $-25.67 | $-236.55 | $-425.31 | $-294.45 | $-111.48 |
| 70/70 | $-605.80 | $-186.49 | $-60.40 | $-286.45 | $-549.69 | $-304.77 | $-20.60 |
| 80/80 | $-768.60 | $-176.17 | $-235.60 | $-247.48 | $-630.03 | $-391.59 | $64.34 |
| 90/90 | $-958.24 | $-288.79 | $-123.91 | $-157.33 | $-585.99 | $-423.39 | $0.49 |
| 100/100 | $-912.64 | $-404.16 | $-15.98 | $-89.13 | $-619.96 | $-452.70 | $39.10 |

*2020 starts Jan 29, 2026 ends Oct 29. Annual model P/L includes floating P/L on open trades.*

## Year-by-year closed-trade WIN RATE

| High SELL TP/SL | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/10 | 32.67% | 45.54% | 44.05% | 44.03% | 46.96% | 43.69% | 43.35% |
| 20/20 | 37.76% | 45.48% | 45.29% | 45.79% | 46.75% | 44.32% | 44.72% |
| 30/30 | 36.54% | 45.90% | 46.23% | 47.14% | 47.57% | 45.36% | 45.84% |
| 40/40 | 35.44% | 45.79% | 46.95% | 48.18% | 47.06% | 44.94% | 45.22% |
| 50/50 | 36.66% | 46.31% | 48.19% | 47.35% | 46.85% | 45.15% | 46.71% |
| 60/60 | 37.58% | 46.11% | 48.50% | 47.30% | 46.44% | 45.26% | 46.58% |
| 70/70 | 38.85% | 46.52% | 48.09% | 47.09% | 45.92% | 45.36% | 47.33% |
| 80/80 | 38.07% | 46.63% | 46.89% | 47.51% | 45.82% | 44.94% | 47.83% |
| 90/90 | 37.22% | 46.00% | 47.62% | 48.07% | 46.44% | 44.94% | 47.20% |
| 100/100 | 37.89% | 45.48% | 48.19% | 48.44% | 46.54% | 44.94% | 47.33% |

## Risk context

| High SELL TP/SL | Max annual wealth drawdown USD (worst annual episode) | Minimum simulated annual quote-marked equity USD |
|---:|---:|---:|
| 10/10 | $464.663 | $536.753 |
| 20/20 | $438.134 | $564.282 |
| 30/30 | $567.250 | $436.466 |
| 40/40 | $733.670 | $272.066 |
| 50/50 | $726.250 | $281.459 |
| 60/60 | $719.736 | $285.792 |
| 70/70 | $654.491 | $366.625 |
| 80/80 | $806.182 | $201.825 |
| 90/90 | $986.315 | $19.213 |
| 100/100 | $989.037 | $18.505 |

At SELL90/SL90 and SELL100/SL100, minimum observed simulated equity across annual restarts fell to approximately $19.21 and $18.50 respectively, **without** a broker-accurate dynamic margin/stop-out model. Such drawdowns may be nonviable under real conditions. This is not a safe profit recovery.

For SELL distance $D (gold price), nominal 0.01-lot TP yields +($D−$0.07) and an exactly filled SL costs −($D+$0.07), before gap losses; nominal SELL breakeven hit rate is ($D+$0.07)/(2$D). BUY fixed $1 threshold requires **53.5%** theoretical TP hits to cover commission, before adverse gap or latency costs. Actual BUY TP hit rate was just **42.96%**. Thus an unchanged buy-leg loss contribution occurs in every model.

The strategy variants were intentionally compared on already-studied 2020–2026 history, **not an untouched out-of-sample period**. None show a positive historical annual-aggregated edge in this comparison. No $0.05 extra adverse-slippage stress variants were run for this set of 10; spread and $0.07 fee are already included.

## Reproducibility
- GitHub Actions run: https://github.com/davidamerson/suresh/actions/runs/41966274025
- Branch `h1-reverse-sell10to100-buy10-20261105`
- Source script: https://github.com/davidamerson/suresh/blob/h1-reverse-sell10to100-buy10-20261105/ph1_backtest/h1_reverse_asymmetric_sell_10_100_buy_10.py
- Workflow: https://github.com/davidamerson/suresh/blob/h1-reverse-sell10to100-buy10-20261105/.github/workflows/h1-asym-reverse-sell10to100-buy10-sevenyear.yml
- Each of 7 uploaded per-year artifacts includes `summary.csv`, `by_side_summary.csv`, `individual_trades.csv`, `sessions.csv`, `daily_realized_PnL.csv`, `provenance.json` and `execution.log`. Artifacts have limited GitHub retention (30 days).
- All 7 annual jobs had status `success` and no modeled margin-rejected trades; that does **not** prove accurate live margin/stop-out behavior. The full comparison CSV captures 10 models' aggregated data.
