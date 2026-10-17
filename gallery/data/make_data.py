"""Synthetic gallery data with the character of the reference figures (no patient data)."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np

SEED = 20260717
FOLDER = Path(__file__).resolve().parent
MAX_OCCUPANCY = 1.15  # overflow beds: real ICU occupancy rarely passes about 110 %
WARDS = [("Unit A", 0.60, 20), ("Unit B", 0.86, 14), ("Unit C", 0.69, 10), ("Unit D", 0.79, 16),
         ("Unit E", 0.79, 8), ("Unit F", 0.68, 12)]
DAYS = 546
INTERIM = (120, 485)


def occupancy_rows(rng: np.random.Generator) -> list[dict]:
    rows = []
    for ward, level, beds in WARDS:
        drift, values = 0.0, []
        for day in range(DAYS):
            drift = 0.9 * drift + rng.normal(0, 0.035)
            weekly = 0.04 * math.sin(day / 7 * 2 * math.pi)
            values.append(min(MAX_OCCUPANCY, max(0.15, level + drift + weekly + rng.normal(0, 0.06))))
        smooth = np.convolve(values, np.ones(7) / 7, mode="full")[:DAYS]
        smooth[:6] = [np.mean(values[: index + 1]) for index in range(6)]
        interim = ward in ("Unit B", "Unit D")
        for day in range(DAYS):
            rows.append({"ward": ward, "day": day, "share": round(values[day], 5), "mean7": round(smooth[day], 5),
                         "beds": beds - 2 if interim and INTERIM[0] <= day <= INTERIM[1] else beds})
    return rows


def scatter_rows(rng: np.random.Generator) -> list[dict]:
    rows = []
    for group, offset in (("Low risk", 0.0), ("Medium risk", 0.8), ("High risk", 1.6)):
        for _ in range(48):
            sofa = rng.uniform(2, 14)
            rows.append({"group": group, "sofa": round(sofa, 3),
                         "lactate": round(max(0.4, 0.6 + offset + 0.25 * sofa + rng.normal(0, 0.7)), 3)})
    return rows


DISCHARGE = [("Home", "Alone", 250), ("Home", "With support", 162), ("Rehabilitation", "Inpatient", 120),
             ("Rehabilitation", "Outpatient", 48), ("Other ward", "Other ward", 97), ("Care home", "Care home", 54),
             ("Died", "Died", 23)]


def discharge_rows() -> list[dict]:
    return [{"route": route, "detail": detail, "patients": patients} for route, detail, patients in DISCHARGE]


def trial_rows(rng: np.random.Generator) -> list[dict]:
    """Two arms, exponential survival with censoring; follow-up capped at 60 months."""
    rows = []
    for arm, scale in (("Standard care", 11.0), ("Early mobilisation", 18.0)):
        for _ in range(90):
            death, censor = rng.exponential(scale), rng.uniform(6, 80)
            months = min(death, censor, 60.0)
            rows.append({"arm": arm, "months": round(max(months, 0.1), 1), "died": int(death <= min(censor, 60.0))})
    return rows


META = [("Adams 2019", 0.62, 0.41, 0.94, 31.0, "34 / 120"), ("Baker 2020", 0.81, 0.55, 1.19, 27.0, "29 / 98"),
        ("Chen 2021", 0.47, 0.25, 0.88, 12.0, "11 / 45"), ("Diaz 2022", 1.05, 0.70, 1.58, 22.0, "37 / 110"),
        ("Evans 2023", 0.69, 0.38, 1.25, 8.0, "9 / 52")]


def meta_rows() -> list[dict]:
    return [{"study": study, "or": estimate, "low": low, "high": high, "weight": weight, "events": events}
            for study, estimate, low, high, weight, events in META]


def stay_rows(rng: np.random.Generator) -> list[dict]:
    """Length of ICU stay in days: right-skewed, longer on the neurological unit."""
    rows = []
    for unit, shape, scale, count in (("Surgical", 2.2, 2.0, 64), ("Medical", 3.0, 2.2, 58), ("Neuro", 4.0, 2.5, 41)):
        rows += [{"unit": unit, "days": round(float(value), 1)} for value in rng.gamma(shape, scale, count)]
    return rows


BUDGET = [("Salary", "Joint account", "Rent", 1200), ("Salary", "Joint account", "Groceries", 420),
          ("Salary", "Joint account", "Leisure", 260), ("Salary", "Savings", "Reserve", 400),
          ("Salary", "Joint account", "Transport", 180), ("Child benefit", "Joint account", "Groceries", 160),
          ("Child benefit", "Savings", "Reserve", 90), ("Side job", "Joint account", "Leisure", 140),
          ("Side job", "Joint account", "Transport", 60), ("Side job", "Savings", "Reserve", 50)]


def budget_rows() -> list[dict]:
    return [{"income": income, "account": account, "spending": spending, "euros": euros}
            for income, account, spending, euros in BUDGET]


DIAGNOSES = ["Sepsis", "Pneumonia", "Trauma", "Stroke", "Cardiac arrest", "Pancreatitis"]


def admission_rows(rng: np.random.Generator) -> list[dict]:
    diagnoses = rng.choice(DIAGNOSES, 420, p=[0.28, 0.24, 0.18, 0.14, 0.1, 0.06])
    sexes = rng.choice(["Female", "Male"], 420)
    return [{"diagnosis": str(name), "sex": str(sex)} for name, sex in zip(diagnoses, sexes, strict=True)]


UNIT_RATES = [("Medical", 132, 1010), ("Surgical", 74, 880), ("Neurological", 61, 410), ("Cardiac", 38, 520),
              ("Burns", 9, 64), ("Paediatric", 6, 230)]


def rate_rows() -> list[dict]:
    rows = []
    for unit, deaths, patients in UNIT_RATES:
        share = deaths / patients
        spread = 1.96 * math.sqrt(share * (1 - share) / patients)
        rows.append({"unit": unit, "mortality": round(share, 4), "low": round(max(share - spread, 0), 4),
                     "high": round(share + spread, 4)})
    return rows


def patient_rows(rng: np.random.Generator) -> list[dict]:
    """Admission measurements with the usual links: lactate and creatinine rise with SOFA, stays lengthen."""
    sofa = rng.uniform(2, 14, 160)
    rows = []
    for score in sofa:
        rows.append({"sofa": round(float(score), 1), "lactate": round(float(0.6 + 0.3 * score + rng.normal(0, 0.8)), 2),
                     "creatinine": round(float(0.7 + 0.08 * score + rng.normal(0, 0.25)), 2),
                     "age": int(rng.normal(64, 12)),
                     "length_of_stay": round(float(2 + 0.5 * score + rng.gamma(2, 1.5)), 1)})
    return rows


def funnel_rows(rng: np.random.Generator) -> list[dict]:
    """Fourteen trials around an odds ratio of 0.75; small trials lean towards benefit (a small-study effect)."""
    rows = []
    for index in range(14):
        se = float(rng.uniform(0.08, 0.5))
        effect = math.log(0.75) - 0.6 * (se - 0.25) + float(rng.normal(0, se * 0.8))
        rows.append({"study": f"Trial {index + 1}", "odds_ratio": round(math.exp(effect), 3), "se": round(se, 3)})
    return rows


BIAS = {"Randomisation": "LLLSLHLLSLLL", "Deviations": "LSSLLHLSLLLL", "Missing data": "LLHLLLSLLLSL",
        "Measurement": "LLLLSLLLHLLL", "Reporting": "SLLLLLLSLLLL"}


def bias_rows() -> list[dict]:
    words = {"L": "Low", "S": "Some concerns", "H": "High"}
    return [{"study": f"Trial {index + 1}", **{domain: words[marks[index]] for domain, marks in BIAS.items()}}
            for index in range(12)]


def write(name: str, rows: list[dict]) -> None:
    with (FOLDER / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = np.random.default_rng(SEED)
    write("occupancy.csv", occupancy_rows(rng))
    write("scatter.csv", scatter_rows(rng))
    write("discharge.csv", discharge_rows())
    write("trial.csv", trial_rows(rng))
    write("meta.csv", meta_rows())
    write("stays.csv", stay_rows(rng))
    write("budget.csv", budget_rows())
    write("admissions.csv", admission_rows(rng))
    write("rates.csv", rate_rows())
    write("patients.csv", patient_rows(rng))
    write("funnel.csv", funnel_rows(rng))
    write("bias.csv", bias_rows())


if __name__ == "__main__":
    main()
