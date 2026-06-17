"""ローカルファイル保存バックエンド（PC内 data/ に保存）。

症例ごとに data/cases/<case_id>/case.json と画像を保存する。
ローカル実行・会社PCサーバー運用で使用。

【データ取り扱いの原則】
- 馬主・個人を特定できる情報は保存しない（症例IDは匿名の日時+乱数）。
- data/ はローカルのみ・外部送信なし・リポジトリに含めない（.gitignore済み）。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
from PIL import Image

from surgery_app import config

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CASES_DIR = DATA_DIR / "cases"
INDEX_FILE = DATA_DIR / "cases_index.json"


def _ensure_dirs() -> None:
    CASES_DIR.mkdir(parents=True, exist_ok=True)


def new_case_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"


def save_image(case_id: str, image: Image.Image, label: str) -> str:
    _ensure_dirs()
    case_dir = CASES_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() else "_" for c in label)[:40] or "image"
    filename = f"{safe}_{datetime.now().strftime('%H%M%S')}.png"
    path = case_dir / filename
    image.convert("RGB").save(path)
    return str(path.relative_to(DATA_DIR))


def save_case(record: dict) -> str:
    _ensure_dirs()
    case_id = record.get("case_id") or new_case_id()
    record["case_id"] = case_id
    record.setdefault("saved_at", datetime.now().isoformat(timespec="seconds"))
    case_dir = CASES_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    _update_index(record)
    return case_id


def _update_index(record: dict) -> None:
    index = load_index()
    summary = {
        "case_id": record["case_id"],
        "saved_at": record.get("saved_at"),
        "condition": record.get("condition"),
        "decision": record.get("decision"),
        "outcome": record.get("outcome"),
    }
    index = [c for c in index if c.get("case_id") != record["case_id"]]
    index.append(summary)
    index.sort(key=lambda c: c.get("saved_at") or "", reverse=True)
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index() -> list[dict]:
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    return []


def load_case(case_id: str) -> dict | None:
    path = CASES_DIR / case_id / "case.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def load_all_cases() -> list[dict]:
    cases = []
    for summary in load_index():
        case = load_case(summary["case_id"])
        if case:
            cases.append(case)
    return cases


def update_outcome(case_id: str, outcome: str, extra_note: str = "") -> bool:
    case = load_case(case_id)
    if case is None:
        return False
    case["outcome"] = outcome
    if extra_note.strip():
        prev = case.get("notes", "")
        case["notes"] = (prev + "\n" + extra_note).strip() if prev else extra_note.strip()
    save_case(case)
    return True


def cases_dataframe() -> pd.DataFrame:
    """全症例をフラット表（DataFrame）で返す。CSV出力用。"""
    return config.build_cases_table(load_all_cases())
