# Supplemental chronological robustness analyses: 6 split tests

**2026-11-06: Exploratory robustness checks after seeing primary results. These are not independent future data.**

The primary pre-registered training windows are unchanged. This experiment varies only a fixed training cutoff per task and uses the same freeze-dated astronomy-feature generation and fixed logistic regression C=0.05, plus the same official USGS/UCDP and archived FRED-source data. It replays *all* models and reports *all* splits, not a filtered selection of winning results.

| Dataset | Training through | Test days | Baseline ROC AUC | Best of six astrology proxy groups | Best ROC AUC | Vedic Brier | Control Brier | Max-stat shift-null p |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| markets | 2019 | 1508 | 0.6386 | lunar | 0.6278 | 0.1260 | 0.1258 | 0.993 |
| earthquakes | 2020 | 1826 | 0.5215 | lunar | 0.5650 | 0.0364 | 0.0364 | 0.392 |
| earthquakes | 2012 | 4748 | 0.4974 | all | 0.5107 | 0.0356 | 0.0357 | 0.787 |
| conflicts | 2015 | 3653 | 0.8133 | lunar | 0.8112 | 0.3276 | 0.1885 | 0.993 |
| conflicts | 2020 | 1826 | 0.8276 | east_proxy | 0.8263 | 0.1432 | 0.1425 | 1.000 |
| markets | 2022 | 752 | 0.5897 | east_proxy | 0.5684 | 0.0983 | 0.1102 | 0.944 |

## Interpretations
- The 2022-2025 S&P 500 primary East Asian 60-day/year periodicity proxy showed ROC AUC 0.6525, yet when the training cutoff moved to 2019 (test 2020–2025), best astronomy proxy fell below baseline (0.6278 lunar vs 0.6386 baseline). Cutoff 2022 (test 2023–2025) similarly had best astronomy 0.5684 (east cycle) below baseline 0.5897. This is NOT a robust validated BaZi benefit, and the periodicity proxy is not canonical BaZi.
- In UCDP global high-fatality forecasting, original `vedic` features had much better Brier 0.266 than uncalibrated baseline 0.463 on test 2011–2025 but significantly worse AUC. Cutoff 2015: Vedic Brier 0.3276 vs baseline 0.1885, worse. Cutoff 2020: Vedic 0.1432 vs baseline 0.1425, slightly worse. The primary Brier advantage does not remain consistent under changed era/cutoffs and is compatible with nonstationarity and spurious extrapolation.
- USGS quake test is noisier: observed positive but weak lunar/vedic ranking shifts in some holdouts, with all approximate max-stat within-year permutation p values >0.05 (2020 train split p≈0.392, 2012 p≈0.787). No replicated reliable advantage established.
- For each split, astronomical features represent observational mathematical proxies and do not test a full practitioner's independent traditional forecast. No causal inference.

## Reproducibility
- [All 6 split job results](https://github.com/davidamerson/suresh/actions/runs/42258335513)
- `../secondary_temporal_robustness.py` and `../../.github/workflows/astrology-secondary-temporal-validation.yml`.
- Per job model_comparison.csv, summary.json, provenance available in GitHub Actions artifacts for 30 days.
- All 48 rows permanently retained in `secondary_48_model_scores_20261106.csv`.

## Further audit caution
Global UCDP events are intensely time-clustered. Within-year circular-shift p values are only exploratory approximate nulls, not formally calibrated p-values for clustered events and complex financial outcomes. Better prospective independent periods, clustered bootstrap confidence intervals, region-specific hazard baselines, and registered practitioner algorithms remain necessary.
