"""Write-token gate, public feed labels, MySQL TLS args, artefact checksums."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.app.services import auth
from src.app.services.agents.runs import public_label
from src.app.services.mysql_client import mysql_connect_args
from src.settings import settings

REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------- write token

def _app() -> FastAPI:
    app = FastAPI()

    @app.post("/write", dependencies=[Depends(auth.require_write_token)])
    async def write() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_write_refused_when_no_token_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "demo_write_token", "")
    client = TestClient(_app())
    assert client.post("/write").status_code == 403
    assert client.post("/write", headers={"X-Write-Token": "anything"}).status_code == 403


def test_write_requires_matching_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "demo_write_token", "s3cret")
    client = TestClient(_app())
    assert client.post("/write").status_code == 401
    assert client.post("/write", headers={"X-Write-Token": "wrong"}).status_code == 401
    assert client.post("/write", headers={"X-Write-Token": "s3cret"}).status_code == 200


def test_has_write_token_false_when_unconfigured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "demo_write_token", "")

    class _Req:
        headers = {"x-write-token": ""}

    assert auth.has_write_token(_Req()) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------- feed labels

def test_public_label_never_contains_prompt_text():
    assert public_label(["compliance"], "dashboard") == "Compliance check"
    assert public_label(["compliance", "matcher"], "properties", None, "L0055") == (
        "Compliance check + Property match from Properties (L0055)"
    )
    assert public_label([], "pipeline", "LD001") == "Orb run from Pipeline (LD001)"


# ---------------------------------------------------------------- mysql tls

def test_mysql_connect_args_follow_setting(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "mysql_ssl", False)
    assert mysql_connect_args() == {}
    monkeypatch.setattr(settings, "mysql_ssl", True)
    assert mysql_connect_args() == {"ssl_verify_cert": True, "ssl_verify_identity": True}


# ---------------------------------------------------------------- artefact checksums

def _load_download_module():
    path = REPO_ROOT / "scripts" / "download_artefacts.py"
    spec = importlib.util.spec_from_file_location("download_artefacts", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["download_artefacts"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_manifest_verification(tmp_path: Path):
    mod = _load_download_module()
    good = tmp_path / "model.pkl"
    good.write_bytes(b"trusted bytes")
    digest = hashlib.sha256(b"trusted bytes").hexdigest()
    manifest_file = tmp_path / "artefacts.sha256"
    manifest_file.write_text(f"{digest}  model.pkl\n# comment\n", encoding="utf-8")

    manifest = mod.load_manifest(manifest_file)
    assert manifest == {"model.pkl": digest}
    mod.verify("model.pkl", good, manifest)  # no raise

    bad = tmp_path / "tampered.pkl"
    bad.write_bytes(b"evil bytes")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        mod.verify("model.pkl", bad, manifest)
    assert not bad.exists(), "tampered artefact must be removed"

    with pytest.raises(RuntimeError, match="no pinned checksum"):
        mod.verify("unknown.parquet", good, manifest)


def test_committed_manifest_covers_every_artefact():
    mod = _load_download_module()
    manifest = mod.load_manifest(REPO_ROOT / "infra-azure" / "artefacts.sha256")
    keys = {key for key, _ in mod.ARTEFACTS}
    assert keys <= set(manifest), f"manifest missing: {keys - set(manifest)}"
    assert all(len(d) == 64 for d in manifest.values())
