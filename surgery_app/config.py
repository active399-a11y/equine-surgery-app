"""アプリ共通の定義（撮影ターゲット・列定義・フラット化）。

app.py と storage バックエンド（ローカル/Googleスプレッドシート）で共有する。
1症例の入れ子レコードを、1行＝1症例のフラットな表（CSV/シート用）に変換する。
"""

from __future__ import annotations

import pandas as pd

from surgery_app import labs

# 病態ごとの撮影ターゲット（slot_key, 見出し, 撮影ガイド）
COLOR_TARGETS: dict[str, list[tuple[str, str, str]]] = {
    "結腸捻転（大結腸）": [
        ("colon_serosa", "① 結腸全体（漿膜）", "結腸全体の漿膜が写るように撮影してください。"),
        ("pelvic_mucosa", "② 結腸骨盤曲・切開部の粘膜", "骨盤曲の切開部の粘膜を撮影してください。"),
    ],
    "小腸絞扼": [
        ("resection_line", "切除ライン", "健常部と病変部の境界（切除予定ライン）を撮影してください。"),
    ],
}
# slot_key -> 表示ラベル
SLOT_LABELS = {k: t for slots in COLOR_TARGETS.values() for k, t, _ in slots}

# 色指標の表示名（列名に使用）
METRIC_JP = {"redness": "赤み", "darkness": "暗さ", "h": "色相H",
             "s": "彩度S", "v": "明度V", "hint": "色ヒント"}

# 症例メタ列（内部キー -> 表示列名）
META_COLS = [
    ("case_id", "症例ID"),
    ("saved_at", "保存日時"),
    ("condition", "病態"),
    ("decision", "最終判断"),
    ("outcome", "転帰"),
]


def flatten_record(c: dict) -> dict:
    """1症例の入れ子レコードを {表示列名: 値} の1行に変換する。"""
    row: dict = {}
    for key, label in META_COLS:
        row[label] = c.get(key)
    lab = c.get("labs") or {}
    for fld in labs.LAB_FIELDS:
        row[f"{fld.label}({fld.unit})"] = lab.get(fld.key)
    color = c.get("color") or {}
    for slot_key, slot_label in SLOT_LABELS.items():
        entry = color.get(slot_key) or {}
        for mk, jp in METRIC_JP.items():
            val = entry.get(mk)
            if isinstance(val, (int, float)) and mk != "hint":
                val = round(val, 1)
            row[f"{slot_label}_{jp}"] = val
    row["メモ"] = c.get("notes")
    return row


def columns() -> list[str]:
    """フラット表の列順（空でも常にこの順）。"""
    return list(flatten_record({}).keys())


def build_cases_table(cases: list[dict]) -> pd.DataFrame:
    """全症例をフラット表（DataFrame）に。"""
    rows = [flatten_record(c) for c in cases]
    return pd.DataFrame(rows, columns=columns())
