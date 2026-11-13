# Finnish Cancer Data — Source Inventory and Access Notes

This is a **source and access catalogue**, not a claim that every listed source has been downloaded or transformed into statistics. The primary challenge source list has **36 distinct embedded URLs**, including institutional pages and research-only services.

## National strategy and implementation

- [National Cancer Strategy 2026–2035](https://files.hackjunction.app/resources/Kansallinen_syopastrategia_2026_2035_FINAL.pdf) — official goals, forecasts and targets; extracted selected values into `national_key_statistics.csv`.
- [Implementation Roadmap 2026–2031](https://files.hackjunction.app/resources/Kansallinen_syopastrategia_toimeenpanon_tiekartta_2026_2031.pdf) — inequalities, governance, planned interventions and resource estimates.
- [FICAN Cancer Strategy](https://fican.fi/toiminta/syopastrategia/) — programme context.
- [Europe's Beating Cancer Plan](https://commission.europa.eu/topics/public-health/european-health-union/cancer-plan-europe_fi) — EU framework.
- [EU Mission on Cancer](https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/eu-missions-horizon-europe/eu-mission-cancer_en) — research framework.

## Public statistics and potential exports

| Source | URL | Extraction status |
| --- | --- | --- |
| Finnish Cancer Registry — annual national cancer report | https://cancerregistry.fi/reports-and-publications/annual-report-on-cancer-in-finland/ | **Selected national outcomes extracted (2023/2024)** |
| Finnish Cancer Registry — breast screening | https://stats.cancerregistry.fi/joukkistilastot/breast.html | **2024 county participation table extracted** |
| Finnish Cancer Registry — preliminary cervical screening | https://stats.cancerregistry.fi/joukkistilastot/ennakkotilastot/cervix_preliminary.html | **2025 subgroup indicators extracted** |
| Finnish Cancer Registry — statistics portal | https://syoparekisteri.fi/tilastot/ | Further cancer-type/region extraction pending |
| Finnish Cancer Registry — screening portal | https://cancerregistry.fi/statistics/screening-statistics/ | Additional programmes and tables pending |
| Colorectal screening statistics | https://stats.cancerregistry.fi/joukkistilastot/colorectal.html | **2024 regional participation by sex extracted via Sotkanet indicator 6103** |
| THL data and statistics | https://thl.fi/data-ja-tilastot | Indicator selection pending |
| Sotkanet indicator bank | https://sotkanet.fi/sotkanet/fi/index | **Extracted via `fetch_sotkanet.py`: indicators 3621, 6103, 3620 (screening), 3099, 180, 187, 6411 (regional context); REST API at `https://sotkanet.fi/rest/1.1`** |
| Statistics Finland, causes of death | https://stat.fi/fi/tilasto/ksyyt | Table selection pending |
| Kela open data | https://tietotarjotin.fi/tilastodata/2242438/avoin-data | Cancer-specific measure selection pending |
| Kela reimbursement rights | https://vip.avoindata.fi/data/fi/dataset/voimassa-olleet-alkaneet-ja-paattyneet-laakekorvausoikeudet | Eligibility, scope and aggregation checks pending |
| Finnish Statistics on Medicines 2025 | https://www.julkari.fi/items/3dfdc48f-2d1a-416e-9795-eca4d3df72ad | Review publication and definitions |
| NORDCAN | https://nordcan.iarc.who.int/en | Nordic comparable series pending |

## Organisational sources and research access

- [FICAN quality registries](https://fican.fi/toiminta/arviointi-ja-seuranta/syopien-laaturekisterit/)
- [FICAN national centre](https://fican.fi/tietoa-meista/fican/)
- [Cancer Society of Finland](https://www.cancersociety.fi/)
- [iCAN](https://ican.fi/flagship-project/) — research project; not assumed open patient-level data
- [FinRegistry](https://www.finregistry.fi/finnish-registry-data) — research registry data, access restrictions may apply
- [Findata](https://findata.fi/) — Finnish data-permit authority; NOT a public patient-data API

## Biobanks (permission-controlled research resources, NOT open statistical feeds)

- [Fingenious](https://site.fingenious.fi/) and [FINBB](https://finbb.fi/)
- [Helsinki Biobank](https://www.helsinki.fi/en/infrastructures/biobank-platform/services-and-infrastructures/helsinki-biobank)
- [Auria Biobank](https://www.auria.fi/biopankki/)
- [Finnish Clinical Biobank Tampere](https://www.pirha.fi/web/english/for-professionals/finnish-clinical-biobank-tampere)
- [Central Finland Biobank](https://www.hyvaks.fi/sairaala-nova/biopankki)
- [Eastern Finland Biobank](https://www.ita-suomenbiopankki.fi/)
- [Biobank Borealis](https://oys.fi/en/front-page/for-researchers/biobank-borealis-of-northern-finland/)
- [Blood Service Biobank](https://www.veripalvelu.fi/biopankki/)
- [Hematological Biobank](https://www.hematologinenbiopankki.fi/)
- [THL Biobank](https://thl.fi/en/research-and-development/thl-biobank)

## Integration principles

1. Import only aggregate, publishable data with a valid reuse basis.
2. Preserve source URL, reference year, capture date, numerator/denominator, geography, rate definition and revision status.
3. Respect programme differences, reporting delays and possible small-cell suppression.
4. Never fabricate missing source statistics or claim that restricted data are public.
5. For all cancer types: represent available evidence and clearly expose coverage gaps.
