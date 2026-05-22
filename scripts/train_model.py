"""Train the property-price RandomForest model.

Adapts the Kaggle notebook (prediction-of-nsw-house-pricing.ipynb): drops the
top 1% of prices, log-transforms the target, one-hot encodes type and a
top-N-suburb feature, and dumps the fitted pipeline plus metrics.

Run from repo root:
    uv run python scripts/train_model.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

REPO_ROOT = Path(__file__).resolve().parent.parent
MISC = REPO_ROOT / "misc"
DATA = REPO_ROOT / "data"

NUMERIC_FEATURES = [
    "num_bed", "num_bath", "num_parking", "property_size",
    "suburb_population", "suburb_median_income", "suburb_sqkm",
    "suburb_lat", "suburb_lng", "suburb_elevation",
    "cash_rate", "property_inflation_index", "km_from_cbd",
]
CATEGORICAL_FEATURES = ["type", "suburb_grouped"]
TARGET = "price"

TOP_N_SUBURBS = 60   # keep top-N by count; collapse the rest to "Other"
OUTLIER_QUANTILE = 0.99


def load() -> pd.DataFrame:
    df = pd.read_csv(MISC / "domain_properties.csv")
    df = df.dropna(subset=["price", "suburb"])
    df["date_sold"] = pd.to_datetime(df["date_sold"], format="%d/%m/%y", errors="coerce")
    return df.reset_index(drop=True)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    print("Loading dataset", flush=True)
    df = load()
    print(f"  {len(df):,} rows", flush=True)

    upper = df[TARGET].quantile(OUTLIER_QUANTILE)
    df = df[df[TARGET] <= upper].reset_index(drop=True)
    print(f"  {len(df):,} rows after dropping top 1% prices (>${upper:,.0f})", flush=True)

    top_suburbs = df["suburb"].value_counts().nlargest(TOP_N_SUBURBS).index.tolist()
    df["suburb_grouped"] = df["suburb"].where(df["suburb"].isin(top_suburbs), other="Other")

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = np.log1p(df[TARGET])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    preprocess = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ])

    model = Pipeline([
        ("preprocess", preprocess),
        ("rf", RandomForestRegressor(
            n_estimators=200,
            max_depth=None,
            min_samples_split=4,
            n_jobs=-1,
            random_state=42,
        )),
    ])

    print("Training RandomForest (200 estimators)", flush=True)
    model.fit(X_train, y_train)

    y_pred_log = model.predict(X_test)
    y_pred = np.expm1(y_pred_log)
    y_true = np.expm1(y_test)

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))

    metrics = {
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "mae_aud": round(mae, 2),
        "rmse_aud": round(rmse, 2),
        "r2": round(r2, 4),
        "target": "log1p(price)",
        "outlier_quantile_dropped": OUTLIER_QUANTILE,
        "top_n_suburbs": TOP_N_SUBURBS,
    }
    print(f"  MAE ${mae:,.0f} | RMSE ${rmse:,.0f} | R² {r2:.3f}", flush=True)

    rf = model.named_steps["rf"]
    feat_names = (
        NUMERIC_FEATURES
        + list(model.named_steps["preprocess"].named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES))
    )
    importances = [
        {"feature": str(name), "importance": float(score)}
        for name, score in sorted(zip(feat_names, rf.feature_importances_), key=lambda kv: -kv[1])
    ]
    top_importances = importances[:25]

    residuals = (y_true - y_pred).round(2).tolist()
    residual_sample = pd.DataFrame({
        "actual": y_true.round(0).tolist(),
        "predicted": y_pred.round(0).tolist(),
        "residual": residuals,
    }).sample(n=min(500, len(y_true)), random_state=42).to_dict(orient="records")

    joblib.dump({
        "pipeline": model,
        "top_suburbs": top_suburbs,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
    }, DATA / "model.pkl")
    (DATA / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (DATA / "feature_importance.json").write_text(json.dumps(top_importances, indent=2))
    (DATA / "residuals.json").write_text(json.dumps(residual_sample, indent=2))

    print(f"Wrote model.pkl + metrics/feature_importance/residuals JSON to {DATA}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"train_model failed: {exc}", file=sys.stderr)
        raise
