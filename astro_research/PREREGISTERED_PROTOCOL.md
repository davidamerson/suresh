# PRE-REGISTERED PILOT: Does astronomical geometry improve event forecasts?
Frozen before pulling historical outcome data. Date: 2026-11-06.

## Scope
This is a controlled pilot of QUANTIFIABLE astronomical proxies inspired by astrology. It is **not** a validated test of every named astrological school, and cannot validate natal dasha, individual nadi consultation, horary, or full BaZi without their own traditional inputs. Do not equate descriptive astronomical co-occurrence with prediction or causality.

Sources, available without credentials:
- USGS global catalog, moment/local magnitude >=7.0, daily UTC dates 2000-2025; outcome = >=1 catalogued M7+ quake during that UTC day. Train through 2017, final holdout 2018-2025.
- FRED SP500 official daily index, 2016-2025; outcome = same day's index return <= -1%. Astronomical state at 00:00 UTC before that day's US closing auction. Train through 2021, final holdout 2022-2025.
- UCDP GED 26.1 global organized violence, calendar dates 1989-2025; outcome = day with global confirmed-date best-estimate deaths > training-period 90th percentile. Train through 2010, final holdout 2011-2025. Include known prior-week deaths as nonastrological baseline. If inaccessible, mark unavailable; do not invent.

## Astronomical calculations
Swiss Ephemeris via Python pyswisseph, Moshier computation (FLG_MOSEPH, no remote ephemeris file); tropical geocentric ecliptic longitudes of Sun Moon Mercury Venus Mars Jupiter Saturn daily at 00:00 UTC. Sidereal longitude = tropical minus Lahiri ayanamsa. Angular aspects = shortest separation in degrees between 0 and 180, with fixed 5 or 6 degree orb. Harmonic encodings: sin/cos 1st and 2nd harmonics, Moon-Sun 30-tithi cycle, 27 sidereal lunar nakshatra sectors, 12 sidereal sign segments, Moon-Sun phases and lunar-solar quadrature, Jupiter-Saturn conjunction/opposition and larger cycles. East Asian sexagenary proxy only, not canonical BaZi.

## PRE-LOCKED model comparison
All are ridge-like regularized logistic regression (StandardScaler plus LogisticRegression C=0.05, max_iter=4000, no hyperparameter tuning). Never fit a feature scaler, threshold, or classifier on final holdout outcomes.
- nonastrological control: calendar annual sin/cos, weekday, year trend and prior known event/price history.
- control + lunar phase
- control + western/tropical planets and angular aspects
- control + vedic/sidereal rasi, nakshatra, tithi
- control + persian/mundane Jupiter-Saturn cyclic aspects and Mars-Saturn angles
- control + East Asian day-cycle proxy (NOT the canonical BaZi rules)
- control + all the above
- control + deterministic random-period sinusoid placebo (negative control)
Predeclared event cutoffs and train/test date ranges are fixed, not selected retrospectively to improve results.

## Metrics and statistical control
Report holdout ROC AUC, average precision, Brier score, event rate, lift top 10%, baseline incremental delta ROC AUC and Brier skill. Use approximate within-year circular-shift null that retains outcome-year event rate/clustering and compare observed max improvement across all candidate methods, 300 permutations seed=20261106. This is exploratory, not a statistically definitive causal test; dates and astronomy can be seasonally correlated. Model comparisons need genuinely forward prospective new outcomes to confirm.

Report every failed data source, data checksum and CSV feature provenance; retain frozen exact source and code. Never report a prediction edge if the actual holdout comparison fails.
