"""Tests for scripts/count_project_loc.py (first-party LOC helper)."""

import importlib.util
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_count_project_loc():
    path = _REPO_ROOT / "scripts" / "count_project_loc.py"
    spec = importlib.util.spec_from_file_location("count_project_loc", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cpl = _load_count_project_loc()


class TestShouldCountFile:
    def test_skips_csv_under_api_data(self):
        root = _REPO_ROOT
        p = root / "api" / "data" / "ireland25.csv"
        assert cpl.should_count_file(root, p) is False

    def test_counts_blender_python(self):
        root = _REPO_ROOT
        p = root / "Blender" / "Hotine" / "trig_pillar.py"
        if p.is_file():
            assert cpl.should_count_file(root, p) is True

    def test_skips_package_lock(self):
        root = _REPO_ROOT
        p = root / "web" / "package-lock.json"
        if p.is_file():
            assert cpl.should_count_file(root, p) is False

    def test_skips_yaml_in_web_public(self):
        root = _REPO_ROOT
        p = root / "web" / "public" / "news.yaml"
        if p.is_file():
            assert cpl.should_count_file(root, p) is False


class TestIterCodeFiles:
    def test_prunes_node_modules_and_counts_src(self, tmp_path: Path):
        (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
        (tmp_path / "node_modules" / "pkg" / "a.ts").write_text("x\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "b.ts").write_text("line1\nline2\n")

        files = cpl.iter_code_files(tmp_path)
        rels = {f.relative_to(tmp_path).as_posix() for f in files}
        assert "src/b.ts" in rels
        assert not any("node_modules" in f.parts for f in files)

    def test_skips_api_data_tree(self, tmp_path: Path):
        (tmp_path / "api" / "data").mkdir(parents=True)
        (tmp_path / "api" / "data" / "d.csv").write_text("a,b\n")
        (tmp_path / "api" / "svc.py").write_text("print(1)\n")

        files = cpl.iter_code_files(tmp_path)
        rels = {f.relative_to(tmp_path).as_posix() for f in files}
        assert "api/svc.py" in rels
        assert "api/data/d.csv" not in rels


@pytest.mark.skipif(
    not (_REPO_ROOT / "api" / "main.py").is_file(),
    reason="repo root not available",
)
def test_main_script_exits_zero():
    import subprocess
    import sys

    r = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "scripts" / "count_project_loc.py"),
            str(_REPO_ROOT),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "Total lines:" in r.stdout
