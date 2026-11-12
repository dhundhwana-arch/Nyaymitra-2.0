"""Download official PDFs safely and record provenance.

Rules:
* a download is written to a temporary ``.part`` file and only replaces the
  destination after it has been fully received and validated as a PDF;
* on any failure the existing destination file is left untouched and the exact
  error is recorded - success is never assumed.
"""
from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path

from .pdfio import ExtractionError, pdf_metadata
from .sources import ROOT, SOURCES, load_manifest, now_utc, save_manifest

USER_AGENT = "Mozilla/5.0 (NyayMitra source acquisition; +https://github.com/dhundhwana-arch/Nyaymitra-2.0)"


class AcquisitionError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _http_fetch(url: str, dest: Path, timeout: int = 120) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
        return {
            "http_status": resp.status,
            "final_url": resp.geturl(),
            "content_type": resp.headers.get("Content-Type"),
            "last_modified": resp.headers.get("Last-Modified"),
            "etag": resp.headers.get("ETag"),
        }


def download(url: str, dest: Path, fetch=_http_fetch) -> dict:
    """Fetch ``url`` to ``dest`` atomically. Raises AcquisitionError; never clobbers ``dest`` on failure."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        try:
            http = fetch(url, tmp)
        except Exception as exc:  # network / TLS / HTTP errors
            raise AcquisitionError(f"{type(exc).__name__}: {exc}") from exc
        with open(tmp, "rb") as f:
            if f.read(5) != b"%PDF-":
                raise AcquisitionError("downloaded content is not a PDF (missing %PDF- header)")
        try:
            meta = pdf_metadata(tmp)
        except ExtractionError as exc:
            raise AcquisitionError(f"downloaded PDF cannot be opened: {exc}") from exc
        os.replace(tmp, dest)
        return {"http": http, "pdf": meta}
    finally:
        if tmp.exists():
            tmp.unlink()


def acquire_all(manifest_path=None, root: Path = ROOT, fetch=_http_fetch, sources=SOURCES) -> dict:
    kwargs = {"path": manifest_path} if manifest_path else {}
    manifest = load_manifest(**kwargs)
    for sid, src in sources.items():
        dest = root / src["local_path"]
        entry = manifest["sources"].setdefault(sid, {})
        entry.update({k: src[k] for k in ("language", "publisher", "url", "local_path",
                                          "claimed_edition", "claimed_amendments_incorporated")})
        entry["claims_verified_against_document"] = entry.get("claims_verified_against_document", False)
        entry["last_attempt_at"] = now_utc()
        try:
            info = download(src["url"], dest, fetch=fetch)
        except AcquisitionError as exc:
            entry["last_attempt_status"] = "failed"
            entry["last_attempt_error"] = str(exc)
            entry["existing_file_preserved"] = dest.exists()
            entry.setdefault("acquired", False)
            for k in ("retrieved_at", "sha256", "size_bytes", "page_count", "pdf_metadata"):
                entry.setdefault(k, None)
            continue
        entry.update({
            "acquired": True,
            "last_attempt_status": "ok",
            "last_attempt_error": None,
            "retrieved_at": entry["last_attempt_at"],
            "sha256": sha256_file(dest),
            "size_bytes": dest.stat().st_size,
            "page_count": info["pdf"]["page_count"],
            "pdf_metadata": info["pdf"]["metadata"],
            "http": info["http"],
        })
    save_manifest(manifest, **kwargs)
    return manifest


def verify_checksums(manifest: dict, root: Path = ROOT) -> dict:
    """Compare files on disk with the manifest. Returns {source_id: {"ok": bool, "reason": str}}."""
    out = {}
    for sid, entry in manifest.get("sources", {}).items():
        path = root / entry["local_path"]
        if not entry.get("acquired") or not entry.get("sha256"):
            out[sid] = {"ok": False, "reason": "not acquired (no checksum in manifest)"}
        elif not path.exists():
            out[sid] = {"ok": False, "reason": f"file missing: {entry['local_path']}"}
        else:
            actual = sha256_file(path)
            ok = actual == entry["sha256"]
            out[sid] = {"ok": ok, "reason": "match" if ok else f"checksum mismatch: disk={actual} manifest={entry['sha256']}"}
    return out
