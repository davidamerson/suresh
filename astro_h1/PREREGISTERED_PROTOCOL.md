# XAUUSD X Astrology: H1 Candle Open/Close Cross-History Trial
**Research protocol fixed on 2026-11-07 before checking newly extracted historical H1 results.**
## Core hypotheses
H1 — Every completed Monday-Friday UTC hour has OHLC characteristics such as direction and range. Test its association with lunar tithi/nakshatra, planetary aspects, planetary retrogrades, Saturn/Rahu/Ketu transit, locations' weekday-based Rahu Kalam, local planetary Hora, and solar/sidereal ascendant.
H2 — Particular calendar month/day/hour candle directions may recur in the next year; compare same YYYY-1 month-day/hour and 52-week same weekday/hour.
H3 — A combined astronomical-panchang feature family might predict direction, numerical close-open return or intrahour range beyond price-history/market-hour/weekday/annual-season baselines.
## Data treatment
- Fixed real Exness XAUUSD Raw Spread source `https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{YYYY}/{MM}/Exness_XAUUSD_Raw_Spread_{YYYY}_{MM}.zip` for Jan 2020 through Oct 2026; no Nov incomplete month.
- Process every Timestamp/Bid/Ask row in full historical monthly ZIP, SHA256 verify each source, reject nonchronological/invalid quotes. Aggregate hour O/H/L/C from first/maximum/minimum/last **BID** quotes and record opening+closing Ask.
- Exclude partial hours/holidays/weekends: Mon-Fri UTC, >=10 quote ticks, first quote ≤600s from start and last quote ≤600s from end. Partial week and daily economic news are not labeled unless verified; unmodeled release events are confounders.
- Astronomical calculations use Swiss Ephemeris and Lahiri sidereal ayanamsa; tropical planetary aspects, retrograde longitude speed; moon 27 lunar mansions/30 tithis/27 nitya yoga/60 karana portions; mean Rahu/Ketu, basic Graha Drishti, Moon-Saturn sign proximity.
- Geographical solar times and Hora are calculated independently for London, Colombo and New York; Rahu/Yama/Gulika windows are sunrise-to-sunset eighths **dependent on local weekday**, so calendar-time aliases must be controlled.
- Birth-oriented Sade Sati and Vimshottari Mahadasha cannot be computed as an authoritative gold instrument natal chart without an accepted birth-event time/location; **do not invent it**.
## Prediction protocol
- No historical OHLC signal beyond opening spread/open bid and earlier candles is permitted at time of signal. All planetary features computed at first actual quote of the H1.
- Fit standard Ridge regression with alpha=150 and LogisticRegression C=0.08 once on data through **2024-12-31 UTC**. Evaluate untouched-by-this-model chronological years **2025–2026 Oct**, with per-year results. Original historical gold data has been studied elsewhere so this cannot claim fully untouched prospective testing.
- Predeclared families: market/calendar only, solar, lunar, Panchang, aspects, retrograde, Rahu+Hora, lunar nodes+Saturn, all astronomical, plus astronomy-only controls. Prefer net gain vs baseline in *both* tested years, not a single lucky year.
- Primary metrics open-to-close USD MAE, direction AUC/accuracy, high-low range MAE. Optional costed simulated sign-confidence trades threshold 0.57/0.43 with first/last archived Bid/Ask + $0.07/0.01 lot commission. First/last tick fills **not guaranteed executable**; no swap, HMR or latency.
- Test annual recurrence with paired H1 body sign, Pearson/Spearman of body changes, and weekday hour effects. Repeating time-of-day market volatility is expected from human sessions and does NOT establish planetary causation.
- Same-year H1 candle price *levels* are nonstationary; evaluate open-close changes and direction instead. No post-hoc single high-correlation feature is sufficient to claim predictive significance; avoid cherry-picked planet orbs.
## Reproducibility
- `astro_h1/extract_exness_h1.py`: full source ZIP tick-to-H1 extraction.
- `astro_h1/calc_astro_h1_features.py`: only-at-open astronomical and solar features.
- `astro_h1/analyze_h1_astro_predictive_relationships.py`: time-order controls, regression/classification and 2025–26 replay.
- Workflow `.github/workflows/astro-h1-extract-2020-2026.yml` and `.github/workflows/astro-h1-cross-ephemeris-forecast.yml`.
