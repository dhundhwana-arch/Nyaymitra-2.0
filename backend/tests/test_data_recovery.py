"""Phase 4A: the owner-side recovery tool is read-only, private and its package is verifiable.

Everything here uses synthetic placeholder files in temporary folders and a temporary database.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts" / "inventory_local_data.py"
IMPORTER = ROOT / "scripts" / "import_constitution_data.py"
GU = "આ માત્ર પરીક્ષણ માટેનું નમૂનાનું ગુજરાતી વાક્ય છે અને તે કાયદાનું લખાણ નથી તે ધ્યાનમાં રાખશો."
EN = "This is only a sample English sentence written for testing and it is not the text of any law."


def snapshot(folder: Path) -> dict:
    """Everything that could reveal a modification: names, bytes, size, mtime, mode."""
    out = {}
    for path in sorted(folder.rglob("*")):
        stat = path.lstat()
        out[str(path.relative_to(folder))] = (
            stat.st_size, stat.st_mtime_ns, stat.st_mode,
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None)
    return out


@pytest.fixture()
def device(tmp_path):
    """A synthetic 'tablet': a project folder and a shared-storage folder with unrelated personal files."""
    project = tmp_path / "home" / "NYAYMITRA-AI"
    (project / "reports").mkdir(parents=True)
    (project / "ocr_output").mkdir()
    (project / "data" / "english_parsed").mkdir(parents=True)
    (project / "logs").mkdir()
    (project / "node_modules" / "x").mkdir(parents=True)
    (project / "reports" / "constitution_gujarati_master_index.csv").write_text(
        "article_no,page_start,page_end,title\n૧,૧૦,૧૦,નમૂનો\n૨,૧૧,૧૧,નમૂનો\n૨,૧૧,૧૨,નમૂનો\n૫,૧૪,૧૪,નમૂનો\n૨૧ક,૩૦,૩૦,નમૂનો\n",
        encoding="utf-8")
    (project / "ocr_output" / "page_010.txt").write_text(GU + "\n", encoding="utf-8")
    (project / "data" / "english_parsed" / "articles.json").write_text(
        json.dumps([{"article_no": "14", "part": "III", "text": EN}, {"article_no": "21A", "part": "III", "text": EN}]),
        encoding="utf-8")
    (project / "logs" / "ocr_run.log").write_text("page 10 done\npage 11 done\n", encoding="utf-8")
    (project / ".env").write_text("GROQ_API_KEY=" + "g" + "sk_abcdefghijklmnopqrstuvwxyz123456\n", encoding="utf-8")
    (project / "config_ocr.json").write_text('{"api_key": "' + "s" + 'k-abcdefghijklmnopqrstuvwxyz0123456789"}', encoding="utf-8")
    (project / "node_modules" / "x" / "index.json").write_text("{}", encoding="utf-8")
    conn = sqlite3.connect(project / "nyaymitra.db")
    conn.execute("CREATE TABLE complaints (id INTEGER, phone TEXT)")
    conn.execute("INSERT INTO complaints VALUES (1, '9999999999')")
    conn.commit()
    conn.close()
    shared = tmp_path / "storage" / "shared"
    (shared / "Download").mkdir(parents=True)
    (shared / "Documents").mkdir()
    (shared / "DCIM").mkdir()
    (shared / "Download" / "Gujarati_Constitution_2024.pdf").write_bytes(b"%PDF-1.4 synthetic placeholder, not a real PDF\n" * 50)
    (shared / "Download" / "bank_statement_index.csv").write_text("date,amount\n1,2\n", encoding="utf-8")
    (shared / "Documents" / "aadhaar_mapping.json").write_text('{"number": "private"}', encoding="utf-8")
    (shared / "Documents" / "gujarati_article_for_school.txt").write_text(GU, encoding="utf-8")
    (shared / "DCIM" / "constitution_photo_notes.txt").write_text("x", encoding="utf-8")
    return tmp_path, project, shared


def run_tool(*args, expect=0):
    proc = subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, timeout=120)
    assert proc.returncode == expect, proc.stdout + proc.stderr
    return proc


def test_inventory_json_and_markdown_and_originals_untouched(device):
    tmp, project, shared = device
    before = snapshot(tmp / "home"), snapshot(tmp / "storage")
    out, md = tmp / "out" / "inv.json", tmp / "out" / "inv.md"
    run_tool(project, "--search", shared, "--out", out, "--markdown", md)
    assert (snapshot(tmp / "home"), snapshot(tmp / "storage")) == before        # byte, size, mtime, mode identical; no new files
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["originals"]["unchanged"] is True and report["labels_are_guesses"] is True
    by_name = {Path(f["path"]).name: f for f in report["files"]}
    index = by_name["constitution_gujarati_master_index.csv"]
    assert index["sha256"] == hashlib.sha256(Path(index["path"]).read_bytes()).hexdigest()
    assert index["size_bytes"] == Path(index["path"]).stat().st_size and index["format"] == "csv"
    assert index["relative_path"] == "reports/constitution_gujarati_master_index.csv"
    assert index["language_guess"] == "gujarati" and index["kind_guess"] == "index_or_mapping"
    stats = index["article_columns"]["article_no"]
    assert stats["duplicates"] == ["2"] and stats["gaps_between_lowest_and_highest"][:2] == [3, 4]
    assert stats["gujarati_letter_suffixes"] == ["ક"]                           # reported as written, not turned into "A"
    assert "395" not in json.dumps(stats) and "470" not in json.dumps(stats)
    assert by_name["page_010.txt"]["derivation_guess"] == "ocr_derived"
    assert by_name["articles.json"]["language_guess"] == "english"
    assert by_name["articles.json"]["derivation_guess"] == "pdf_text_derived"
    assert by_name["ocr_run.log"]["kind_guess"] == "log"
    assert by_name["Gujarati_Constitution_2024.pdf"]["found_by"] == "search"
    assert by_name["nyaymitra.db"]["tables"]["complaints"]["rows"] == 1
    text = md.read_text(encoding="utf-8")
    assert "## Gujarati" in text and "## English" in text and "constitution_gujarati_master_index.csv" in text
    assert "નમૂનો" not in text and GU not in json.dumps(report, ensure_ascii=False)   # the inventory carries facts, not the text


def test_unrelated_personal_files_are_never_named(device):
    tmp, project, shared = device
    out = tmp / "inv.json"
    run_tool(project, "--search", shared, "--out", out, "--markdown", tmp / "inv.md")
    everything = out.read_text(encoding="utf-8") + (tmp / "inv.md").read_text(encoding="utf-8")
    for private in ("bank_statement", "aadhaar", "for_school", "photo_notes", "node_modules"):
        assert private not in everything
    assert json.loads(out.read_text(encoding="utf-8"))["not_listed"]["data_files_not_listed_no_matching_name"] >= 3
    # shared storage passed as a plain folder is still treated as a broad search
    run_tool(shared, "--out", tmp / "inv2.json")
    second = json.loads((tmp / "inv2.json").read_text(encoding="utf-8"))
    assert [Path(f["path"]).name for f in second["files"]] == ["Gujarati_Constitution_2024.pdf"]
    assert second["search_roots"] == [str(shared)]


def test_secrets_are_flagged_without_content_and_never_packaged(device):
    tmp, project, shared = device
    package = tmp / "nyaymitra-transfer"
    run_tool(project, "--search", shared, "--package", package, "--out", tmp / "inv.json")
    report = json.loads((tmp / "inv.json").read_text(encoding="utf-8"))
    flagged = {Path(f["path"]).name: f for f in report["files"] if f.get("possible_secret")}
    assert "config_ocr.json" in flagged and "record_keys" not in flagged["config_ocr.json"]
    packaged = [p.name for p in package.rglob("*") if p.is_file()]
    assert "config_ocr.json" not in packaged and ".env" not in packaged and "nyaymitra.db" not in packaged
    blob = b"".join(p.read_bytes() for p in package.rglob("*") if p.is_file())
    with tarfile.open(str(package) + ".tar.gz") as tar:
        names = tar.getnames()
        blob += b"".join(tar.extractfile(m).read() for m in tar.getmembers() if m.isfile())
    assert b"sk_abcdefgh" not in blob and b"k-abcdefgh" not in blob and b"9999999999" not in blob
    assert not any("config_ocr" in n or n.endswith(".db") or n.endswith(".env") for n in names)
    reasons = {Path(x["path"]).name: x["reason"] for x in report["package"]["not_packaged"]}
    assert reasons["nyaymitra.db"].startswith("database") and reasons["config_ocr.json"].startswith("possible secret")


def test_package_layout_manifest_and_verification(device):
    tmp, project, shared = device
    before = snapshot(tmp / "home"), snapshot(tmp / "storage")
    package = tmp / "nyaymitra-transfer"
    proc = run_tool(project, "--search", shared, "--package", package)
    assert (snapshot(tmp / "home"), snapshot(tmp / "storage")) == before        # copied, not moved; originals identical
    assert (package / "gujarati" / "NYAYMITRA-AI" / "reports" / "constitution_gujarati_master_index.csv").is_file()
    assert (package / "gujarati" / "NYAYMITRA-AI" / "ocr_output" / "page_010.txt").read_text(encoding="utf-8") == GU + "\n"
    assert (package / "english" / "NYAYMITRA-AI" / "data" / "english_parsed" / "articles.json").is_file()
    assert (package / "gujarati" / "shared" / "Download" / "Gujarati_Constitution_2024.pdf").is_file()
    for name in ("MANIFEST.sha256", "inventory.json", "INVENTORY.md", "SOURCE_INFO.md"):
        assert (package / name).is_file()
    report = json.loads((package / "inventory.json").read_text(encoding="utf-8"))
    assert report["package"]["copies_verified"] and report["originals"]["method"].endswith("SHA-256")
    for line in (package / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((package / name).read_bytes()).hexdigest() == digest
    archive = Path(str(package) + ".tar.gz")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest in proc.stdout and digest in Path(str(archive) + ".sha256").read_text()
    run_tool("--verify-package", package)
    # receiver side: unpack elsewhere and verify; then detect tampering
    received = tmp / "received"
    with tarfile.open(archive) as tar:
        tar.extractall(received)
    run_tool("--verify-package", received / "nyaymitra-transfer")
    victim = received / "nyaymitra-transfer" / "gujarati" / "NYAYMITRA-AI" / "ocr_output" / "page_010.txt"
    victim.write_text("changed", encoding="utf-8")
    assert "MISMATCH" in run_tool("--verify-package", received / "nyaymitra-transfer", expect=1).stdout
    # a second run neither overwrites the package nor inventories it
    assert run_tool(project, "--package", package, expect=1).returncode == 1
    run_tool(tmp / "home", "--all", "--out", tmp / "again.json")
    assert "nyaymitra-transfer" not in (tmp / "again.json").read_text(encoding="utf-8")


def test_large_files_are_listed_with_checksum_but_not_copied(device):
    tmp, project, shared = device
    package = tmp / "pkg"
    run_tool(project, "--search", shared, "--package", package, "--max-file-mb", "0.001", "--out", tmp / "inv.json")
    report = json.loads((tmp / "inv.json").read_text(encoding="utf-8"))
    skipped = {Path(x["path"]).name: x for x in report["package"]["not_packaged"]}
    pdf = skipped["Gujarati_Constitution_2024.pdf"]
    assert "larger than" in pdf["reason"] and len(pdf["sha256"]) == 64
    assert not list(package.rglob("*.pdf"))


def test_package_inside_project_folder_is_refused(device):
    tmp, project, _ = device
    before = snapshot(project)
    proc = subprocess.run([sys.executable, str(TOOL), str(project), "--package", str(project / "transfer")],
                          capture_output=True, text=True)
    assert proc.returncode == 2 and snapshot(project) == before


def test_readonly_sqlite_leaves_no_side_files(device):
    tmp, project, _ = device
    run_tool(project, "--out", tmp / "inv.json")
    assert sorted(p.name for p in project.iterdir() if p.name.startswith("nyaymitra.db")) == ["nyaymitra.db"]


def test_read_only_files_and_folders_work(device):
    tmp, project, _ = device
    target = project / "reports" / "constitution_gujarati_master_index.csv"
    os.chmod(target, 0o444)
    os.chmod(project / "reports", 0o555)
    try:
        run_tool(project, "--out", tmp / "inv.json")
        assert json.loads((tmp / "inv.json").read_text(encoding="utf-8"))["originals"]["unchanged"]
    finally:
        os.chmod(project / "reports", 0o755)


# ----------------------------------------------------------------------------- importer on recovered-style files
def importer(tmp_path, *args):
    env = {"PATH": "/usr/bin:/bin", "NYAYMITRA_DB_PATH": str(tmp_path / "isolated.db"),
           "NYAYMITRA_BACKUP_DIR": str(tmp_path / "bk"), "NYAYMITRA_ENV": "development"}
    return subprocess.run([sys.executable, str(IMPORTER), *map(str, args)], capture_output=True, text=True, env=env, cwd=ROOT)


@pytest.fixture()
def isolated_db(tmp_path):
    env = {"PATH": "/usr/bin:/bin", "NYAYMITRA_DB_PATH": str(tmp_path / "isolated.db")}
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "init_db.py")], capture_output=True, text=True, env=env, cwd=ROOT)
    assert proc.returncode == 0, proc.stderr
    return tmp_path / "isolated.db"


def db_digest(path: Path) -> str:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = []
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            rows.append((name, conn.execute(f'SELECT * FROM "{name}" ORDER BY 1').fetchall()))
        return hashlib.sha256(repr(rows).encode()).hexdigest()
    finally:
        conn.close()


def test_index_without_text_stops_with_mapping_report(device, tmp_path, isolated_db):
    _, project, _ = device
    index = project / "reports" / "constitution_gujarati_master_index.csv"
    before = hashlib.sha256(index.read_bytes()).hexdigest(), db_digest(isolated_db)
    out = importer(tmp_path, "inspect", index, "--language", "gu")
    assert out.returncode == 4 and "MAPPING REQUIRED" in out.stderr and "text" in out.stdout
    out = importer(tmp_path, "check", index, "--language", "gu", "--source-key", "india-code-constitution", "--extraction-method", "ocr")
    assert out.returncode == 4 and "nothing was imported" in out.stderr
    assert (hashlib.sha256(index.read_bytes()).hexdigest(), db_digest(isolated_db)) == before


def test_check_is_a_true_dry_run_and_reports_accurately(tmp_path, isolated_db):
    data = tmp_path / "gujarati_articles.csv"
    rows = [("૧", GU + " એક"), ("૨", GU + " બે"), ("૨", GU + " બે"), ("૫", GU + " પાંચ"), ("૨૧ક", GU + " ક"), ("૭", "")]
    data.write_text("અનુચ્છેદ,લખાણ,verification_status\n" + "".join(f'{n},"{t}",verified\n' for n, t in rows), encoding="utf-8")
    file_before, db_before = hashlib.sha256(data.read_bytes()).hexdigest(), db_digest(isolated_db)
    report_path = tmp_path / "r.json"
    out = importer(tmp_path, "check", data, "--language", "gu", "--source-key", "india-code-constitution",
                   "--extraction-method", "ocr", "--report", report_path)
    assert "DRY RUN" in out.stdout, out.stdout + out.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["totals"]["records_discovered"] == 6 and report["totals"]["import_ready"] == 3
    assert report["rejections"]["by_reason"] == {"duplicate_identical": 1, "invalid_article_number": 1, "empty_text": 1}
    assert report["numbering"]["gaps_in_sequence"] == ["3", "4"] and report["numbering"]["duplicate_article_numbers"] == ["2"]
    assert report["content_status_on_import"] == "OCR_REVIEW_REQUIRED"
    assert report["verification_status_on_import"] == "requires_human_verification"
    assert report["claimed_verified_ignored"] == 3
    assert out.returncode == 3 and "more_than_20_percent_rejected" in report["blocking_reasons"]
    assert hashlib.sha256(data.read_bytes()).hexdigest() == file_before          # source file untouched
    assert db_digest(isolated_db) == db_before                                   # database untouched
    assert not (tmp_path / "bk").exists()                                        # a dry run does not even take a backup


def test_gujarati_text_survives_byte_for_byte(tmp_path):
    from backend.app.services import structured_import as si

    tricky = "ક્ષત્રિય શ્રી જ્ઞાન ર્‍ય ક્‌ષ અં અઃ ૧૨૩ — “અવતરણ” ‘એક’ ।" + " " + GU
    data = tmp_path / "g.json"
    data.write_text(json.dumps([{"article_no": "૧", "text": tricky}], ensure_ascii=False), encoding="utf-8")
    loaded = si.read_records(data)
    records, _ = si.build_records(loaded, si.infer_mapping(loaded, "gu"), "gu", "ocr", normalize=True)
    assert records[0].text == tricky and records[0].text.encode("utf-8") == tricky.encode("utf-8")
    assert records[0].article_no == "1"


# ----------------------------------------------------------------------------- final readiness audit (tool 2.1)
def test_personal_data_and_archives_are_listed_but_never_packaged(device):
    tmp, project, shared = device
    (project / "exports").mkdir()
    (project / "exports" / "complaints_export.csv").write_text("id,name,phone\n1,Private Person,9876543210\n", encoding="utf-8")
    (project / "data" / "users.json").write_text('[{"name": "Private Person"}]', encoding="utf-8")
    (project / "data" / "constitution_backup.zip").write_bytes(b"PK-not-a-real-zip Private Person")
    package = tmp / "pkg"
    proc = run_tool(project, "--search", shared, "--package", package, "--out", tmp / "inv.json")
    report = json.loads((tmp / "inv.json").read_text(encoding="utf-8"))
    reasons = {Path(x["path"]).name: x["reason"] for x in report["package"]["not_packaged"]}
    assert reasons["complaints_export.csv"].startswith("possible personal data")
    assert reasons["users.json"].startswith("possible personal data")
    assert reasons["constitution_backup.zip"].startswith("archive")
    entry = next(f for f in report["files"] if f["path"].endswith("complaints_export.csv"))
    assert "columns" not in entry and "rows" not in entry and len(entry["sha256"]) == 64
    names = [p.name for p in package.rglob("*") if p.is_file()]
    assert not {"complaints_export.csv", "users.json", "constitution_backup.zip"} & set(names)
    with tarfile.open(str(package) + ".tar.gz") as tar:
        blob = b"".join(tar.extractfile(m).read() for m in tar.getmembers() if m.isfile())
    assert b"Private Person" not in blob and b"9876543210" not in blob
    # every omission is named on the console and in the readable report, not only counted
    for name in ("complaints_export.csv", "users.json", "constitution_backup.zip", "nyaymitra.db"):
        assert f"NOT COPIED: {project}" in proc.stdout and name in proc.stdout
        assert name in (package / "INVENTORY.md").read_text(encoding="utf-8")


def test_large_file_omission_is_printed(device):
    tmp, project, shared = device
    proc = run_tool(project, "--search", shared, "--package", tmp / "pkg", "--max-file-mb", "0.001")
    line = next(l for l in proc.stdout.splitlines() if "Gujarati_Constitution_2024.pdf" in l)
    assert line.strip().startswith("NOT COPIED") and "larger than 0.001 MB" in line
    assert "Gujarati_Constitution_2024.pdf" in (tmp / "pkg" / "INVENTORY.md").read_text(encoding="utf-8")


def test_source_info_can_be_edited_without_breaking_verification(device):
    tmp, project, shared = device
    package = tmp / "nyaymitra-transfer"
    run_tool(project, "--search", shared, "--package", package)
    manifest = (package / "MANIFEST.sha256").read_text(encoding="utf-8")
    assert "SOURCE_INFO.md" not in manifest
    copied = [p for p in package.rglob("*") if p.is_file() and p.parts[len(package.parts)] in ("gujarati", "english", "unclassified")]
    assert copied and all(p.relative_to(package).as_posix() in manifest for p in copied)   # every data file is in the manifest
    with (package / "SOURCE_INFO.md").open("a", encoding="utf-8") as handle:
        handle.write("- Edition: answered by the owner\n")
    assert "not checksummed" in run_tool("--verify-package", package).stdout             # exit 0 after the edit
    # the guide's re-archive step, then the receiver's checks
    subprocess.run(["tar", "-czf", "nyaymitra-transfer.tar.gz", "nyaymitra-transfer"], cwd=tmp, check=True)
    received = tmp / "received"
    with tarfile.open(tmp / "nyaymitra-transfer.tar.gz") as tar:
        tar.extractall(received)
    run_tool("--verify-package", received / "nyaymitra-transfer")
    assert "answered by the owner" in (received / "nyaymitra-transfer" / "SOURCE_INFO.md").read_text(encoding="utf-8")
    # an added or removed data file is still caught
    (received / "nyaymitra-transfer" / "gujarati" / "extra.txt").write_text("x", encoding="utf-8")
    assert "NOT IN MANIFEST" in run_tool("--verify-package", received / "nyaymitra-transfer", expect=1).stdout
    (received / "nyaymitra-transfer" / "gujarati" / "extra.txt").unlink()
    (received / "nyaymitra-transfer" / "gujarati" / "NYAYMITRA-AI" / "ocr_output" / "page_010.txt").unlink()
    assert "MISMATCH" in run_tool("--verify-package", received / "nyaymitra-transfer", expect=1).stdout


def test_existing_archive_is_never_overwritten(device):
    tmp, project, _ = device
    archive = tmp / "pkg.tar.gz"
    archive.write_bytes(b"an earlier archive")
    proc = subprocess.run([sys.executable, str(TOOL), str(project), "--package", str(tmp / "pkg")], capture_output=True, text=True)
    assert proc.returncode != 0 and "will not be overwritten" in proc.stderr
    assert archive.read_bytes() == b"an earlier archive" and not (tmp / "pkg").exists()


def test_verification_does_not_modify_package_or_originals(device):
    tmp, project, shared = device
    package = tmp / "pkg"
    run_tool(project, "--search", shared, "--package", package)
    before = snapshot(tmp / "home"), snapshot(tmp / "storage"), snapshot(package)
    run_tool("--verify-package", package)
    assert (snapshot(tmp / "home"), snapshot(tmp / "storage"), snapshot(package)) == before


def test_file_changed_during_packaging_fails_loudly(device, monkeypatch):
    import importlib.util

    tmp, project, _ = device
    spec = importlib.util.spec_from_file_location("inventory_tool", TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    real_copy = tool.shutil.copyfile

    def corrupting_copy(src, dst):
        real_copy(src, dst)
        if str(src).endswith("page_010.txt"):
            Path(dst).write_text("damaged in transit", encoding="utf-8")

    monkeypatch.setattr(tool.shutil, "copyfile", corrupting_copy)
    code = tool.main([str(project), "--package", str(tmp / "pkg"), "--out", str(tmp / "inv.json")])
    report = json.loads((tmp / "inv.json").read_text(encoding="utf-8"))
    assert code == 1 and report["package"]["copies_verified"] is False
    assert report["originals"]["unchanged"] is True
