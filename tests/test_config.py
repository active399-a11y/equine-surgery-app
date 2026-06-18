"""config モジュール（フラット化・列定義）のテスト。"""

from __future__ import annotations

from surgery_app import config


def _sample_record() -> dict:
    """入れ子の1症例レコード（色2スロット＋一部検査値＋判断/転帰/メモ）。"""
    return {
        "case_id": "20260618-120000-abc123",
        "saved_at": "2026-06-18T12:00:00",
        "condition": "結腸捻転（大結腸）",
        "decision": "温存",
        "outcome": "生存",
        "notes": "整復後に色が回復",
        "labs": {
            "ht": 45.0,
            "blood_lactate": 3.2,
        },
        "color": {
            "colon_serosa": {
                "redness": 55.4,
                "darkness": 80.1,
                "h": 350.2,
                "s": 40.5,
                "v": 60.3,
                "hint": "生存寄り",
            },
            "pelvic_mucosa": {
                "redness": 30.1,
                "darkness": 120.6,
                "h": 10.7,
                "s": 25.2,
                "v": 50.8,
                "hint": "判定不能（追加評価を）",
            },
        },
    }


def test_flatten_record_contains_meta_columns():
    """症例ID/病態/転帰/メモ がフラット行に含まれる。"""
    row = config.flatten_record(_sample_record())
    for col in ("症例ID", "病態", "転帰", "メモ"):
        assert col in row
    assert row["症例ID"] == "20260618-120000-abc123"
    assert row["病態"] == "結腸捻転（大結腸）"
    assert row["転帰"] == "生存"
    assert row["メモ"] == "整復後に色が回復"


def test_flatten_record_contains_lab_columns():
    """検査値列（ラベル(単位)）が含まれ、値が反映される。"""
    from surgery_app import labs

    row = config.flatten_record(_sample_record())
    ht = labs.LAB_FIELDS[0]
    col = f"{ht.label}({ht.unit})"
    assert col in row
    assert row[col] == 45.0


def test_flatten_record_contains_color_columns():
    """色値列（スロットラベル_指標名）が含まれる。"""
    row = config.flatten_record(_sample_record())
    serosa_label = config.SLOT_LABELS["colon_serosa"]
    # 赤み列が存在し、丸められた値が入る
    redness_col = f"{serosa_label}_赤み"
    assert redness_col in row
    assert row[redness_col] == 55.4


def test_columns_match_empty_flatten_keys():
    """columns() と flatten_record({}).keys() の順序が一致する。"""
    assert config.columns() == list(config.flatten_record({}).keys())


def test_build_cases_table_row_count():
    """build_cases_table の行数が症例数と一致する。"""
    cases = [_sample_record(), _sample_record(), _sample_record()]
    df = config.build_cases_table(cases)
    assert len(df) == len(cases)
    assert list(df.columns) == config.columns()


def test_build_cases_table_empty():
    """空リストでも列定義どおりの空DataFrameを返す。"""
    df = config.build_cases_table([])
    assert len(df) == 0
    assert list(df.columns) == config.columns()
