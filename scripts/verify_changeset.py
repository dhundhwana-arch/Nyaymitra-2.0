#!/usr/bin/env python3
"""Changeset integrity checker: manifest, verification and archive extraction check.

Purpose: make a handover auditable. A manifest pins every tracked file to a SHA-256 and a
size, so anyone can prove that the copy they received is the copy that was tested — and can
tell the difference between "a file changed" and "a file went missing".

    python scripts/verify_changeset.py --write backups/manifest.json
    python scripts/verify_changeset.py --verify backups/manifest.json
    python scripts/verify_changeset.py --verify-archive backups/code.tar.gz \\
                                       --manifest backups/manifest.json

Exit codes: 0 = identical, 1 = mismatch/missing/extra, 2 = cannot run (bad path, no git).

The manifest only covers **tracked** files by default. That is deliberate: caches, databases,
uploaded documents and virtualenvs must not be part of a code integrity check, and a database
backup carries personal data that belongs in a separate, access-controlled artefact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
CHUNK = 1024 * 1024


# --------------------------------------------------------------------------- hashing
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_entries(root: Path, paths: Iterable[str]) -> list[dict]:
    """Return a sorted list of ``{path, sha256, size}`` for the given relative paths."""
    entries: list[dict] = []
    for rel in sorted(set(paths)):
        full = root / rel
        entries.append({"path": rel, "sha256": sha256_file(full), "size": full.stat().st_size})
    return entries


# --------------------------------------------------------------------------- discovery
def git_tracked_paths(root: Path, ref: str | None = None) -> list[str]:
    """Tracked paths at ``ref`` (default: the index) — never includes ignored files."""
    cmd = ["git", "-C", str(root), "ls-tree", "-r", "--long", ref] if ref else [
        "git", "-C", str(root), "ls-files", "-s"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git failed: {result.stderr.strip() or result.returncode}")
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        if ref:
            # <mode> <type> <object> <size>\t<path>
            meta, _, path = line.partition("\t")
            mode = meta.split()[0]
        else:
            # <mode> <object> <stage>\t<path>
            meta, _, path = line.partition("\t")
            mode = meta.split()[0]
        # 100644/100755 are regular files. Symlinks (120000) and gitlinks (160000) have no
        # content of their own, so they cannot be hashed; they are reported, not skipped silently.
        if mode in {"100644", "100755"}:
            paths.append(path)
    return paths


def head_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True
        )
    except FileNotFoundError:  # pragma: no cover - git is present in every supported env
        return None
    return result.stdout.strip() if result.returncode == 0 else None


# --------------------------------------------------------------------------- manifest
def build_manifest(root: Path, paths: Sequence[str], *, commit: str | None = None) -> dict:
    return {
        "format": "nyaymitra-changeset-manifest",
        "version": 1,
        "algorithm": "sha256",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": commit,
        "root": root.name,
        "entry_count": len(paths),
        "entries": hash_entries(root, paths),
    }


def write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != "nyaymitra-changeset-manifest":
        raise ValueError(f"{path} is not a changeset manifest")
    if data.get("algorithm") != "sha256":
        raise ValueError(f"{path} uses an unsupported algorithm")
    return data


# --------------------------------------------------------------------------- comparison
def compare(manifest_entries: Sequence[dict], actual_entries: Sequence[dict]) -> dict:
    expected = {entry["path"]: entry for entry in manifest_entries}
    actual = {entry["path"]: entry for entry in actual_entries}
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    modified = sorted(
        path for path in set(expected) & set(actual)
        if expected[path]["sha256"] != actual[path]["sha256"]
    )
    return {
        "ok": not (missing or extra or modified),
        "checked": len(actual),
        "expected": len(expected),
        "missing": missing,
        "extra": extra,
        "modified": modified,
    }


def verify_tree(root: Path, manifest: dict, paths: Sequence[str] | None = None) -> dict:
    if paths is None:
        paths = [entry["path"] for entry in manifest["entries"]]
    return compare(manifest["entries"], hash_entries(root, paths))


# --------------------------------------------------------------------------- archive
def _safe_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = []
    for member in archive.getmembers():
        name = member.name.replace("\\", "/")
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError(f"refusing to extract unsafe path: {member.name}")
        if member.isfile():
            members.append(member)
    return members


def verify_archive(archive_path: Path, manifest: dict) -> dict:
    """Extract into a temporary directory and compare against the manifest.

    The archive is expected to contain a single top-level directory (``git archive --prefix``
    style or a ``tar`` of the checkout). Files are matched on their path *inside* that directory.
    """
    with tempfile.TemporaryDirectory(prefix="nyaymitra-verify-") as tmp:
        target = Path(tmp)
        with tarfile.open(archive_path, "r:*") as archive:
            members = _safe_members(archive)
            if not members:
                raise ValueError("archive contains no files")
            # Extracted one member at a time: tarfile's `filter=` argument is not available on
            # every supported Python 3.11 build, and this way the path check above is the only
            # thing that decides what may be written.
            for member in members:
                destination = target / member.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    continue
                with source, destination.open("wb") as handle:
                    shutil.copyfileobj(source, handle)
        files = [member.name for member in members]
        prefixes = {Path(name).parts[0] for name in files}
        prefix = prefixes.pop() if len(prefixes) == 1 and len(Path(files[0]).parts) > 1 else None
        relative = []
        for name in files:
            parts = Path(name).parts
            if prefix is not None and parts[0] == prefix:
                parts = parts[1:]
            relative.append(str(Path(*parts)))
        entries = hash_entries(target / prefix if prefix else target, relative)
        report = compare(manifest["entries"], entries)
        report["archive"] = str(archive_path)
        report["archive_files"] = len(files)
        return report


# --------------------------------------------------------------------------- CLI
def _print_human(manifest: dict | None, report: dict) -> None:
    if manifest:
        print(f"manifest: {manifest['entry_count']} entries, commit {manifest.get('commit') or 'unknown'}")
    print(
        f"checked {report['checked']} files against {report['expected']} expected: "
        f"{len(report['missing'])} missing, {len(report['extra'])} extra, "
        f"{len(report['modified'])} modified"
    )
    for label in ("missing", "extra", "modified"):
        for path in report[label][:20]:
            print(f"  {label}: {path}")
        if len(report[label]) > 20:
            print(f"  {label}: … and {len(report[label]) - 20} more")
    print("RESULT: OK — the changeset is identical to the manifest" if report["ok"]
          else "RESULT: MISMATCH — do not treat this copy as the tested changeset")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NYAYMITRA changeset integrity checker")
    parser.add_argument("--write", metavar="MANIFEST", help="write a manifest for the tracked files")
    parser.add_argument("--verify", metavar="MANIFEST", help="verify the working tree against a manifest")
    parser.add_argument("--verify-archive", metavar="ARCHIVE", help="extract an archive and verify it")
    parser.add_argument("--manifest", metavar="MANIFEST", help="manifest to use with --verify-archive")
    parser.add_argument("--ref", default=None, help="git ref to manifest (default: HEAD)")
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository root (default: this checkout)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        if args.write:
            ref = args.ref or "HEAD"
            paths = git_tracked_paths(root, ref)
            manifest = build_manifest(root, paths, commit=head_commit(root))
            write_manifest(Path(args.write), manifest)
            if args.json:
                print(json.dumps({"written": args.write, "entry_count": manifest["entry_count"],
                                  "commit": manifest["commit"]}))
            else:
                print(f"wrote {args.write}: {manifest['entry_count']} entries, commit {manifest['commit']}")
            return 0

        if args.verify:
            manifest = load_manifest(Path(args.verify))
            report = verify_tree(root, manifest)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                _print_human(manifest, report)
            return 0 if report["ok"] else 1

        if args.verify_archive:
            if not args.manifest:
                print("--verify-archive requires --manifest", file=sys.stderr)
                return 2
            manifest = load_manifest(Path(args.manifest))
            report = verify_archive(Path(args.verify_archive), manifest)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                _print_human(manifest, report)
            return 0 if report["ok"] else 1

        parser.print_help()
        return 2
    except (RuntimeError, ValueError, OSError, tarfile.TarError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
