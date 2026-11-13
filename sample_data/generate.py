"""Generate SYNTHETIC sample data for the Equal Care prototype.

Nothing in the output is a real statistic. Region names are the real Finnish
wellbeing services counties (plus Helsinki), but every number is invented so
that the pipeline can be built before real open data is wired in.

Run:  python3 sample_data/generate.py
"""
import csv
import math
import random
from pathlib import Path

OUT = Path(__file__).parent
SEED = 2026

# name, population (thousands, rough), rurality 0..1, share of foreign-language speakers
REGIONS = [
    ("Helsinki", 670, 0.00, 0.18),
    ("Vantaa ja Kerava", 290, 0.05, 0.24),
    ("Länsi-Uusimaa", 490, 0.10, 0.15),
    ("Keski-Uusimaa", 205, 0.15, 0.08),
    ("Itä-Uusimaa", 100, 0.25, 0.07),
    ("Varsinais-Suomi", 490, 0.25, 0.09),
    ("Satakunta", 210, 0.45, 0.04),
    ("Kanta-Häme", 170, 0.35, 0.05),
    ("Pirkanmaa", 540, 0.25, 0.06),
    ("Päijät-Häme", 205, 0.35, 0.06),
    ("Kymenlaakso", 160, 0.45, 0.06),
    ("Etelä-Karjala", 125, 0.50, 0.06),
    ("Etelä-Savo", 130, 0.70, 0.03),
    ("Pohjois-Savo", 248, 0.55, 0.03),
    ("Pohjois-Karjala", 162, 0.70, 0.03),
    ("Keski-Suomi", 273, 0.50, 0.04),
    ("Etelä-Pohjanmaa", 190, 0.60, 0.03),
    ("Pohjanmaa", 177, 0.45, 0.08),
    ("Keski-Pohjanmaa", 68, 0.60, 0.03),
    ("Pohjois-Pohjanmaa", 418, 0.55, 0.03),
    ("Kainuu", 70, 0.85, 0.03),
    ("Lappi", 176, 0.95, 0.03),
]

# cancer: (cases per 1000 inhabitants, national-ish early-stage share,
#          screening base participation or None, base days per stage,
#          placeholder target for diagnosis -> treatment start)
CANCERS = {
    "breast":     dict(rate=0.90, early=0.80, screen=0.82, ref=7,  dx=10, tx=13, target=21),
    "colorectal": dict(rate=0.70, early=0.48, screen=0.74, ref=21, dx=20, tx=17, target=28),
    "lung":       dict(rate=0.50, early=0.27, screen=None, ref=18, dx=22, tx=13, target=21),
    "prostate":   dict(rate=0.95, early=0.72, screen=None, ref=25, dx=28, tx=25, target=42),
}
EDUCATION = ["low", "middle", "high"]


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def share_within(target, median, sigma=0.5):
    """Share of patients below `target` days if waits are lognormal around `median`."""
    z = (math.log(target) - math.log(median)) / sigma
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def write(name, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def main():
    rnd = random.Random(SEED)
    regions, pathway, ses = [], [], []

    for name, pop_k, rural, foreign in REGIONS:
        low_edu = clamp(0.20 + 0.14 * rural + rnd.gauss(0, 0.025), 0.12, 0.40)
        occ_cov = clamp(0.52 - 0.6 * (low_edu - 0.27) + rnd.gauss(0, 0.03), 0.25, 0.65)
        pc_strain = clamp(0.25 + 0.40 * rural + rnd.gauss(0, 0.20))
        dx_strain = clamp(0.30 + 0.20 * rural + rnd.gauss(0, 0.22))
        tx_strain = clamp(0.30 + rnd.gauss(0, 0.22))
        vacancy = clamp(0.04 + 0.12 * rural + rnd.gauss(0, 0.04), 0.0, 0.30)
        dist_rt = round(8 + 230 * rural ** 1.5 + abs(rnd.gauss(0, 8)))
        route_ratio = round(1.2 + 1.1 * pc_strain + rnd.gauss(0, 0.1), 2)

        regions.append(dict(
            region=name,
            population=pop_k * 1000,
            share_low_education=round(low_edu, 3),
            share_foreign_language=round(foreign + rnd.gauss(0, 0.005), 3),
            occupational_health_coverage=round(occ_cov, 3),
            primary_care_wait_days=round(5 + 20 * pc_strain, 1),
            public_vs_occupational_dx_time_ratio=route_ratio,
            specialist_vacancy_rate=round(vacancy, 3),
            median_distance_to_radiotherapy_km=dist_rt,
        ))

        for cancer, c in CANCERS.items():
            cases = round(pop_k * c["rate"] * (1 + 0.3 * rural))
            screen = None
            if c["screen"] is not None:
                screen = clamp(c["screen"] - 0.35 * foreign - 0.25 * (low_edu - 0.27)
                               + rnd.gauss(0, 0.02))
            early = clamp(c["early"] - 0.08 * rural - 0.30 * (low_edu - 0.27)
                          - 0.06 * (pc_strain - 0.45) + rnd.gauss(0, 0.02))
            d_ref = c["ref"] * (0.70 + 0.90 * pc_strain) * (1 + rnd.gauss(0, 0.05))
            d_dx = c["dx"] * (0.75 + 0.70 * dx_strain) * (1 + rnd.gauss(0, 0.05))
            d_tx = c["tx"] * (0.80 + 0.50 * tx_strain + 0.15 * rural) * (1 + rnd.gauss(0, 0.05))
            within = share_within(c["target"], d_tx)

            # Fragmented data is part of the challenge: some stage timings are not reported.
            ref_missing = rnd.random() < 0.12
            dx_missing = rnd.random() < 0.08

            pathway.append(dict(
                region=name,
                cancer=cancer,
                new_cases_per_year=cases,
                screening_participation="" if screen is None else round(screen, 3),
                share_stage_I_II=round(early, 3),
                days_first_contact_to_referral="" if ref_missing else round(d_ref, 1),
                days_referral_to_diagnosis="" if dx_missing else round(d_dx, 1),
                days_diagnosis_to_treatment=round(d_tx, 1),
                share_treated_within_target=round(within, 3),
            ))

            # Education gradient: wider where occupational health covers fewer people.
            spread = 0.04 + 0.10 * (0.55 - occ_cov) + abs(rnd.gauss(0, 0.01))
            for level, sign in zip(EDUCATION, (-1, 0, 1)):
                ses.append(dict(
                    region=name,
                    cancer=cancer,
                    education=level,
                    screening_participation="" if screen is None
                    else round(clamp(screen + sign * spread * 1.2), 3),
                    share_stage_I_II=round(clamp(early + sign * spread), 3),
                ))

    write("synthetic_regions.csv", regions)
    write("synthetic_pathway.csv", pathway)
    write("synthetic_ses_gradient.csv", ses)


if __name__ == "__main__":
    main()
