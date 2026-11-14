"""The owner-side inventory tool must be read-only and must flag duplicates / wrong scripts."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts" / "inventory_local_data.py"


def _run(tmp_path, *args):
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, str(TOOL), *args, "--out", str(out)],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def test_inventory_reports_csv_and_leaves_files_untouched(tmp_path):
    data = tmp_path / "d"
    data.mkdir()
    csv_file = data / "gujarati_master_index.csv"
    # Synthetic rows only: placeholder titles, not constitutional text.
    csv_file.write_text(
        "article_no,title\n1,placeholder\n2,placeholder\n2,placeholder\n4,ગુજરાતી\n",
        encoding="utf-8",
    )
    before = hashlib.sha256(csv_file.read_bytes()).hexdigest()
    report = _run(tmp_path, str(data))
    text = json.dumps(report, ensure_ascii=False)
    assert "gujarati_master_index.csv" in text
    assert before in text                       # checksum recorded
    assert '"2"' in text                        # duplicate article number surfaced
    assert hashlib.sha256(csv_file.read_bytes()).hexdigest() == before
    assert sorted(p.name for p in data.iterdir()) == ["gujarati_master_index.csv"]


def test_inventory_handles_missing_folder(tmp_path):
    report = _run(tmp_path, str(tmp_path / "does-not-exist"))
    assert "does-not-exist" in json.dumps(report)
