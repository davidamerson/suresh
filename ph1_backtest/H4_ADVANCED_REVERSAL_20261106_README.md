# H4 confirmed reversal research — 2026-11-06

Instrument: Exness XAUUSD_Raw_Spread. Research only, NOT a live-money strategy.

## Experimental registration and execution
- Original code/algorithm branches are not overwritten.
- Dataset: 2020-01-29 onward through 2026-11-05 09:12:23.770 UTC, 296,709,207 recorded quotes if full archive succeeds.
- All signals are evaluated on fully completed UTC H4 Bid candles; earliest entry is executable first available next-H4 Bid/Ask tick, not a future open.
- Starting cash: $1,000 continuous account per configuration, 0.01 lot (1 troy oz), modeled leverage 1:2000, original spread plus $0.07/0.01-lot roundtrip fee.
- Hold weekends; do not impose a different experiment's Friday force-close. Exit only at fixed TP/SL; SL gap fills can be adverse; open positions must be included in end marked equity.
- The ten predeclared RR3 configurations (user's diagram pip=$0.10 gold): TP30/SL10 through TP300/SL100 in increments of 30/10, or gold $3/$1 through $30/$10.
- All nine methods are exploratory because earlier H4 and S/R findings from these historical years have already been observed by the researcher.
- A completed GitHub job does not imply profitable or live-reproducible execution. Tests omit account-specific execution latency, swaps and high-margin requirements.

## Nine candidate causal signal classes
1. `MACD_BODY_EMA`: MACD histogram zero cross with MACD line sign, new H4 candle body >=0.25 ATR14 in trend direction and completed close past EMA20.
2. `MACD_KAMA_EFF`: MACD zero histogram cross with signal sign, Kaufman ER10 >=0.22, completed close above/below KAMA, and KAMA change in direction of event.
3. `MACD_TWO_BAR_HOLD`: MACD baseline cross on first H4; verify next completed H4 still has directional histogram and progresses >=0.10 ATR14 with EMA20 alignment.
4. `PA_MSS_MACD`: previously confirmed 2L/2R swing market-structure shift, H4 close beyond pivot >=0.20 ATR14, body >=0.45 ATR14, MACD line direction agrees.
5. `PA_MSS_ACCEPT_MACD`: pivot break >=0.15 ATR and body >=0.30 ATR; subsequent completed H4 retains pivot-side close, makes directional progress and MACD histogram agrees.
6. `ATR_SUPERTREND_FLIP`: first completed H4 close across previous SuperTrend ATR14 x2.5 band in opposite direction.
7. `CUSUM_EMA_REVERSAL`: positive/negative sequential H4 normalized-return CUSUM with reference k0.20, threshold 3 ATR units and opposite established EMA trend; prospective EMA50 alignment.
8. `OLS_SLOPE_REVERSAL`: compare causal 6- and 18-H4 close regression slopes; confirm persistent slope sign change and price beyond EMA20.
9. `EMA_CROSS_ATR_CONFIRM`: completed EMA20/50 crossing plus 0.15 ATR14 displacement and EMA200 slope alignment.

## Files
- `ph1_backtest/h4_advanced_reversal_detectors.py`
- `ph1_backtest/h4_advanced_reversal_nine_runner.py`
- `.github/workflows/h4-advanced-confirmed-reversal-nine-rr3.yml`

This study cannot establish a permanent change of trend from finite historical prices. A confirmation is an operational historical condition and may reverse again. Compare full marked wealth, trade samples, chronological years, duration/latency and adverse execution cost; do not optimize by cherry-picking a backtest winner.
