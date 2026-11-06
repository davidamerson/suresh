# Survey of 29 distinct astrological and related historical systems

This is a research inventory, not an endorsement of predictive validity and not proof of exhaustiveness. Some are full divination systems, not astrology in the narrow astronomical sense. Some concepts have divergent local versions and interpretations. No fair scientific conclusion can be drawn from a proxy when a school's authentic prediction rules were not used.

## Goal and evidence grades
- **Implemented/math proxy**: astronomical or calendrical input represented by a measurable feature in the 2026-11-06 historical pilot. This is not equivalent to validating a traditional reading.
- **Formalizable but not tested**: transparent chart rules exist; cannot evaluate without matching independent individual or event records.
- **Not standardized**: first obtain a canonical prediction text or pre-committed practitioner rule, before observing the target outcome.
- **Predictive edge demonstrated**: requires high-quality outcome labels, controls, clustered uncertainty, multiyear robust holdout, preregistered prospects. None meet this grade today.

## Inventory
| Region | System | Main numerical input | Pilot empirical status |
|---|---|---|---|
| South Asian | Parashari natal | D1 lagna, graha lords, yogas, varga | not directly tested |
| South Asian | Vimshottari Dasha | 120-year 9-lord cycles from birth Moon nakshatra | not directly tested |
| South Asian | Ashtottari/Yogini Dashas | alternative planetary periods | not directly tested |
| South Asian | Jaimini Chara Karakas and Chara Dasha | karaka degrees, sign aspects, variable sign periods | not directly tested |
| South Asian | Nadi/Bhrigu traditions | manuscript-specific fixed planetary or fingerprint rules | cannot yet formalize uniformly |
| South Asian | Krishnamurti Paddhati (KP) | nakshatra 9 sub-lords, cuspal lord, star lord | not directly tested |
| South Asian | Ashtakavarga | sign transit bindu point scores | not directly tested |
| South Asian | Tajika/Varshaphala | annual solar returns, Tajika aspects | not directly tested |
| South Asian | Prashna/Horary | question-time ascendant, significators | not directly tested |
| South Asian | Muhurta/electional | chosen action timing with planetary conditions | not directly tested |
| South Asian | Panchanga tithi/nakshatra | Moon-Sun tithi and sidereal lunar sectors | partial mathematical proxies tested |
| Sri Lanka | Hora/Nekath/Lagna | planetary hour, auspicious calendar, local rising | not directly tested |
| South Asian | Medini/mundane Jyotish | transits eclipses planetary ingress and signs | partial planetary proxies tested |
| Western | Hellenistic natal | sect, annual profections, time lords, lots | not directly tested |
| Western | Medieval/Renaissance mundane | ingress, eclipse, Jupiter-Saturn great conjunction | Jupiter-Saturn proxies tested, not full method |
| Western | Modern natal/transits | planetary sign/aspect transits natal chart | not directly tested |
| Western | Secondary progressions/Solar Arc | symbolic time-degree transformations | not directly tested |
| Western | Uranian/Hamburg and Cosmobiology | midpoints, 90-degree dial, planetary pictures | not directly tested |
| Western | Financial astrology and lunar market rules | Moon phase, planetary aspects and market cycles | lunar/planetary proxies tested on index drop days |
| Persian-Arabic | Great Conjunction astrology | Jupiter-Saturn ~20yr conjunction and triplicity shifts | Jupiter-Saturn angle proxies tested |
| Persian-Arabic | Arabic Lots / Pars Fortuna | weighted angles ascendant Sun Moon | not directly tested |
| East Asian | BaZi / Four Pillars | lunar-solar year-month-day-hour sexagenary chart | ONLY noncanonical 60-day/year periodicity proxy tested |
| East Asian | Zi Wei Dou Shu | 12 palaces and multiple calculated stars | not directly tested |
| East Asian | Korean Saju | Four Pillars stems branches | not directly tested |
| East Asian | Qi Men Dun Jia | time-dependent rotating palace chart for choices | not directly tested |
| East Asian | Nine Star Ki | year/month/day 九星 cycles | not directly tested |
| Tibetan | Nagtsi / Tibetan astrology | Chinese-derived elements and Tibetan calendrical calculations | not directly tested |
| Southeast Asian | Thai Hora and Burmese Mahabote | weekday, planetary and calendrical rules | not directly tested |
| Mesoamerican | Maya Tzolkin calendrical cycles | 260-day ordered day-name/number cycle | not directly tested |

## Why 'all astrology combined' is not the same as summing all features
The main computational pilot combined feature groups derived from real daily astronomical longitudes and sexagenary proxy clocks; it did **not** implement full Parashari, Jaimini, KP, Nadi, Horary, Zi Wei or BaZi readings. Such traditions may require birth hour, locality, rising sign, official question timestamp, practitioner judgement, a canonical manuscript, or an action to be scheduled.

A fair comparison of full schools requires:
1. Freeze birth/location/house/ayanamsa/ephemeris conventions and anonymized adjudicated outcomes.
2. For each method, register exact pre-event date windows, binary answers and numerical probabilities; record unchosen predictions and no-signal periods.
3. Use blind matched charts/decoys and placebo calendar cycles, match demographic and seasonal baselines.
4. Split train/calibration/untouched holdout by person, by event type and by era, not by duplicated records.
5. Test each school separately and use cross-validated stacking only on training data; evaluate all combined versus weighted combination on locked final data.
6. Pre-specify a multiple-testing correction. Confirm again prospectively on dates unavailable when the models were finalized.

## Sources for reconstructing actual methods
- Vimshottari period computation reference: https://jyotipy.readthedocs.io/en/latest/api/dasha.html
- KP sublords (source-specific implementation): https://kpstellarastro.com/kp-sub-lord-table
- Persian/Sasanian Jupiter-Saturn Great Conjunctions: https://www.iranicaonline.org/articles/planets/
- Ayanamsa and variants: https://openpanchanga.org/learn/ayanamsa
- Zi Wei Palace overview: https://www.tianeon.com/en/learn/zi-wei-dou-shu-twelve-palaces

**Important:** Methods being mathematically computable is distinct from their future-event predictive performance. The first empirical pilot is already archived as 24 primary rows and 48 secondary rows in the GitHub repo.
