"""Upload local ML artefacts to the S3 bucket Terraform provisioned.

Run from the laptop after a `train_model.py` or `build_*_embeddings.py`
rebuild. Needs AWS creds on PATH (`aws configure`).

Pass the bucket name on the CLI or set S3_ARTEFACT_BUCKET in env:
    uv run python scripts/upload_artefacts_to_s3.py \
        --bucket "$(terraform -chdir=infra output -raw s3_artefacts_bucket)"
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"

ARTEFACTS: list[tuple[Path, str]] = [
    (DATA / "model.pkl",                       "model.pkl"),
    (DATA / "metrics.json",                    "metrics.json"),
    (DATA / "feature_importance.json",         "feature_importance.json"),
    (DATA / "residuals.json",                  "residuals.json"),
    (DATA / "reviews_embeddings.parquet",      "reviews_embeddings.parquet"),
    (DATA / "regulations" / "embeddings.parquet", "regulations/embeddings.parquet"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", default=os.getenv("S3_ARTEFACT_BUCKET", ""))
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "ap-southeast-2"))
    args = parser.parse_args()

    bucket = args.bucket.strip()
    if not bucket:
        print("Bucket not specified. Pass --bucket or set S3_ARTEFACT_BUCKET.",
              file=sys.stderr)
        return 2

    import boto3
    s3 = boto3.client("s3", region_name=args.region)

    started = time.time()
    uploaded = 0
    for src, key in ARTEFACTS:
        if not src.exists():
            print(f"  skip (missing): {src.relative_to(REPO_ROOT)}", file=sys.stderr)
            continue
        size_mb = src.stat().st_size / (1024 * 1024)
        print(f"  -> s3://{bucket}/{key}  ({size_mb:.1f} MB)", flush=True)
        s3.upload_file(str(src), bucket, key)
        uploaded += 1

    print(f"Uploaded {uploaded} artefact(s) in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"upload_artefacts_to_s3 failed: {exc}", file=sys.stderr)
        sys.exit(1)
