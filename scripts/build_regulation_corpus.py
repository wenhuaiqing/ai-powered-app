"""Chunk + embed the regulation corpus into data/regulations/embeddings.parquet.

Run from repo root after staging the docs:
    uv run python scripts/stage_regulation_corpus.py
    uv run python scripts/build_regulation_corpus.py

Requires AZURE_OPENAI_API_KEY (uses text-embedding-3-small by default).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "data" / "regulations" / "docs"
OUT_PATH = REPO_ROOT / "data" / "regulations" / "embeddings.parquet"

# Tiny envless settings loader — script runs without the FastAPI app context.
import os
from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
EMBED_MODEL = os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-small")

CHUNK_TARGET_CHARS = 1600   # roughly 400 tokens
CHUNK_OVERLAP_CHARS = 200


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
            # Try to break on a paragraph or sentence boundary nearby
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


def embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def main() -> None:
    if not AZURE_ENDPOINT or not AZURE_API_KEY:
        print("AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY not set — cannot build embeddings.",
              file=sys.stderr)
        sys.exit(1)
    if not DOCS_DIR.exists():
        print(f"No docs at {DOCS_DIR}. Run scripts/stage_regulation_corpus.py first.",
              file=sys.stderr)
        sys.exit(1)

    client = OpenAI(base_url=AZURE_ENDPOINT, api_key=AZURE_API_KEY)

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

    print(f"Embedding {len(records)} chunks via {EMBED_MODEL}", flush=True)
    BATCH = 32
    embeddings: list[list[float]] = []
    for i in range(0, len(records), BATCH):
        batch = [r["text"] for r in records[i:i + BATCH]]
        attempt = 0
        while True:
            try:
                embeddings.extend(embed_batch(client, batch))
                break
            except Exception as exc:  # noqa: BLE001
                attempt += 1
                if attempt > 3:
                    raise
                wait = 2 ** attempt
                print(f"  batch {i//BATCH} failed ({exc}); retry {attempt} after {wait}s", flush=True)
                time.sleep(wait)
        print(f"  embedded {i + len(batch)}/{len(records)}", flush=True)

    for r, vec in zip(records, embeddings):
        r["embedding"] = vec

    df = pd.DataFrame(records)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(df):,} chunks to {OUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"build_regulation_corpus failed: {exc}", file=sys.stderr)
        raise
