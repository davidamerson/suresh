# Multi-Tradition Astrology Proxies vs Real Events: Empirical Pilot (2026-11-06)

## Executive finding
**NO convincingly validated astrological predictive advantage found in the PRIMARY held-out ROC-AUC comparisons in three registered tasks.** This is not a disproof of every traditional practice; many authentic natal, dasha, Nadi, Jaimini, Zi Wei and horary methods cannot be represented by date-only public events and have not been tested. Our measured models are explicitly mathematical astro-inspired proxies.

We computed actual Sun/Moon and 8 other planetary geocentric longitudes for every eligible day using Swiss Ephemeris Moshier, formed tropical and sidereal Lahiri zodiac cycle features, aspects, lunar tithi/nakshatra cyclical proxies, Persian Jupiter/Saturn cycle proxies, and East Asian sexagenary periodicity proxy (NOT canonical BaZi). Dates all UTC and computed using 00:00 UTC, without outcomes in feature generation.

Three independently sourced event datasets and chronological holdout windows:
1. **Global earthquake days** 2000–2025, USGS magnitude >=7; train 2000–2017, test 2018–2025.
2. **Global precise-date organized violence high-fatality days** 1989–2025, UCDP GED v26.1; threshold >142 global fatalities/day (90th percentile training), train 1989–2010, test 2011–2025. This is NOT war onset or election outcome forecasting. Dataset shifted from lower to much higher baseline violence rate, so nonstationarity affects calibration.
3. **S&P 500 same-day drop of at least 1%**, FRED close historical archive mirrored in public GitHub `datasets/s-and-p-500`. Train Nov 2016–2021 and test 2022–2025. 00:00 UTC features precede each US close. The primary FRED direct server request remained inaccessible/slow; Stooq rejected automated access; mirrored archive used with checksum. This is NOT a transaction-cost trading backtest.

## Performance (fixed logistic regularization, all candidates disclosed)

ROC AUC is ranking quality, 0.50 is chance for balanced positive/negative pair choice. Higher is better. Brier is squared probability prediction error, lower is better; Brier improvement is Control minus Model.

| Task | Model | Holdout AUC | Delta AUC | Brier | Brier improvement vs control |
|---|---|---:|---:|---:|---:|
| earthquakes | control | 0.499 | +0.000 | 0.0347 | +0.0000 |
| earthquakes | lunar | 0.527 | +0.028 | 0.0347 | +0.0000 |
| earthquakes | western | 0.505 | +0.006 | 0.4204 | -0.3857 |
| earthquakes | vedic | 0.538 | +0.039 | 0.0347 | +0.0000 |
| earthquakes | mundane | 0.471 | -0.028 | 0.0349 | -0.0002 |
| earthquakes | east_proxy | 0.456 | -0.042 | 0.0348 | -0.0001 |
| earthquakes | all | 0.501 | +0.002 | 0.4242 | -0.3895 |
| earthquakes | placebo | 0.473 | -0.026 | 0.0358 | -0.0011 |
| conflicts | control | 0.823 | +0.000 | 0.4632 | +0.0000 |
| conflicts | lunar | 0.813 | -0.011 | 0.4637 | -0.0005 |
| conflicts | western | 0.719 | -0.104 | 0.5386 | -0.0753 |
| conflicts | vedic | 0.732 | -0.091 | 0.2660 | +0.1973 |
| conflicts | mundane | 0.698 | -0.126 | 0.4146 | +0.0486 |
| conflicts | east_proxy | 0.820 | -0.004 | 0.4417 | +0.0215 |
| conflicts | all | 0.646 | -0.177 | 0.5327 | -0.0695 |
| conflicts | placebo | 0.725 | -0.098 | 0.4870 | -0.0237 |
| markets | control | 0.560 | +0.000 | 0.1193 | +0.0000 |
| markets | lunar | 0.545 | -0.015 | 0.1197 | -0.0005 |
| markets | western | 0.446 | -0.114 | 0.2871 | -0.1679 |
| markets | vedic | 0.626 | +0.067 | 0.1323 | -0.0131 |
| markets | mundane | 0.474 | -0.085 | 0.4415 | -0.3222 |
| markets | east_proxy | 0.652 | +0.093 | 0.1227 | -0.0035 |
| markets | all | 0.445 | -0.114 | 0.2881 | -0.1689 |
| markets | placebo | 0.505 | -0.055 | 0.1281 | -0.0088 |

### Exploratory significance check
Max incremental AUC across seven tested alternative groups, including placebo, compared with 300 within-year circularly shifted outcome series:
- earthquakes: maximum observed AUC gain +0.0389 ; approximate max-stat adjusted p=0.3588.
- conflicts: maximum observed AUC gain -0.0038 ; approximate max-stat adjusted p=0.4684.
- markets: maximum observed AUC gain +0.0929 ; approximate max-stat adjusted p=0.5615.

**None reached an adjusted p below 0.05 in this preliminary procedure.** These permutation p values are approximate because time-shifting year-wise outcomes also perturbs relationships with seasonality and market regimes; a genuine future forward test and multi-year replication are necessary. An exploratory result is NOT proof of a mechanism.

### Lunar full/new exposure as an explicit contrast
- earthquakes: full/new proxy day 27/766; other days 78/2156; rate ratio 0.9743.
- conflicts: full/new proxy day 864/1434; other days 2563/4045; rate ratio 0.9509.
- markets: full/new proxy day 34/261; other days 105/742; rate ratio 0.9206.

### Important metrics that disagree
- For global conflicts, control has strongest ROC AUC (0.8233) while `vedic` family has much lower **Brier 0.2660 vs control 0.4632**, despite worse AUC (0.7322). This is an unconfirmed calibration effect, potentially from major historical regime shift and overfitting of slow celestial cycles. Do NOT suppress this result or declare a true astrology advantage; requires strict further temporal validation.
- For S&P500, East Asian periodicity **proxy** AUC 0.6525 vs control 0.5596, but Brier 0.1227 vs 0.1193 (worse) and adjusted circular-shift p≈0.5615. The proxy is NOT actual Four Pillars / BaZi and cannot be represented as validation of that tradition.
- Combining ALL astrology feature families decreased AUC in all three observed tasks and caused severe model probability calibration problems in the quake and stock tasks. Large numbers of astronomical features cause statistical overfit and slow-planet temporal extrapolation; combination is not automatically advantageous.

### Event-count nuances
USGS: 387 recorded >=M7 earthquakes in 2000–2025, 359 distinct UTC event-days, 105 heldout event-days in 2018–2025.
UCDP: 417,968 event rows, of which 358,130 have the exact-date precision flag used in our test; no complete election or government-transition study.
Stock returns: 2,299 valid trading dates in 2016–2025 after first-return drop; test 1,003 dates, 139 down-1%-days.

## Sources and SHA256 checksums
- **earthquakes**: https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&starttime=2000-01-01&endtime=2026-01-01&minmagnitude=7 ; SHA256 `7e7e545adf42b3dee71e341cc2005f425c623431f43b29e4937a2d959e07419f`; 2922 test days; 105 positive days; permutation p (approx max over families) 0.3588; [run](https://github.com/davidamerson/suresh/actions/runs/42256919683)
- **conflicts**: https://ucdp.uu.se/downloads/ged/ged261-csv.zip ; SHA256 `8c941d84954e555ee2e54f40fa04d9203bf1e2f962203d0a9930966c4947c667`; 5479 test days; 3427 positive days; permutation p (approx max over families) 0.4684; [run](https://github.com/davidamerson/suresh/actions/runs/42256919683)
- **markets**: https://raw.githubusercontent.com/datasets/s-and-p-500/main/archive/fred_sp500.csv ; SHA256 `1be28db4d187fc2abc35c89b9bdc93c60344f9cbc031dd5e914213a7b7ce0da0`; 1003 test days; 139 positive days; permutation p (approx max over families) 0.5615; [run](https://github.com/davidamerson/suresh/actions/runs/42257923501)

## Method register
- [Locked protocol](../PREREGISTERED_PROTOCOL.md).
- `../astral_global_hypothesis_test.py` main engine.
- `../astral_market_fred_public_archive.py` replaces ONLY FRED fetch endpoint with checksum-mirrored archival FRED data.
- `../secondary_temporal_robustness.py` additional post-hoc chronological splits to test stability. Do not conflate them with primary locked holdout.

## Claims NOT supported by these data
This research does NOT establish:
- astrology is proven or disproven in general;
- individual personality/longevity/health/life outcomes could be read from natal charts;
- global astrological “100% accurate” disaster, war, or market forecasting;
- an economic or forex trading edge after real costs;
- planetary causation of the observed event rates.

Observed lunar-tidal physics may matter for narrowly-defined geophysical conditions, not a general confirmation of all astrology. See USGS lunar/earthquake FAQs and USGS 2018 study of M>=8 events. Controlled personality experiments include Carlson (Nature 1985), Ertel's methodological reanalysis (Journal of Scientific Exploration, 2009/2010), and Hartmann et al 2006 large-sample date-of-birth assessment; none establish 100% accurate life prediction.

## Follow-up priorities
1. Multiple independent chronological time windows, alternate training endpoints, and confidence intervals for true out-of-sample delta AUC/Brier.
2. Real, precise traditional algorithms, specified by subject-matter practitioners before outcomes are revealed; especially natal Dasha and Horary require different datasets and should not be unfairly “tested” using earthquake dates.
3. Prospectively locked forecasts for 2027 and later before knowing outcomes.
4. Separate matched controls for events by region, season, time zone and underlying baseline hazard; test source choice and multiple-testing penalties.
