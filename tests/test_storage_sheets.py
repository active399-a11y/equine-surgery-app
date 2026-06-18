"""storage_sheets（Googleスプレッドシート保存）のテスト。

本物のGoogle接続は使わず、_conn を in-memory の DataFrame を保持する Fake に
差し替えて、読み書きのロジックだけを検証する。
"""

from __future__ import annotations

import pandas as pd
import pytest

# storage_sheets はモジュール先頭で streamlit_gsheets を import するため、
# 未導入環境ではこのテストファイルごとスキップする。
pytest.importorskip("streamlit_gsheets")

from surgery_app import config, storage_sheets  # noqa: E402


class FakeConn:
    """st.connection("gsheets") の代わり。1枚のDataFrameを保持する。"""

    def __init__(self) -> None:
        # 最初は空（列だけ定義どおり）
        self.df = pd.DataFrame(columns=config.columns())

    def read(self, worksheet=None, ttl=None):
        # 実シートを模して、保持中のDataFrameのコピーを返す。
        # 空でも config.columns() を列に持つ表を返す（_read_df の前提）。
        if self.df.empty:
            return pd.DataFrame(columns=config.columns())
        return self.df.copy()

    def update(self, worksheet=None, data=None):
        self.df = data.copy().reset_index(drop=True)


@pytest.fixture
def fake_conn(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(storage_sheets, "_conn", lambda: conn)
    return conn


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


def test_read_df_empty_returns_columns(fake_conn):
    """空シートでも config.columns() の空表が返る。"""
    df = storage_sheets._read_df()
    assert list(df.columns) == config.columns()
    assert len(df) == 0


def test_save_case_adds_one_row(fake_conn):
    """save_case でシートに1行追加される。"""
    case_id = storage_sheets.save_case(_record("case-001"))
    assert case_id == "case-001"

    df = storage_sheets._read_df()
    assert len(df) == 1
    assert df.iloc[0]["症例ID"] == "case-001"


def test_load_index_maps_japanese_to_internal_keys(fake_conn):
    """load_index が日本語列を内部キーへ正しく写像する。"""
    storage_sheets.save_case(_record("case-001", outcome="生存"))

    index = storage_sheets.load_index()
    assert len(index) == 1
    entry = index[0]
    assert entry["case_id"] == "case-001"
    assert entry["condition"] == "結腸捻転（大結腸）"
    assert entry["decision"] == "温存"
    assert entry["outcome"] == "生存"
    # 内部キーになっていること（日本語キーは無い）
    assert "症例ID" not in entry


def test_update_outcome_updates_row(fake_conn):
    """update_outcome で転帰が更新され、メモが追記される。"""
    storage_sheets.save_case(_record("case-001", outcome="生存"))

    ok = storage_sheets.update_outcome("case-001", "死亡", extra_note="術後に悪化")
    assert ok is True

    case = storage_sheets.load_case("case-001")
    assert case["outcome"] == "死亡"
    assert "術後に悪化" in str(case["notes"])


def test_update_outcome_missing_returns_false(fake_conn):
    """存在しない症例IDなら False。"""
    assert storage_sheets.update_outcome("missing", "死亡") is False


def test_cases_dataframe_returns_read_df(fake_conn):
    """cases_dataframe が _read_df の内容（列定義どおり）を返す。"""
    storage_sheets.save_case(_record("case-001"))
    df = storage_sheets.cases_dataframe()
    assert list(df.columns) == config.columns()
    assert len(df) == 1


def test_save_image_returns_empty_string(fake_conn):
    """クラウドでは画像保存しないので "" を返す。"""
    assert storage_sheets.save_image("case-001", object(), "ラベル") == ""
