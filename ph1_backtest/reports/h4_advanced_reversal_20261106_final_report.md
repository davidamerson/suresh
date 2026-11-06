# XAUUSD H4 Advanced Confirmed Reversal — Final 90-Configuration Research Audit
Date: 2026-11-06. **Historical simulation only; not an established profitable live trading system.**

## Evidence and architecture
- Source: 296,709,207 historical Exness XAUUSD_Raw_Spread Timestamp/Bid/Ask quotes, 2020-01-29 through 2026-11-05 09:12 UTC.
- One continuous $1,000 hypothetical account per configuration; fixed 0.01 lot = 1 oz; modeled leverage 1:2000. BUY filled at Ask, SELL at Bid, exit at appropriate side of quote.
- $0.07 modeled roundtrip commission per 0.01 lot plus actual archived spread; gap stop simulation. **Specific broker swap fees, historical changing margin/HMR, execution latency, actual live fills are not fully reconstructed.**
- Previous H4 experiment's Friday/weekend holding allowed; **TP/SL only**, no Friday forced liquidation or daily profit goal. One new entry on confirmed completed UTC H4 candle at first quote of subsequent H4.
- 10 predefined 3:1 ratio configs: TP30/SL10, TP60/SL20, ... TP300/SL100. Diagram pip = GOLD USD 0.10, e.g. TP300 = gold $30, SL100 = gold $10. *Exness official pip vocabulary can differ.*
- Single global signals shared by all 10 TP/SL configurations, direct quote replay, full open+closed ledger reconciliation, no model stopout. Provisional baseline MACD12_26_9 prior run 42188261322; original nine-method run 42245014059 (8 succeeded, one final reconciliation audit failed), EMA-only corrected *audit* run 42249388742 succeeded (strategy entry code unchanged).
- IMPORTANT: This is NOT a pristine independent holdout; the historical 2020–2026 data and prior MACD baseline were already studied before choosing these new variants. 90 configurations create multiple-testing risk. Do NOT select a winner solely by historical maximum P/L.

## Comparable TP300 / SL100 (gold $30/$10) results
| Method | Trades opened | TP | SL | Net P/L USD | Max DD USD | Positions open at cutoff |
|---|---:|---:|---:|---:|---:|---:|
| MACD12_26_9_PREVIOUS | 307 | 99 | 208 | +851.134 | 204.067 | 0 |
| MACD_BODY_EMA | 228 | 78 | 150 | +814.325 | 183.909 | 0 |
| MACD_KAMA_EFF | 206 | 69 | 137 | +673.639 | 194.618 | 0 |
| MACD_TWO_BAR_HOLD | 137 | 46 | 91 | +441.353 | 102.392 | 0 |
| PA_MSS_MACD | 108 | 28 | 80 | +28.242 | 256.654 | 0 |
| PA_MSS_ACCEPT_MACD | 152 | 35 | 117 | -139.200 | 320.473 | 0 |
| ATR_SUPERTREND_FLIP | 350 | 90 | 260 | +39.346 | 451.141 | 0 |
| CUSUM_EMA_REVERSAL | 97 | 21 | 76 | -140.972 | 239.189 | 0 |
| OLS_SLOPE_REVERSAL | 375 | 96 | 279 | +37.432 | 629.098 | 0 |
| EMA_CROSS_ATR_CONFIRM | 131 | 27 | 103 | -224.986 | 321.274 | 1 |

## Best net configuration inside each method's ten candidates (in-sample search, not a validation)
| Method | TP/SL diagram pips | Model net USD | Model Max DD USD |
|---|---:|---:|---:|
| MACD_BODY_EMA | 300/100 | +814.325 | 183.909 |
| MACD_KAMA_EFF | 300/100 | +673.639 | 194.618 |
| MACD_TWO_BAR_HOLD | 270/90 | +501.771 | 93.386 |
| PA_MSS_MACD | 150/50 | +108.504 | 120.259 |
| PA_MSS_ACCEPT_MACD | 150/50 | +82.288 | 87.764 |
| ATR_SUPERTREND_FLIP | 300/100 | +39.346 | 451.141 |
| CUSUM_EMA_REVERSAL | 30/10 | -59.906 | 64.760 |
| OLS_SLOPE_REVERSAL | 300/100 | +37.432 | 629.098 |
| EMA_CROSS_ATR_CONFIRM | 30/10 | -21.502 | 34.689 |

## Full year-end marked equity (TP300 / SL100)
### MACD_BODY_EMA at TP300 / SL100
- 2020: continuous net P/L +156.504, marked equity $1156.504
- 2021: continuous net P/L +166.968, marked equity $1166.968
- 2022: continuous net P/L +209.777, marked equity $1209.777
- 2023: continuous net P/L +356.764, marked equity $1356.764
- 2024: continuous net P/L +580.842, marked equity $1580.842
- 2025: continuous net P/L +697.714, marked equity $1697.714
- 2026: continuous net P/L +814.325, marked equity $1814.325

### MACD_KAMA_EFF at TP300 / SL100
- 2020: continuous net P/L +134.871, marked equity $1134.871
- 2021: continuous net P/L +44.100, marked equity $1044.100
- 2022: continuous net P/L +129.905, marked equity $1129.905
- 2023: continuous net P/L +176.705, marked equity $1176.705
- 2024: continuous net P/L +431.288, marked equity $1431.288
- 2025: continuous net P/L +566.800, marked equity $1566.800
- 2026: continuous net P/L +673.639, marked equity $1673.639

### MACD_TWO_BAR_HOLD at TP300 / SL100
- 2020: continuous net P/L +23.467, marked equity $1023.467
- 2021: continuous net P/L +54.694, marked equity $1054.694
- 2022: continuous net P/L +115.359, marked equity $1115.359
- 2023: continuous net P/L +163.108, marked equity $1163.108
- 2024: continuous net P/L +271.176, marked equity $1271.176
- 2025: continuous net P/L +433.529, marked equity $1433.529
- 2026: continuous net P/L +441.353, marked equity $1441.353

### PA_MSS_MACD at TP300 / SL100
- 2020: continuous net P/L +28.265, marked equity $1028.265
- 2021: continuous net P/L +86.747, marked equity $1086.747
- 2022: continuous net P/L +45.087, marked equity $1045.087
- 2023: continuous net P/L -46.812, marked equity $953.188
- 2024: continuous net P/L -68.617, marked equity $931.383
- 2025: continuous net P/L +39.860, marked equity $1039.860
- 2026: continuous net P/L +28.242, marked equity $1028.242

### PA_MSS_ACCEPT_MACD at TP300 / SL100
- 2020: continuous net P/L +37.826, marked equity $1037.826
- 2021: continuous net P/L +28.500, marked equity $1028.500
- 2022: continuous net P/L -126.722, marked equity $873.278
- 2023: continuous net P/L -189.224, marked equity $810.776
- 2024: continuous net P/L -71.267, marked equity $928.733
- 2025: continuous net P/L -86.715, marked equity $913.285
- 2026: continuous net P/L -139.200, marked equity $860.800

### ATR_SUPERTREND_FLIP at TP300 / SL100
- 2020: continuous net P/L +75.818, marked equity $1075.818
- 2021: continuous net P/L -6.561, marked equity $993.439
- 2022: continuous net P/L -144.460, marked equity $855.540
- 2023: continuous net P/L -158.154, marked equity $841.846
- 2024: continuous net P/L -215.549, marked equity $784.451
- 2025: continuous net P/L +177.063, marked equity $1177.063
- 2026: continuous net P/L +39.346, marked equity $1039.346

### CUSUM_EMA_REVERSAL at TP300 / SL100
- 2020: continuous net P/L -10.898, marked equity $989.102
- 2021: continuous net P/L +68.097, marked equity $1068.097
- 2022: continuous net P/L -24.812, marked equity $975.188
- 2023: continuous net P/L +43.686, marked equity $1043.686
- 2024: continuous net P/L -47.596, marked equity $952.404
- 2025: continuous net P/L -68.800, marked equity $931.200
- 2026: continuous net P/L -140.972, marked equity $859.028

### OLS_SLOPE_REVERSAL at TP300 / SL100
- 2020: continuous net P/L +197.317, marked equity $1197.317
- 2021: continuous net P/L +92.150, marked equity $1092.150
- 2022: continuous net P/L -136.148, marked equity $863.852
- 2023: continuous net P/L -162.300, marked equity $837.700
- 2024: continuous net P/L -139.439, marked equity $860.561
- 2025: continuous net P/L +135.730, marked equity $1135.730
- 2026: continuous net P/L +37.432, marked equity $1037.432

### EMA_CROSS_ATR_CONFIRM at TP300 / SL100
- 2020: continuous net P/L -172.879, marked equity $827.121
- 2021: continuous net P/L -164.590, marked equity $835.410
- 2022: continuous net P/L -226.355, marked equity $773.645
- 2023: continuous net P/L -247.651, marked equity $752.349
- 2024: continuous net P/L -200.245, marked equity $799.755
- 2025: continuous net P/L -252.091, marked equity $747.909
- 2026: continuous net P/L -224.986, marked equity $775.014

## Interpretation
- **No new method surpassed the previous MACD histogram model's +$851.134 model net** at the directly comparable TP300 / SL100. The first-bar MACD body+EMA filter produced +$814.325 with lower modeled maximum drawdown ($183.909 vs baseline $204.067) and fewer trades (228 vs 307).
- MACD_TWO_BAR_HOLD at TP270/SL90 produced +$501.771 and $93.386 drawdown, illustrating risk/return/confirmation-lag tradeoffs, not a guaranteed improved system.
- Price-action swing confirmation and CUSUM/OLS mathematical methods failed to produce a convincing advantage within these fixed targets; filtering and additional H4-bar confirmations can lag the true price transition.
- EMA_CROSS_ATR_CONFIRM at TP300/SL100 opened 131, closed 130 and left one marked open ticket at cutoff. The corrected audit compares both closed and open entries across configurations and accounts for the remaining floating P/L; **net = -$224.986**.
- No strategy should be deployed with real funds based only on these backtests. Next validation should freeze rules before *new future* gold ticks, test realistic swap/latency/HMR, quote anomalies, and report P/L distribution and confidence intervals. These methods do not meet a guaranteed daily-income objective.

## Sources and reproduce
- [Nine-method research branch](https://github.com/davidamerson/suresh/tree/h4-advanced-confirmed-reversal-nine-models-20261106)
- [Primary eight successful jobs (plus EMA audit failure)](https://github.com/davidamerson/suresh/actions/runs/42245014059)
- [Corrected EMA verification run](https://github.com/davidamerson/suresh/actions/runs/42249388742)
- [Previous MACD histogram baseline](https://github.com/davidamerson/suresh/actions/runs/42188261322)
- `ph1_backtest/h4_advanced_reversal_detectors.py`: exact signal thresholds.
- `ph1_backtest/h4_advanced_reversal_nine_runner.py`: original strategy replay wrapper.
- `ph1_backtest/h4_advanced_ema_repaired_runner.py`: corrected open+closed entry audit, same trading signals.
- `.github/workflows/h4-advanced-confirmed-reversal-nine-rr3.yml` and `.github/workflows/h4-advanced-ema-audit-repair.yml`: remote reproducible runs.
- Per-run individual trade ledgers and source checksums in GitHub Actions ZIP artifacts (retention 30 days). The permanent 90-row summary CSV accompanies this report.

