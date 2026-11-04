# XAUUSD Raw Spread — H1 first break TP10/SL10, 2020–2026

**Completed 2026-11-05 (Sri Lanka date).** GitHub Actions successful run: https://github.com/davidamerson/suresh/actions/runs/41889031888

## Exact test
- Same source entry/exit engine as TP5/SL5 previous study, new clean branch `h1-tp10-sl10-all-years`.
- Sydney 08:00, Tokyo 09:00, London 08:00 and New York 08:00 local first **completed** H1. Observe its Bid high and low. First subsequent raw Bid tick **strictly** above high: buy at available Ask; first strictly below low: sell at Bid. At most one order per reference session; signals expire on next same-session opening. The four sessions can hold positions simultaneously.
- **TP10 and SL10 trader-diagram pips: GOLD $1.00/$1.00**, measured from actual filled entry. They are not Exness official pips ($0.01 each).
- 0.01 lot = 1 oz, starting $1,000 separately per calendar year, 1:2000 example leverage, all profits retained, zero withdrawals, no early profit holding, no Friday force-flat.
- Historical actual Bid/Ask quotes, commission $0.07/round-trip for 0.01 lot. TP capped at exact limit target; SL at actual available quote with gap loss. Stress: +$0.05 adverse execution offset each side, independent run.
- Raw coverage 2020 Jan29–2026 Oct29 only, **295,225,516** ticks; not actual personal-account fills, swap and dynamic HMR not modeled.

## Year-by-year verified results

| Year | Closed trades | TP | SL | TP hit (win %) | SL hit (loss %) | No extra slippage modeled net P/L | TP hit with +$0.05/side slip | Stress net P/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020* | 903 | 380 | 523 | 42.08% | 57.92% | $-267.512 | 36.66% | $-372.734 |
| 2021 | 964 | 433 | 531 | 44.92% | 55.08% | $-176.174 | 39.42% | $-283.912 |
| 2022 | 967 | 468 | 499 | 48.40% | 51.60% | $-106.316 | 43.33% | $-205.107 |
| 2023 | 963 | 461 | 502 | 47.87% | 52.13% | $-116.973 | 43.20% | $-208.361 |
| 2024 | 969 | 463 | 506 | 47.78% | 52.22% | $-121.176 | 42.52% | $-224.100 |
| 2025 | 959 | 506 | 453 | 52.76% | 47.24% | $-26.149 | 48.70% | $-104.740 |
| 2026* | 805 | 374 | 431 | 46.46% | 53.54% | $-137.572 | 42.11% | $-210.683 |
| **Total** | **6530** | **3085** | **3445** | **47.24%** | **52.76%** | **$-951.872** | **42.33%** | **$-1609.637** |

*2020 begins Jan29, 2026 ends Oct29. All seven yearly simulations started with independent $1,000 balances: summed net P/L is **not** the end balance of one continuous $1,000 2020–2026 account. The stress TP/SL count total is 2764/3766.*

## Interpretation

- **3,085/6,530 TP = 47.24%**, **3,445/6,530 SL = 52.76%** on raw Bid/Ask quote replay without additional slippage.
- +$0.93 nominal win vs −$1.07 nominal loss after round-trip commission when SL fills exactly; theoretical break-even TP hit rate **53.5%** before extra gap/latency/swap costs. Some actual stops exceeded their nominal level.
- Every single year net P/L was **negative**, including 2025 at 52.76% TP hit rate.
- With $0.05 per oz adverse execution per side: 2,764 TP, 3,766 SL, TP **42.33%**, total annual-model net **−$1,609.637**.
- None of the 7 years reported margin rejection, failure or remaining active open positions at end. All 6,530 signal orders closed.
- This shows no verified positive edge, not that future winning trades are impossible.

## Audit
- Source: https://github.com/davidamerson/suresh/blob/h1-tp10-sl10-all-years/ph1_backtest/h1_firstbreak_tp10_sl10_2020_2026.py
- GitHub Actions: https://github.com/davidamerson/suresh/actions/runs/41889031888
- Each year uploads `summary.csv`, `individual_trades.csv`, `sessions.csv`, `daily_realized_PnL.csv`, `provenance.json`, `execution.log`.
- Numerical values transcribed directly from successful per-year GitHub Actions raw execution logs; yearly counts sum to historical 6,530. Report uses exact USD without invented fills.

