# Pipeline run report

Run finished 2026-11-14T04:42:53+00:00 (68 s). Analysis year 2024.

## Reconciliation

| Rows read | Published | of which imputed | Quarantined | Out of scope | Duplicates removed | Balanced |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 833,394 | 767,332 | 44 | 5 | 56,772 | 9,329 | yes |

## Steps

### 01 ingest
- rows read: 833,394
- lines skipped by an adapter: 48

### 02 profile
- rows profiled: 833,394

### 03 validate_schema
- rows passed: 833,394

### 04 standardise
- rows standardised: 833,389
- rejected: 5
- rejected: unknown region: 5

### 05 scope_filter
- rows kept: 776,617
- filtered out: 56,772
- filtered out: level maakunta: 7,288
- filtered out: level sairaanhoitopiiri: 7,721
- filtered out: level erva: 1,895
- filtered out: level aluehallintovirasto: 2,440
- filtered out: level seutukunta: 20,517
- filtered out: level suuralue: 1,474
- filtered out: level nuts1: 523
- filtered out: level yta: 2,019
- filtered out: level pohjoismaat: 324
- filtered out: level eurooppa: 2,091
- filtered out: level unknown: 10,480

### 06 deduplicate
- duplicates removed: 9,329
- duplicates removed: across files: 9,329
- rows kept: 767,288

### 07 quality_checks
- flagged: outlier: 749
- flagged: small_cell: 368
- flagged: preliminary: 28
- flagged: strategy_baseline: 1
- flagged: projection: 1
- flagged: strategy_target: 3
- flagged: roadmap_estimate: 1
- rows passed: 767,288

### 08 completeness
- indicators checked for region-year coverage: 13
- gaps: region-year missing: 44
- gaps: no open data: 8

### 09 impute
- values imputed: 44
- values imputed: temporal_mean: 44

### 10 integrate
- observations in clean layer: 767,332
- observations in analysis subset: 6,600

### 11 enrich
- context values attached: 138

### 12 derive
- confidence intervals computed: 405
- target status: at_or_above_target: 71
- target status: below_target: 236
- target status: near_target: 22
- denominators derived from participants and percentage: 177
- outcome figures with statistics: 865

### 13 categorise
- region categories assigned: 132
- observations tagged, evidence B: 924
- observations tagged, evidence A: 400
- imputed observations left out of the measures: 44

### 14 measure
- gaps measured, evidence A: 151
- gaps measured, evidence B: 42
- evidence B patterns that survive correction: 1
- gaps measured, evidence B-municipality: 15
- municipality patterns that survive correction: 9
- barriers listed, evidence C: 6

### 15 recommend
- gaps without a recommendation: not clearly above zero: 5
- national recommendations: 9
- regional recommendations: 29

### 16 trends
- cancer sites with a mortality series: 18
- region-entitlement figures: 110

### 17 compare_runs
- figures unchanged: 6,600

### 18 publish
- fact sheets written: 26
- rows read: 833,394
- rows accounted for: 833,394
