# Corrected XAUUSD first-H1-session Major Support & Resistance Entry: 40 strategy replay 2020–2026

**Completed research on 5 November 2026.** All 14 GitHub Actions matrix jobs completed successfully. **Source**: Exness XAUUSD Raw Spread Bid/Ask historical tick archives, **295,225,516** observed quote rows, 2020 from January 29 and 2026 to October 29. Each 1-year backtest independently initializes a hypothetical $1,000 account; profit is never withdrawn; 0.01 lot fixed (1oz) without compounding order size.

## 1. Entry definition — auditable, causal and the ONLY intended strategy change

Instead of entering on first H1 candle's own High or Low, wait for the **completion of that first regional H1 hour** after Sydney 08:00, Tokyo 09:00, London 08:00, New York 08:00 *local* (timezones with historical DST) and freeze the *nearest qualifying major RESISTANCE above that moment's Bid and SUPPORT below that moment's Bid*, selected only from:
- Prior fully **completed** UTC Monday–Sunday weekly maximum Bid High and minimum Bid Low (NOT the still unfolding current week's high or low).
- The latest *causally confirmed UTC D1 swing pivot High or Low*: a central bar exceeding (for High) or below (for Low) its 2 preceding and 2 succeeding **completely closed** observed D1 quote bars. The pivot only becomes known after both right-hand D1 bars are completed, not at pivot occurrence.

Choose nearer eligible resistance above current Bid and nearer eligible support below. If one side has no eligible preexisting major level, that side gives no signal. Observe every historical Bid tick after H1 close; enter only on an actual next **tick crossing** from ≤ resistance to > resistance, or from ≥ support to < support. **Do not** retroactively enter when price is already beyond a level. One first-cross opportunity per local session opening; no trade after the later second break from the same opening. Levels frozen for that signal, not selected using future outcome.

A major level is **operationally defined** as these higher-timeframe price landmarks; it is NOT a guaranteed institutional liquidity level, multi-touch confirmed zone, or market depth orderbook. UTC D1 differs from many platforms' New York-closing daily candles. This is one testable definition of “Major S/R”, not all possible S/R theories.

The four original groups of 10 remain otherwise unchanged:
1. REVERSE_EQ: Resistance BUY? **NO** Resistance SELL / Support BUY, both TP=SL 10 through 100 diagram pips.
2. MOMENTUM_EQ: Resistance BUY / Support SELL, both TP=SL 10 through 100 diagram pips.
3. REVERSE_RR2: Resistance SELL / Support BUY, both TP/SL 10/5 through 100/50 diagram pips.
4. MOMENTUM_RR2: Resistance BUY / Support SELL, both TP/SL 10/5 through 100/50 diagram pips.

**User diagram pip Gold $0.10**; so TP90/SL90 means Gold $9/$9, TP100/SL50 means Gold $10/$5. Do not confuse with Exness official XAUUSD pip convention. Bid/Ask spread is real archived quote spread. One model round-trip commission $0.07 per 0.01-lot trade. TP at exact limit; stops on first available executable quote including adverse gaps. No extra slippage in these 40 standard models, no swap/dynamic high-margin regimes or guaranteed live fills modelled. None withdraw profits; annual results are **seven distinct reset-$1,000 simulations**, not a continuous 2020–26 $1,000 portfolio.

## 2. Group-by-group verified results

### Reverse 1:1 (Resistance SELL / Support BUY)
| TP/SL | Opened | Closed | TP | SL | Win % | Loss % | Annual model net P/L |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/10 | 1925 | 1925 | 821 | 1104 | 42.65% | 57.35% | $-510.734 |
| 20/20 | 1925 | 1925 | 860 | 1065 | 44.68% | 55.32% | $-636.565 |
| 30/30 | 1925 | 1925 | 864 | 1061 | 44.88% | 55.12% | $-812.474 |
| 40/40 | 1925 | 1925 | 806 | 1119 | 41.87% | 58.13% | $-1470.844 |
| 50/50 | 1925 | 1925 | 827 | 1098 | 42.96% | 57.04% | $-1568.683 |
| 60/60 | 1925 | 1925 | 784 | 1141 | 40.73% | 59.27% | $-2368.622 |
| 70/70 | 1925 | 1925 | 773 | 1152 | 40.16% | 59.84% | $-2861.770 |
| 80/80 | 1925 | 1922 | 783 | 1139 | 40.74% | 59.26% | $-3069.450 |
| 90/90 | 1925 | 1920 | 787 | 1133 | 40.99% | 59.01% | $-3329.955 |
| 100/100 | 1925 | 1916 | 820 | 1096 | 42.80% | 57.20% | $-2982.783 |

### Momentum/Breakout 1:1 (Resistance BUY / Support SELL)
| TP/SL | Opened | Closed | TP | SL | Win % | Loss % | Annual model net P/L |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/10 | 1925 | 1925 | 906 | 1019 | 47.06% | 52.94% | $-306.307 |
| 20/20 | 1925 | 1925 | 969 | 956 | 50.34% | 49.66% | $-163.492 |
| 30/30 | 1925 | 1925 | 1001 | 924 | 52.00% | 48.00% | $37.659 |
| 40/40 | 1925 | 1925 | 1069 | 856 | 55.53% | 44.47% | $655.398 |
| 50/50 | 1925 | 1925 | 1039 | 886 | 53.97% | 46.03% | $566.747 |
| 60/60 | 1925 | 1925 | 1104 | 821 | 57.35% | 42.65% | $1502.838 |
| 70/70 | 1925 | 1925 | 1109 | 816 | 57.61% | 42.39% | $1864.284 |
| 80/80 | 1925 | 1922 | 1108 | 814 | 57.65% | 42.35% | $2141.461 |
| 90/90 | 1925 | 1920 | 1099 | 821 | 57.24% | 42.76% | $2313.793 |
| 100/100 | 1925 | 1916 | 1075 | 841 | 56.11% | 43.89% | $2149.106 |

### Reverse 2:1 (Resistance SELL / Support BUY)
| TP/SL | Opened | Closed | TP | SL | Win % | Loss % | Annual model net P/L |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/5 | 1925 | 1925 | 460 | 1465 | 23.90% | 76.10% | $-542.220 |
| 20/10 | 1925 | 1925 | 554 | 1371 | 28.78% | 71.22% | $-508.471 |
| 30/15 | 1925 | 1925 | 534 | 1391 | 27.74% | 72.26% | $-722.676 |
| 40/20 | 1925 | 1925 | 529 | 1396 | 27.48% | 72.52% | $-927.771 |
| 50/25 | 1925 | 1925 | 556 | 1369 | 28.88% | 71.12% | $-892.051 |
| 60/30 | 1925 | 1925 | 538 | 1387 | 27.95% | 72.05% | $-1179.375 |
| 70/35 | 1925 | 1925 | 492 | 1433 | 25.56% | 74.44% | $-1817.472 |
| 80/40 | 1925 | 1922 | 485 | 1437 | 25.23% | 74.77% | $-2102.642 |
| 90/45 | 1925 | 1922 | 505 | 1417 | 26.27% | 73.73% | $-2072.332 |
| 100/50 | 1925 | 1918 | 523 | 1395 | 27.27% | 72.73% | $-1965.900 |

### Momentum/Breakout 2:1 (Resistance BUY / Support SELL)
| TP/SL | Opened | Closed | TP | SL | Win % | Loss % | Annual model net P/L |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10/5 | 1925 | 1925 | 597 | 1328 | 31.01% | 68.99% | $-301.649 |
| 20/10 | 1925 | 1925 | 640 | 1285 | 33.25% | 66.75% | $-223.579 |
| 30/15 | 1925 | 1925 | 697 | 1228 | 36.21% | 63.79% | $39.522 |
| 40/20 | 1925 | 1925 | 750 | 1175 | 38.96% | 61.04% | $452.095 |
| 50/25 | 1925 | 1925 | 738 | 1187 | 38.34% | 61.66% | $523.574 |
| 60/30 | 1925 | 1925 | 741 | 1184 | 38.49% | 61.51% | $688.059 |
| 70/35 | 1925 | 1925 | 753 | 1172 | 39.12% | 60.88% | $949.681 |
| 80/40 | 1925 | 1925 | 777 | 1148 | 40.36% | 59.64% | $1410.117 |
| 90/45 | 1925 | 1923 | 760 | 1163 | 39.52% | 60.48% | $1413.400 |
| 100/50 | 1925 | 1923 | 757 | 1166 | 39.37% | 60.63% | $1544.485 |

## 3. Best models by aggregate economic P/L

| Family | Best TP/SL user pips | Win % | Annual economic P/L sum | Positive annual years |
|---|---:|---:|---:|---:|
| REVERSE_EQ | 10/10 | 42.65% | $-510.734 | 0/7 |
| MOMENTUM_EQ | 90/90 | 57.24% | $2313.793 | 7/7 |
| REVERSE_RR2 | 20/10 | 28.78% | $-508.471 | 1/7 |
| MOMENTUM_RR2 | 100/50 | 39.37% | $1544.485 | 7/7 |

**Best overall within 40**: MOMENTUM_EQ TP90/SL90, **$2313.793** combined *separate annual* economic model P/L; 57.24% win percentage and 1099 TP wins / 821 SL losses, 1920 closed. Total 1925 opened signals, 5 unresolved at annual endpoints. Worst single-annual drawdown $206.683, lowest model equity $833.553. **This is an in-sample historical finding, not a demonstrated live edge.**

**Number of 40 configurations with positive combined annual economic P/L:** 16. 0 are REVERSE and 16 MOMENTUM. Trade count changed materially from 6,530 H1 boundary signals per variant to 1925 major-S/R cross signals (across annual resets), so comparisons reflect both signal quality and participation frequency.

## 4. Exact entry-only change versus previous H1-bar High/Low historical test

| Family | TP/SL | Old first H1 High/Low entry P/L | Major S/R entry P/L | Net difference |
|---|---:|---:|---:|---:|
| MOMENTUM_EQ | 90/90 | $-1302.652 | $2313.793 | $3616.445 |
| MOMENTUM_EQ | 70/70 | $-900.780 | $1864.284 | $2765.064 |
| MOMENTUM_RR2 | 100/50 | $-1325.024 | $1544.485 | $2869.509 |
| MOMENTUM_RR2 | 80/40 | $-404.810 | $1410.117 | $1814.927 |
| REVERSE_EQ | 10/10 | $-1580.110 | $-510.734 | $1069.376 |

Comparability: equal year coverage, underlying archive, 4 local regional opens and first-H1-wait session filter, 0.01-lot, $0.07 fee, stop and TP mechanics, and no withdrawal. The new S/R sample has substantially fewer trades. Do not compare totals alone without inspecting expectancy and risk; multi-variant selection of best parameters on already-reviewed years increases overfit risk.

## 5. Annual P/L of best overall Major S/R model

| Year | Closed | TP | SL | Win % | Annual economic P/L | Year-end open |
|---|---:|---:|---:|---:|---:|---:|
| 2020* | 215 | 114 | 101 | 53.02% | $78.523 | 3 |
| 2021 | 306 | 162 | 144 | 52.94% | $151.569 | 2 |
| 2022 | 305 | 183 | 122 | 60.00% | $517.703 | 0 |
| 2023 | 266 | 176 | 90 | 66.17% | $752.986 | 0 |
| 2024 | 286 | 155 | 131 | 54.20% | $191.681 | 0 |
| 2025 | 276 | 159 | 117 | 57.61% | $354.742 | 0 |
| 2026* | 266 | 150 | 116 | 56.39% | $266.589 | 0 |

*2020 partial Jan 29 onward; 2026 partial to October 29. Positive years here are on in-sample data and do not prove sustained live profitability. The annual starting equity always resets to $1,000, so annual gains are not dollar-compounded across years.*

## 6. Major levels and source provenance

The engine retains and freezes weekly previous completed highs/lows and 2L/2R D1 pivot highs/lows directly as the tick stream unfolds, rather than calculating pivots from the full future chart. Per-year CSV `summary.csv` contains the count of frozen resistance/support levels sourced from D1 pivots vs previous completed weekly highs/lows, plus number of sessions with no usable levels. `individual_trades.csv` contains each ticket's frozen levels, quote entry, exit, TP/SL reason, spread and P/L. `provenance.json` contains archive URL/monthly ZIP SHA256; `execution.log` documents test and replay. All 14 jobs succeeded with **zero modeled rejected-margin orders and zero engine equity failures**; broker-accurate stopouts, swap and dynamic broker high margin rules are not fully simulated.

## 7. Limitations and validation

- Higher-timeframe "major" levels require a definition; this test uses **nearest** qualified prior-week extreme or confirmed D1 fractal pivot, not hand-drawn zones.
- Previous completed week and D1 observed bars are UTC-aligned, which may differ from other gold daily/weekly candle conventions. Historical feed source has market closures/gaps.
- A more reliable system needs **genuinely future out-of-sample data**, independent rolling-forward calibration without repeated reuse of 2020–26, realistic adverse slippage, spread distributions and broker-specific leverage/HMR, and preferably robustness across different S/R definitions. No guaranteed daily profits.
- Extra execution slippage for the two selected strongest configurations is being studied separately. Do not interpret this base-cost positive P/L as final live evidence.

## Audit

- Equal 1:1 GitHub Actions: https://github.com/davidamerson/suresh/actions/runs/41972310501
- Reward-to-risk 2:1 GitHub Actions: https://github.com/davidamerson/suresh/actions/runs/41972316163
- Repo branch: `h1-major-sr-40models-20261105`
- Equal code: https://github.com/davidamerson/suresh/blob/h1-major-sr-40models-20261105/ph1_backtest/h1_major_sr_reverse_vs_breakout_equal_2020_2026.py
- 2:1 code: https://github.com/davidamerson/suresh/blob/h1-major-sr-40models-20261105/ph1_backtest/h1_major_sr_reverse_vs_breakout_rr2_2020_2026.py
- All 280 annual model rows and 560 annual breakout-side rows verified from successful original GitHub logs and against archived original H1 40-model CSV.

