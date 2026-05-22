"""RandomForest model loader + predict + per-feature contributions.

Contributions use a perturbation method: for each feature, swap it for the
training-set baseline (median for numerics, mode for categoricals) and measure
how much the prediction moves. Intuitive, no extra deps, and the directions
match what users expect — e.g. raising `km_from_cbd` from 5 to 25 makes
contribution_aud negative.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.app.services.agents.schemas import FeatureContribution, ValuationResult
from src.app.services.duckdb_client import get_conn
from src.settings import settings

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _bundle() -> dict[str, Any]:
    path = Path(settings.model_path)
    if not path.exists():
        raise RuntimeError(
            f"Model not found at {path}. Run `python scripts/train_model.py` first."
        )
    return joblib.load(path)


@lru_cache(maxsize=1)
def _baselines() -> dict[str, Any]:
    """Compute training-set baselines for numerics (median) and categoricals (mode)."""
    bundle = _bundle()
    numeric = bundle["numeric_features"]
    categorical = bundle["categorical_features"]
    top_suburbs = bundle["top_suburbs"]

    with get_conn() as conn:
        df = conn.execute(
            """
            SELECT num_bed, num_bath, num_parking, property_size,
                   suburb_population, suburb_median_income, suburb_sqkm,
                   suburb_lat, suburb_lng, suburb_elevation,
                   cash_rate, property_inflation_index, km_from_cbd,
                   type, suburb
            FROM properties
            """
        ).df()

    df["suburb_grouped"] = df["suburb"].where(df["suburb"].isin(top_suburbs), other="Other")

    baseline: dict[str, Any] = {}
    for col in numeric:
        baseline[col] = float(df[col].median())
    for col in categorical:
        baseline[col] = str(df[col].mode().iloc[0])
    return baseline


@lru_cache(maxsize=1)
def _suburb_lookup() -> dict[str, dict[str, float]]:
    """Median suburb-level features keyed by lowercase suburb name."""
    with get_conn() as conn:
        df = conn.execute(
            """
            SELECT LOWER(suburb) AS key,
                   MEDIAN(suburb_population)        AS suburb_population,
                   MEDIAN(suburb_median_income)     AS suburb_median_income,
                   MEDIAN(suburb_sqkm)              AS suburb_sqkm,
                   MEDIAN(suburb_lat)               AS suburb_lat,
                   MEDIAN(suburb_lng)               AS suburb_lng,
                   MEDIAN(suburb_elevation)         AS suburb_elevation,
                   MEDIAN(km_from_cbd)              AS km_from_cbd,
                   ANY_VALUE(suburb)                AS canonical_suburb
            FROM properties
            GROUP BY LOWER(suburb)
            """
        ).df()
    out: dict[str, dict[str, float]] = {}
    for row in df.to_dict(orient="records"):
        key = row.pop("key")
        out[key] = row
    return out


# ---------------------------------------------------------------------------
# Enrich + predict
# ---------------------------------------------------------------------------

def enrich_features(features: dict[str, Any]) -> dict[str, Any]:
    """Fill in any missing model features using suburb median lookups + dataset baselines."""
    bundle = _bundle()
    top_suburbs = bundle["top_suburbs"]
    baselines = _baselines()
    feats = dict(features)

    suburb_raw = (feats.get("suburb") or "").strip()
    if suburb_raw:
        lookup = _suburb_lookup().get(suburb_raw.lower())
        if lookup:
            for key in ("suburb_population", "suburb_median_income", "suburb_sqkm",
                        "suburb_lat", "suburb_lng", "suburb_elevation", "km_from_cbd"):
                if feats.get(key) in (None, ""):
                    feats[key] = lookup[key]
            feats["suburb"] = lookup["canonical_suburb"]

    # Bucket the suburb for the model's one-hot
    canonical = feats.get("suburb") or ""
    feats["suburb_grouped"] = canonical if canonical in top_suburbs else "Other"

    # Fall back to baseline for anything still missing
    for feature, baseline in baselines.items():
        if feats.get(feature) in (None, ""):
            feats[feature] = baseline

    if not feats.get("type"):
        feats["type"] = baselines["type"]

    return feats


def _row(features: dict[str, Any]) -> pd.DataFrame:
    bundle = _bundle()
    cols = bundle["numeric_features"] + bundle["categorical_features"]
    return pd.DataFrame([{c: features.get(c) for c in cols}], columns=cols)


def _predict_aud(features: dict[str, Any]) -> float:
    pipeline = _bundle()["pipeline"]
    log_pred = float(pipeline.predict(_row(features))[0])
    return float(np.expm1(log_pred))


def _confidence_interval(features: dict[str, Any]) -> tuple[float, float]:
    """Use the spread of individual-tree predictions to bound the point estimate."""
    bundle = _bundle()
    pipeline = bundle["pipeline"]
    rf = pipeline.named_steps["rf"]
    X = pipeline.named_steps["preprocess"].transform(_row(features))
    tree_log_preds = np.array([tree.predict(X)[0] for tree in rf.estimators_])
    aud = np.expm1(tree_log_preds)
    lo, hi = np.quantile(aud, [0.1, 0.9])
    return float(lo), float(hi)


def predict_with_contributions(features: dict[str, Any]) -> ValuationResult:
    """Predict a price + per-feature contribution (in AUD)."""
    enriched = enrich_features(features)
    baselines = _baselines()
    bundle = _bundle()
    feature_order = bundle["numeric_features"] + ["type"]   # suburb handled separately

    predicted = _predict_aud(enriched)
    ci_lo, ci_hi = _confidence_interval(enriched)

    contributions: list[FeatureContribution] = []
    for feat in feature_order:
        if feat not in enriched:
            continue
        perturbed = dict(enriched)
        perturbed[feat] = baselines[feat]
        # When perturbing `type`, leave suburb_grouped as-is; vice versa.
        delta = predicted - _predict_aud(perturbed)
        if abs(delta) < 250:  # ignore tiny moves to keep the chart readable
            continue
        contributions.append(FeatureContribution(
            feature=feat,
            value=enriched.get(feat),
            contribution_aud=round(delta, 2),
        ))

    # Suburb contribution: compare against the "Other" bucket
    perturbed = dict(enriched)
    perturbed["suburb_grouped"] = "Other"
    delta_suburb = predicted - _predict_aud(perturbed)
    if abs(delta_suburb) >= 250:
        contributions.append(FeatureContribution(
            feature="suburb",
            value=enriched.get("suburb"),
            contribution_aud=round(delta_suburb, 2),
        ))

    contributions.sort(key=lambda c: abs(c.contribution_aud), reverse=True)

    return ValuationResult(
        predicted_price=round(predicted, 2),
        confidence_interval=(round(ci_lo, 2), round(ci_hi, 2)),
        contributions=contributions[:8],
        inputs_used={k: enriched.get(k) for k in feature_order + ["suburb", "suburb_grouped"]},
    )
