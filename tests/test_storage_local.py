"""storage_local（ローカルファイル保存）のテスト。

tmp_path と monkeypatch で保存先を一時ディレクトリに差し替え、
本物の data/ を汚さずに save/load/update のラウンドトリップを検証する。
"""

from __future__ import annotations

import pytest

from surgery_app import config, storage_local


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    """storage_local の保存先定数を一時ディレクトリへ差し替える。"""
    data_dir = tmp_path / "data"
    cases_dir = data_dir / "cases"
    index_file = data_dir / "cases_index.json"
    monkeypatch.setattr(storage_local, "DATA_DIR", data_dir)
    monkeypatch.setattr(storage_local, "CASES_DIR", cases_dir)
    monkeypatch.setattr(storage_local, "INDEX_FILE", index_file)
    return data_dir


def _record(case_id: str = "case-001", outcome: str = "生存") -> dict:
    return {
        "case_id": case_id,
        "saved_at": f"2026-06-18T12:00:0{case_id[-1]}",
        "condition": "結腸捻転（大結腸）",
        "decision": "温存",
        "outcome": outcome,
        "notes": "初回メモ",
        "labs": {"ht": 45.0},
        "color": {},
    }


def test_save_and_load_roundtrip(temp_storage):
    """save_case で保存した内容が load_case で読み戻せる。"""
    case_id = storage_local.save_case(_record("case-001"))
    assert case_id == "case-001"

    loaded = storage_local.load_case("case-001")
    assert loaded is not None
    assert loaded["condition"] == "結腸捻転（大結腸）"
    assert loaded["outcome"] == "生存"
    assert loaded["labs"]["ht"] == 45.0


def test_load_index_count(temp_storage):
    """保存した症例数だけインデックスに載る。"""
    storage_local.save_case(_record("case-001"))
    storage_local.save_case(_record("case-002"))

    index = storage_local.load_index()
    assert len(index) == 2
    assert {c["case_id"] for c in index} == {"case-001", "case-002"}


def test_update_outcome_changes_outcome_and_appends_note(temp_storage):
    """update_outcome で転帰が変わり、メモが追記される。"""
    storage_local.save_case(_record("case-001", outcome="生存"))

    ok = storage_local.update_outcome("case-001", "死亡", extra_note="術後に悪化")
    assert ok is True

    loaded = storage_local.load_case("case-001")
    assert loaded["outcome"] == "死亡"
    assert "初回メモ" in loaded["notes"]
    assert "術後に悪化" in loaded["notes"]


def test_update_outcome_missing_returns_false(temp_storage):
    """存在しない症例IDなら False。"""
    assert storage_local.update_outcome("missing", "死亡") is False


def test_cases_dataframe_columns(temp_storage):
    """cases_dataframe の列が config.columns() と一致する。"""
    storage_local.save_case(_record("case-001"))
    df = storage_local.cases_dataframe()
    assert list(df.columns) == config.columns()
    assert len(df) == 1
