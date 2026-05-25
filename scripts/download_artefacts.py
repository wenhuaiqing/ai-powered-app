"""Download model.pkl + RAG parquets from S3 to ./data/ if missing.

Runs at backend container boot before uvicorn so each Fargate task has
the model files it needs. No-op locally when files already exist (e.g.
on a dev laptop with `data/` populated from `train_model.py` etc).

Environment:
  S3_ARTEFACT_BUCKET   bucket name (set by ECS task def env from
                       `terraform output -raw s3_artefacts_bucket`)
  AWS_REGION           region for the S3 client
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"

# (object key under bucket, local destination path)
ARTEFACTS: list[tuple[str, Path]] = [
    ("model.pkl",                       DATA / "model.pkl"),
    ("metrics.json",                    DATA / "metrics.json"),
    ("feature_importance.json",         DATA / "feature_importance.json"),
    ("residuals.json",                  DATA / "residuals.json"),
    ("reviews_embeddings.parquet",      DATA / "reviews_embeddings.parquet"),
    ("regulations/embeddings.parquet",  DATA / "regulations" / "embeddings.parquet"),
]


def main() -> int:
    bucket = os.getenv("S3_ARTEFACT_BUCKET", "").strip()
    if not bucket:
        print("S3_ARTEFACT_BUCKET not set -- skipping artefact download "
              "(local dev mode; data/ must already contain the files).")
        return 0

    # Lazy import so this script is cheap when bucket is unset.
    import boto3
    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-southeast-2"))

    DATA.mkdir(parents=True, exist_ok=True)
    started = time.time()
    for key, dest in ARTEFACTS:
        if dest.exists():
            print(f"  already present: {dest.relative_to(REPO_ROOT)}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"  downloading s3://{bucket}/{key} -> {dest.relative_to(REPO_ROOT)}", flush=True)
        s3.download_file(bucket, key, str(dest))

    print(f"Artefacts ready ({time.time() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"download_artefacts failed: {exc}", file=sys.stderr)
        sys.exit(1)
