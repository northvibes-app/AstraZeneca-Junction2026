# Do measures against unequal screening pay off for the health system?

Written by `research/calculations.py`. Do not edit by hand; change `research/assumptions.csv` and run the script again.

## The question

Cancer care cost Finland about 1.4 billion euros in 2024. The National Cancer Strategy expects 2.6 billion a year by 2035 if nothing specific is done. The two roadmap measures against unequal screening participation have budgets of 1.5 million and 0.4 million euros for 2026-2031. This file estimates what the health system gets back for that money.

## Result per measure

All amounts are for the health system. Each column is one set of assumptions. The pessimistic column sets every uncertain value to its unfavourable end at the same time, the optimistic column every value to its favourable end. Both extremes are unlikely; they mark the range.

### Measure 1.1.1: People with primary or unknown education

| | Pessimistic | Central | Optimistic |
| --- | ---: | ---: | ---: |
| Extra participants per year (all three programmes) | 4 746 | 9 493 | 18 986 |
| Cancers found earlier per year | 10.5 | 21.6 | 45.9 |
| Colorectal cancers prevented per year | 5.8 | 23.2 | 61.8 |
| Extra screening cost per year | 179 237 € | 253 962 € | 356 302 € |
| Extra follow-up examinations per year | 93 168 € | 103 520 € | 111 802 € |
| Treatment of overdiagnosed breast cancers per year | 46 416 € | 76 687 € | 88 795 € |
| Saving on later treatment per year, in today's money | 204 080 € | 1 288 154 € | 5 681 533 € |
| Cost of the measure per year (roadmap budget / 6) | 250 000 € | 250 000 € | 250 000 € |
| **Net result per year** | -364 741 € | 603 985 € | 4 874 634 € |
| **Net result over 2026-2031** | -2 188 448 € | 3 623 909 € | 29 247 804 € |
| Largest budget at which the measure still pays for itself | 0 € | 5 123 909 € | 30 747 804 € |
| Saving per euro spent | 0.36 € | 1.88 € | 7.04 € |

By programme, central assumptions, per year:

| Programme | Gap (points) | Gain used | Extra participants | Extra cost | Saving |
| --- | ---: | ---: | ---: | ---: | ---: |
| Colorectal | 17.8 | 7.7 | 5 280 | 235 519 € | 1 191 221 € |
| Breast | 22.3 | 6.2 | 2 301 | 198 650 € | 96 933 € |
| Cervical | 29.5 | 6.1 | 1 912 | not calculated | not calculated |

### Measure 1.3.1: People with a native language other than Finnish or Swedish

| | Pessimistic | Central | Optimistic |
| --- | ---: | ---: | ---: |
| Extra participants per year (all three programmes) | 2 577 | 5 154 | 10 308 |
| Cancers found earlier per year | 4.2 | 8.8 | 18.8 |
| Colorectal cancers prevented per year | 1.4 | 5.5 | 14.7 |
| Extra screening cost per year | 79 578 € | 119 464 € | 177 803 € |
| Extra follow-up examinations per year | 22 140 € | 24 600 € | 26 568 € |
| Treatment of overdiagnosed breast cancers per year | 23 661 € | 39 092 € | 45 264 € |
| Saving on later treatment per year, in today's money | 53 796 € | 332 492 € | 1 502 074 € |
| Cost of the measure per year (roadmap budget / 6) | 66 667 € | 66 667 € | 66 667 € |
| **Net result per year** | -138 249 € | 82 670 € | 1 185 772 € |
| **Net result over 2026-2031** | -829 496 € | 496 018 € | 7 114 634 € |
| Largest budget at which the measure still pays for itself | 0 € | 896 018 € | 7 514 634 € |
| Saving per euro spent | 0.28 € | 1.33 € | 4.75 € |

By programme, central assumptions, per year:

| Programme | Gap (points) | Gain used | Extra participants | Extra cost | Saving |
| --- | ---: | ---: | ---: | ---: | ---: |
| Colorectal | 21.2 | 7.7 | 1 518 | 62 561 € | 283 080 € |
| Breast | 22.4 | 6.2 | 1 538 | 120 595 € | 49 413 € |
| Cervical | 19.8 | 6.1 | 2 098 | not calculated | not calculated |

## How to read this

- **The money comes back through colorectal screening.** Removing pre-stages of cancer prevents cancers altogether, and each prevented case saves its whole treatment. With central assumptions the education measure saves 1 191 221 € a year there against 235 519 € of extra screening and colonoscopies.
- **Breast screening does not pay for itself in euros.** The extra screening and the treatment of overdiagnosed cancers cost more (198 650 € a year) than is saved on metastatic treatment (96 933 €). Its case is fewer deaths, not lower spending.
- **Cervical screening is counted in people, not in euros.** No Finnish cost per case was found, so its extra costs and its savings are both missing from the totals.
- **The budgets are small against the stakes.** Both measures together cost 1 900 000 € over six years, which is 0.14 % of one year of cancer care.
- **Do not add the two measures together.** Some people belong to both groups, so the effects overlap.

## Which assumption matters most

Measure 1.1.1, net result over 2026-2031 when one value is changed and all others stay central (central result: 3 623 909 €).

| Value changed | Basis | At its pessimistic end | At its optimistic end |
| --- | --- | ---: | ---: |
| `gain_pp_colorectal` | published | 756 804 € | 9 358 119 € |
| `colorectal_adenoma_progression_10y` | published | 362 622 € | 5 798 100 € |
| `colorectal_direct_cost_share` | assumption | 1 974 526 € | 5 273 292 € |
| `cost_growth_per_case` | derived | 2 918 170 € | 4 666 218 € |
| `colorectal_metastatic_periods` | published | 3 110 807 € | 4 137 011 € |
| `gain_pp_breast` | published | 3 929 060 € | 3 013 608 € |
| `colorectal_stage4_share_unscreened` | published | 3 198 444 € | 4 087 193 € |
| `colorectal_fit_cost_per_participant` | assumption | 3 148 712 € | 3 940 707 € |
| `colorectal_colonoscopy_cost` | assumption | 3 127 012 € | 3 909 625 € |
| `breast_distant_recurrence_reduction` | published | 3 381 576 € | 4 157 041 € |
| `colorectal_stage4_reduction` | published | 3 346 241 € | 3 901 577 € |
| `breast_overdiagnosis_share` | published | 3 498 320 € | 3 875 086 € |
| `breast_screening_cost_per_attendee` | derived | 3 472 030 € | 3 761 980 € |
| `breast_metastatic_periods` | assumption | 3 507 589 € | 3 740 229 € |

## What this calculation can not show

- **Whether the measures reach the assumed gain.** The gains come from reviews of mostly US studies. Whether a budget of this size produces them across Finland is not known. The row "largest budget at which the measure still pays for itself" shows how much room there is.
- **Costs that are estimates.** The cost of a stool test and of a colonoscopy are rough estimates, because no Finnish unit cost was found. They are marked `assumption` in `assumptions.csv`.
- **Old cost studies.** Treatment costs per patient come from Finnish studies published in 2015 and 2019. New medicines have probably made advanced disease more expensive since, which would raise the savings.
- **Who is found by screening.** People who start taking part after a measure may differ from those who already take part. Findings per examination are taken from the group as it is today.
- **Savings arrive later than costs.** Screening is paid in the same year; the savings come three to five years later and are converted to today's money.
- **Health is not priced.** Longer life, working years and costs to families are left out.

## Sources of the numbers

| Value | Pessimistic | Central | Optimistic | Basis | Source |
| --- | ---: | ---: | ---: | --- | --- |
| `gain_pp_breast` | 3.1 | 6.2 | 12.4 | published | [link](https://thecommunityguide.org/findings/cancer-screening-multicomponent-interventions-breast-cancer) |
| `gain_pp_colorectal` | 3.85 | 7.7 | 15.4 | published | [link](https://thecommunityguide.org/findings/cancer-screening-multicomponent-interventions-colorectal-cancer) |
| `gain_pp_cervical` | 3.05 | 6.1 | 12.2 | published | [link](https://www.thecommunityguide.org/findings/cancer-screening-multicomponent-interventions-cervical-cancer) |
| `breast_screening_cost_per_attendee` | 64 | 53 | 43 | derived | [link](https://www.sttinfo.fi/tiedote/70982494/uusi-suositus-rintasyovan-seulonta-laajennettava-46-74-vuotiaisiin) |
| `breast_distant_recurrence_reduction` | 0.07 | 0.12 | 0.23 | published | [link](https://doi.org/10.1001/jama.292.9.1064) |
| `breast_overdiagnosis_share` | 0.23 | 0.19 | 0.11 | published | [link](https://doi.org/10.1038/bjc.2013.177) |
| `breast_cost_primary_6m` | 11798 | 11798 | 11798 | published | [link](https://pubmed.ncbi.nlm.nih.gov/30591480/) |
| `breast_cost_rehabilitation_6m` | 2398 | 2398 | 2398 | published | [link](https://pubmed.ncbi.nlm.nih.gov/30591480/) |
| `breast_cost_remission_6m` | 1147 | 1147 | 1147 | published | [link](https://pubmed.ncbi.nlm.nih.gov/30591480/) |
| `breast_cost_metastatic_6m` | 13923 | 13923 | 13923 | published | [link](https://pubmed.ncbi.nlm.nih.gov/30591480/) |
| `breast_metastatic_periods` | 4 | 5 | 6 | assumption | - |
| `colorectal_fit_cost_per_participant` | 40 | 25 | 15 | assumption | [link](https://www.sttinfo.fi/tiedote/70953769/helppo-kotitesti-saastaa-ihmishenkia) |
| `colorectal_colonoscopy_cost` | 900 | 500 | 270 | assumption | [link](https://kokoukset.heinola.fi/dynasty/kokous/20195283-7-1.PDF) |
| `colorectal_stage4_reduction` | 0.10 | 0.18 | 0.26 | published | [link](https://esmo.org/oncology-news/screen-detected-colorectal-cancers-have-a-more-favourable-stage-distribution-than-colorectal-cancers-detected-otherwise) |
| `colorectal_stage4_share_unscreened` | 0.225 | 0.27 | 0.319 | published | [link](https://esmo.org/oncology-news/screen-detected-colorectal-cancers-have-a-more-favourable-stage-distribution-than-colorectal-cancers-detected-otherwise) |
| `colorectal_cost_primary_6m` | 22200 | 22200 | 22200 | published | [link](https://pubmed.ncbi.nlm.nih.gov/25519708/) |
| `colorectal_cost_rehabilitation_6m` | 2106 | 2106 | 2106 | published | [link](https://pubmed.ncbi.nlm.nih.gov/25519708/) |
| `colorectal_cost_remission_6m` | 2812 | 2812 | 2812 | published | [link](https://pubmed.ncbi.nlm.nih.gov/25519708/) |
| `colorectal_cost_metastatic_6m` | 20540 | 20540 | 20540 | published | [link](https://pubmed.ncbi.nlm.nih.gov/25519708/) |
| `colorectal_cost_palliative_6m` | 21146 | 21146 | 21146 | published | [link](https://pubmed.ncbi.nlm.nih.gov/25519708/) |
| `colorectal_metastatic_periods` | 4 | 5 | 6 | published | [link](https://pubmed.ncbi.nlm.nih.gov/25519708/) |
| `colorectal_direct_cost_share` | 0.5 | 0.65 | 0.8 | assumption | [link](https://pubmed.ncbi.nlm.nih.gov/25519708/) |
| `colorectal_adenoma_progression_10y` | 0.15 | 0.30 | 0.40 | published | [link](https://pmc.ncbi.nlm.nih.gov/articles/PMC2095643) |
| `years_until_metastatic_cost_breast` | 5 | 5 | 5 | assumption | - |
| `years_until_stage4_cost_colorectal` | 3 | 3 | 3 | assumption | - |
| `years_until_prevented_cancer` | 5 | 5 | 5 | assumption | - |
| `discount_rate` | 0.03 | 0.03 | 0.03 | assumption | - |
| `cost_growth_per_case` | 0.0 | 0.02 | 0.047 | derived | [link](https://www.sttinfo.fi/tiedote/71176751/syovan-kustannuskasvu-hidastunut) |
| `programme_years` | 6 | 6 | 6 | published | - |
| `national_cancer_care_cost_2024` | 1400000000 | 1400000000 | 1400000000 | published | [link](https://www.sttinfo.fi/tiedote/71176751/syovan-kustannuskasvu-hidastunut) |
| `national_cancer_care_cost_2035` | 2600000000 | 2600000000 | 2600000000 | published | - |

Counts of invited people, participants and findings: Finnish Cancer Registry, screening statistics 2024, in `research/screening_yield_2024.csv`. Measure budgets: `pipeline/reference/measures.csv`.
