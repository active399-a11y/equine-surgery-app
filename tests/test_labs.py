"""labs モジュールのテスト。"""

from __future__ import annotations

from surgery_app.labs import LAB_FIELDS


def test_lab_field_keys():
    """検査値キーの集合が仕様どおり5項目と一致する。"""
    keys = {fld.key for fld in LAB_FIELDS}
    assert keys == {"ht", "blood_lactate", "wbc", "periton_lactate", "blood_k"}


def test_lab_field_units_non_empty():
    """各項目の unit が非空。"""
    for fld in LAB_FIELDS:
        assert fld.unit, f"{fld.key} の unit が空"


def test_lab_field_labels_non_empty():
    """各項目の label が非空（列名に使われるため）。"""
    for fld in LAB_FIELDS:
        assert fld.label
