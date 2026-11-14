# Pipeline run report

Run finished 2026-11-14T00:06:52+00:00 (13 s). Analysis year 2024.

## Reconciliation

| Rows read | Published | of which imputed | Quarantined | Out of scope | Duplicates removed | Balanced |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 804,804 | 756,185 | 44 | 5 | 48,635 | 23 | yes |

## Steps

### 01 ingest
- rows read: 804,804

### 02 profile
- rows profiled: 804,804

### 03 validate_schema
- rows passed: 804,804

### 04 standardise
- rows standardised: 804,799
- rejected: 5
- rejected: unknown region: 5

### 05 scope_filter
- rows kept: 756,164
- filtered out: 48,635
- filtered out: level maakunta: 6,129
- filtered out: level sairaanhoitopiiri: 6,438
- filtered out: level erva: 1,585
- filtered out: level aluehallintovirasto: 2,025
- filtered out: level seutukunta: 16,296
- filtered out: level suuralue: 1,183
- filtered out: level nuts1: 418
- filtered out: level yta: 1,666
- filtered out: level pohjoismaat: 324
- filtered out: level eurooppa: 2,091
- filtered out: level unknown: 10,480

### 06 deduplicate
- duplicates removed: 23
- duplicates removed: across files: 23
- rows kept: 756,141

### 07 quality_checks
- flagged: outlier: 1,278
- flagged: small_cell: 1,368
- flagged: preliminary: 10
- flagged: strategy_baseline: 1
- flagged: projection: 1
- flagged: strategy_target: 3
- flagged: roadmap_estimate: 1
- rows passed: 756,141

### 08 completeness
- indicators checked for region-year coverage: 13
- gaps: region-year missing: 44
- gaps: no open data: 6

### 09 impute
- values imputed: 44
- values imputed: temporal_mean: 44

### 10 integrate
- observations in clean layer: 756,185
- observations in analysis subset: 5,650

### 11 enrich
- context values attached: 138

### 12 categorise
- region categories assigned: 132
- observations tagged, evidence B: 924
- observations tagged, evidence A: 321
- imputed observations left out of the measures: 44

### 13 measure
- gaps measured, evidence A: 99
- gaps measured, evidence B: 42
- barriers listed, evidence C: 5

### 14 publish
- rows read: 804,804
- rows accounted for: 804,804
