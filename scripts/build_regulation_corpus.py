"""Chunk + embed the regulation corpus into data/regulations/embeddings.parquet.

Uses Bedrock Titan v2 (1024-D) via boto3 -- same wrapper the runtime
Compliance retriever uses, so corpus and query embeddings stay aligned
on model + dimension.

Run from repo root after staging the docs:
    uv run python scripts/stage_regulation_corpus.py
    uv run python scripts/build_regulation_corpus.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "data" / "regulations" / "docs"
OUT_PATH = REPO_ROOT / "data" / "regulations" / "embeddings.parquet"

CHUNK_TARGET_CHARS = 1600   # roughly 400 tokens
CHUNK_OVERLAP_CHARS = 200

# Reuse the runtime Titan wrapper so corpus and query embeddings are
# guaranteed identical.
sys.path.insert(0, str(REPO_ROOT / "backend"))
from src.app.services import embed  # noqa: E402


def parse_doc(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    lines = text.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if not line.strip():
            body_start = i + 1
            break
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip().lower()] = val.strip()
    body = "\n".join(lines[body_start:]).strip()
    return meta, body


def chunk_text(text: str, target: int = CHUNK_TARGET_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    if len(text) <= target:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + target, len(text))
        if end < len(text):
            for boundary in ("\n\n", ". ", "; ", ", "):
                last = text.rfind(boundary, start + target // 2, end)
                if last != -1:
                    end = last + len(boundary)
                    break
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start, end - overlap)
    return [c for c in chunks if c]


def main() -> None:
    if not DOCS_DIR.exists():
        print(f"No docs at {DOCS_DIR}. Run scripts/stage_regulation_corpus.py first.",
              file=sys.stderr)
        sys.exit(1)

    records: list[dict[str, object]] = []
    files = sorted(DOCS_DIR.glob("*.md"))
    print(f"Found {len(files)} documents", flush=True)
    for path in files:
        meta, body = parse_doc(path)
        for i, chunk in enumerate(chunk_text(body)):
            records.append({
                "chunk_id": f"{path.stem}__{i:02d}",
                "filename": path.name,
                "source": meta.get("source", path.stem),
                "url": meta.get("url", ""),
                "section": meta.get("section", ""),
                "text": chunk,
            })

    print(f"Embedding {len(records)} chunks via Bedrock Titan v2", flush=True)
    embeddings: list[list[float]] = []
    started = time.time()
    for i, rec in enumerate(records):
        attempt = 0
        while True:
            try:
                vec = embed.embed_batch([rec["text"]])[0]
                embeddings.append(vec.tolist())
                break
            except Exception as exc:  # noqa: BLE001
                attempt += 1
                if attempt > 3:
                    raise
                wait = 2 ** attempt
                print(f"  chunk {i} failed ({exc}); retry {attempt} after {wait}s", flush=True)
                time.sleep(wait)
        if (i + 1) % 10 == 0 or i == len(records) - 1:
            elapsed = time.time() - started
            print(f"  embedded {i + 1}/{len(records)}  ({elapsed:.1f}s elapsed)", flush=True)

    for r, vec in zip(records, embeddings):
        r["embedding"] = vec

    df = pd.DataFrame(records)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(df):,} chunks ({len(embeddings[0])}-D) to {OUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"build_regulation_corpus failed: {exc}", file=sys.stderr)
        raise
