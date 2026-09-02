"""Download model.pkl + RAG parquets to ./data/ if missing.

Runs at backend container boot before uvicorn so each replica has the
model files it needs. No-op locally when files already exist (e.g. on a
dev laptop with `data/` populated from `train_model.py` etc).

Two sources, checked in order:

  ARTEFACT_BASE_URL    (Azure path) base URL of a public-read blob
                       container, e.g.
                       https://<account>.blob.core.windows.net/artefacts
                       Files are fetched with plain HTTPS -- no SDK, no
                       credentials, nothing to break at 2am. The
                       artefacts are derived from public Kaggle data,
                       so public-read is deliberate.

  S3_ARTEFACT_BUCKET   (legacy AWS path) bucket name; needs boto3 +
                       AWS credentials. Kept as reference.

Integrity: every artefact is verified against infra-azure/artefacts.sha256,
which ships inside the image (i.e. is pinned by the repo, not by the
blob). model.pkl is unpickled at runtime, so a tampered blob must never be
loaded - a mismatch deletes the file and aborts boot. Regenerate the
manifest with scripts/hash_artefacts.py after uploading new artefacts.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
MANIFEST_PATH = Path(os.getenv("ARTEFACT_MANIFEST", REPO_ROOT / "infra-azure" / "artefacts.sha256"))

# (object key under container/bucket, local destination path)
ARTEFACTS: list[tuple[str, Path]] = [
    ("model.pkl",                       DATA / "model.pkl"),
    ("metrics.json",                    DATA / "metrics.json"),
    ("feature_importance.json",         DATA / "feature_importance.json"),
    ("residuals.json",                  DATA / "residuals.json"),
    ("reviews_embeddings.parquet",      DATA / "reviews_embeddings.parquet"),
    ("regulations/embeddings.parquet",  DATA / "regulations" / "embeddings.parquet"),
]


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, str]:
    """Parse `<sha256>  <key>` lines. Missing manifest -> empty dict."""
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, key = line.partition("  ")
        if digest and key:
            out[key.strip()] = digest.lower()
    return out


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(key: str, dest: Path, manifest: dict[str, str]) -> None:
    """Raise if `dest` does not match the pinned digest for `key`.
    Fail closed: an artefact with no manifest entry is also rejected."""
    expected = manifest.get(key)
    if not expected:
        raise RuntimeError(f"no pinned checksum for {key} in {MANIFEST_PATH}")
    actual = sha256_of(dest)
    if actual != expected:
        dest.unlink(missing_ok=True)
        raise RuntimeError(
            f"checksum mismatch for {key}: expected {expected[:12]}..., got {actual[:12]}... (file removed)"
        )


def _download_https(base_url: str, manifest: dict[str, str]) -> None:
    import httpx  # already a backend dependency

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for key, dest in ARTEFACTS:
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                url = f"{base_url.rstrip('/')}/{key}"
                print(f"  downloading {url} -> {dest.relative_to(REPO_ROOT)}", flush=True)
                resp = client.get(url)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
            else:
                print(f"  already present: {dest.relative_to(REPO_ROOT)}")
            verify(key, dest, manifest)
            print(f"  verified {key}")


def _download_s3(bucket: str) -> None:
    import boto3  # legacy path only

    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-southeast-2"))
    for key, dest in ARTEFACTS:
        if dest.exists():
            print(f"  already present: {dest.relative_to(REPO_ROOT)}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"  downloading s3://{bucket}/{key} -> {dest.relative_to(REPO_ROOT)}", flush=True)
        s3.download_file(bucket, key, str(dest))


def main() -> int:
    base_url = os.getenv("ARTEFACT_BASE_URL", "").strip()
    bucket = os.getenv("S3_ARTEFACT_BUCKET", "").strip()
    if not base_url and not bucket:
        print("ARTEFACT_BASE_URL / S3_ARTEFACT_BUCKET not set -- skipping "
              "artefact download (local dev mode; data/ must already "
              "contain the files).")
        return 0

    DATA.mkdir(parents=True, exist_ok=True)
    started = time.time()
    if base_url:
        manifest = load_manifest()
        if not manifest:
            print(f"artefact manifest missing or empty: {MANIFEST_PATH}", file=sys.stderr)
            return 1
        _download_https(base_url, manifest)
    else:
        _download_s3(bucket)
    print(f"Artefacts ready ({time.time() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"download_artefacts failed: {exc}", file=sys.stderr)
        sys.exit(1)
