# Sample data (synthetic)

**Every number in this folder is invented.** Region names are real, values are not.
The files exist so the prototype can be built before real open data is connected.
Do not show them as findings about Finland.

| File | Content |
| --- | --- |
| `synthetic_regions.csv` | 22 regions: education, language, primary care wait, vacancies, distance to radiotherapy |
| `synthetic_pathway.csv` | region x cancer: screening, stage at diagnosis, days per pathway stage, share treated within target |
| `synthetic_ses_gradient.csv` | region x cancer x education level: screening and stage at diagnosis |
| `thresholds.json` | Decision thresholds, each marked `documented` (from the strategy or roadmap) or `placeholder` |
| `synthetic_recommendations.csv` | Output: one row per detected gap with stage, measure, source and success KPI |
| `synthetic_sensitivity.csv` | Output: how many decisions change when one threshold moves |

```
python3 sample_data/generate.py     # rebuild the data (fixed seed)
python3 sample_data/recommend.py    # detect gaps, pick measures, run sensitivity
```

Measures come from the Implementation Roadmap 2026-2031; the page is in the `measure_source` column.
