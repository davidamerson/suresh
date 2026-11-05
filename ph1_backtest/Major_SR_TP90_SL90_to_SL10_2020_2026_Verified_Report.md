# Verified XAUUSD Major S/R TP90 / SL90–SL10 Sweep — 2020–2026

**Completed 5 November 2026**. One fully successful continuous-account run with Numba/pandas on **296,709,207** Exness Raw Spread real historical Bid/Ask tick records from 84 provenance-hashed archives. Single original $1,000 account 2020-01-29 through **2026-11-05 09:12:23.770 UTC**, fixed 0.01 lot (1 oz XAUUSD), zero profits withdrawn, no additional capital, modeled $0.07 round-trip per 0.01 lot. No annual resets.

[**Successful GitHub Actions execution**](https://github.com/davidamerson/suresh/actions/runs/42071221763)  
[**Complete exact source code**](https://github.com/davidamerson/suresh/blob/major-sr-tp90-sl90-to-sl10-sweep-20261105/ph1_backtest/major_sr_tp90_sl90_to_sl10_weekend_hold_2020_2026.py)

## 9 predeclared strategy variants (no outcome-based exclusion)

TP **90 user diagram pips = Gold $9.00** is identical in all 9 variants. SL90 is Gold $9.00, SL80 $8.00, SL70 $7.00, … SL10 $1.00. This is the user's established **diagram pip definition**, not a universal MT4 symbol pip specification.

The *previously selected* strongest system has been LOCKED otherwise: Major Resistance broken → BUY, Major Support broken → SELL. Sources frozen after first completed regional-opening H1 across Sydney, Tokyo, London, New York with DST-aware local sessions: last complete UTC weekly high/low and latest confirmed 2-left/2-right UTC Daily pivots (up to four qualifying source levels). Both buy/sell sides symmetric. Multiple independent entries per day are permitted, no per-day trade cap. Same Gold $1 price-zone grouping prevents simultaneous duplicate trade on same S/R. For repeated trade on the same level, prior same-zone position must be CLOSED, then a **fully completed UTC H1 candle closes Gold $9 back on the prebreakout side**, and finally an actual tick crosses the level again. No future-quote trade selection.

Weekend/holiday carry is ALLOWED and **ALL Friday time-forced closes, holiday/Thursday time closes, six-hour stops and Friday entry bans are OFF**. Trades can close **ONLY TP or SL** at the first actually observed historical executable Bid/Ask quote after trigger; SL can gap through nominal distance. No trailing stop, break-even adjustment or time exits in any of nine variants. Only broker 0%-equity emergency stopout contingency would override; NONE occurred. Swap-free status **assumed only conditionally**, no synthetic swap debit in nine main profiles. Historical account-specific swap rates, variable HMR, execution queue/network delays and live broker eligibility not supplied.

## Full verified comparison

| Model | Trades | TP wins | SL losses | TP win rate | SL loss rate | Continuous account final equity | Net profit USD | Max equity DD USD | Worst single trade USD | Average losing trade USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **TP90/SL90** | 793 | 454 | 339 | 57.25% | 42.75% | $1958.890 | **+$958.890** | $98.253 | −$11.589 | −$9.131 |
| **TP90/SL80** | 793 | 431 | 362 | 54.35% | 45.65% | $1903.554 | **+$903.554** | $117.886 | −$11.589 | −$8.136 |
| **TP90/SL70** | 793 | 395 | 398 | 49.81% | 50.19% | $1683.076 | **+$683.076** | $134.759 | −$11.589 | −$7.146 |
| **TP90/SL60** | 793 | 369 | 424 | 46.53% | 53.47% | $1696.055 | **+$696.055** | $115.430 | −$7.589 | −$6.130 |
| **TP90/SL50** | 793 | 323 | 470 | 40.73% | 59.27% | $1473.566 | **+$473.566** | $90.074 | −$7.589 | −$5.129 |
| **TP90/SL40** | 793 | 286 | 507 | 36.07% | 63.93% | $1458.667 | **+$458.667** | $98.086 | −$7.589 | −$4.133 |
| **TP90/SL30** | 793 | 237 | 556 | 29.89% | 70.11% | $1376.414 | **+$376.414** | $94.297 | −$6.021 | −$3.129 |
| **TP90/SL20** | 793 | 188 | 605 | 23.71% | 76.29% | $1392.707 | **+$392.707** | $41.985 | −$6.021 | −$2.126 |
| **TP90/SL10** | 793 | 111 | 682 | 14.00% | 86.00% | $1220.063 | **+$220.063** | $80.447 | −$6.021 | −$1.131 |

**Exact audit findings:**
- The full trade ledgers were loaded from the GitHub artifact, individually summed, and **P/L sums matched all 9 model summaries**.
- **All 793 executed entry events were identical in timestamp, price, direction, session and causal S/R source in ALL 9 variants** (set equality verified). Therefore the result difference is strictly from the differing stops and resulting historical quote exits, not changing entry opportunities or varying model filter criteria. Each model had **361 S/R zones with 432 revalidated repeat entries**.
- Each model: **793 opened, 793 closed; 0 Friday/time exits; 0 break-even/trailing exits; 0 broker stopouts; 0 margin call/rejections; 0 open tickets at final cutoff**. Four original regional market sessions and all source S/R events handled uniformly.
- The **SL90 benchmark reproduced exactly** the previous independent TP/SL-only weekend-hold 2020–2026 analysis: **454 TP, 339 SL, +$958.890, maximum DD $98.253**.
- **All nine were net profitable in the tested historical quote sample.** Smaller SL did not improve total profit: TP90/SL90 is the maximum by net profit and TP fraction.
- **TP90/SL20** is minimum historical max DD **$41.985**, but net P/L only **+$392.707**, versus SL90 P/L +$958.890 and DD $98.253; this is a risk–return trade-off, not free improvement.
- **SL80** loses $55.336 net profit AND increases max DD $19.633 relative to SL90, so it is historically dominated in both P/L and DD on this dataset.
- SL10 worst realized loss **−$6.021** despite its nominal $1 hard stop due to gap/first observed quote; even very tight stops do NOT cap downside exactly at stop distance.
- SL90 has 454 winning TP vs 339 losing SL; SL10 111 TP vs 682 SL. Thus attempting to make each SL cheaper **more than doubles number of losing trades** in this sample.
- Beware **multiple comparisons / in-sample fit**: TP90 and $9 H1 rearm were chosen on this 2020–26 dataset during prior exploration. This 9-stop sweep shares that same sample; choosing the 'best' of these 9 by historical P/L does NOT provide untouched future confirmation. Future data/live Exness Demo is needed.

## Year-end account equity for all 9 independent portfolios (ONE unreset account per strategy)

| Year | SL90 | SL80 | SL70 | SL60 | SL50 | SL40 | SL30 | SL20 | SL10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Start | $1000 | $1000 | $1000 | $1000 | $1000 | $1000 | $1000 | $1000 | $1000 |
| 2020* | $1012.39 | $1037.19 | $1049.26 | $1052.87 | $1006.25 | $1011.56 | $1002.30 | $1004.59 | $1005.32 |
| 2021 | $1152.42 | $1203.31 | $1181.37 | $1202.61 | $1081.38 | $1108.96 | $1089.83 | $1083.47 | $1029.76 |
| 2022 | $1334.41 | $1359.66 | $1336.39 | $1303.45 | $1126.29 | $1192.16 | $1156.64 | $1135.83 | $1071.71 |
| 2023 | $1562.36 | $1545.73 | $1519.56 | $1457.84 | $1273.52 | $1325.11 | $1238.97 | $1224.15 | $1156.42 |
| 2024 | $1661.60 | $1622.49 | $1550.09 | $1529.45 | $1346.21 | $1355.04 | $1277.13 | $1270.81 | $1202.60 |
| 2025 | $1838.57 | $1810.19 | $1689.90 | $1651.71 | $1447.77 | $1464.44 | $1367.96 | $1339.77 | $1252.23 |
| 2026* | $1958.89 | $1903.55 | $1683.08 | $1696.06 | $1473.57 | $1458.67 | $1376.41 | $1392.71 | $1220.06 |

*2020 starts Jan29; 2026 ends Nov05; some year-end rows can include OPEN unrealized positions marked to latest quote, and a year may have negative P/L even though overall sample is positive. No forced year-end liquidation. At 2026 cutoff all nine portfolios had zero open tickets, so marked equity equals cash.*

## Reproducibility & provenance

GitHub Actions run: https://github.com/davidamerson/suresh/actions/runs/42071221763

- Results artifact **`MajorSR-TP90-SL90-to-SL10-NoFriday-2020-2026`** contains `ticket_ledger.csv` (7,137 individual closed tickets across nine models), `model_summary.csv`, `continuous_annual_equity.csv`, `open_positions_at_cutoff.csv` (empty), `provenance.json` (84 source URLs/ZIP SHA256/input row counts), `execution.log`.
- Full run source from branch `major-sr-tp90-sl90-to-sl10-sweep-20261105`: https://github.com/davidamerson/suresh/blob/major-sr-tp90-sl90-to-sl10-sweep-20261105/ph1_backtest/major_sr_tp90_sl90_to_sl10_weekend_hold_2020_2026.py
- Original reference no-Friday TP/SL-only test: https://github.com/davidamerson/suresh/actions/runs/42050760343
- All analyzed historical quoted Bid/Ask data, not verified broker actual trade transactions. Past performance is not a guarantee. Swap-free account status must be checked; live execution, gaps, and swaps can alter outcomes.
