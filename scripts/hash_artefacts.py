"""Write infra-azure/artefacts.sha256 from the artefacts in ./data/.

The backend verifies every artefact it downloads at boot against this
manifest (see download_artefacts.py). The manifest ships inside the
backend image, so it is only as trustworthy as the repo - which is the
point: a tampered blob cannot be unpickled unless the attacker can also
land a commit.

Run after retraining / rebuilding the corpus and uploading to the blob:

    uv run python scripts/hash_artefacts.py
    git add infra-azure/artefacts.sha256
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_artefacts import ARTEFACTS, MANIFEST_PATH, REPO_ROOT  # noqa: E402


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    lines = []
    for key, dest in ARTEFACTS:
        if not dest.exists():
            print(f"missing: {dest.relative_to(REPO_ROOT)} - build it first", file=sys.stderr)
            return 1
        digest = sha256_of(dest)
        lines.append(f"{digest}  {key}")
        print(f"  {digest[:12]}...  {key}")
    MANIFEST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
