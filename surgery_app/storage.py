"""保存バックエンドの切替役。

Streamlit secrets に [connections.gsheets] があれば Googleスプレッドシート、
無ければローカルファイルに保存する。app.py からはこのモジュールだけを呼ぶ。
"""

from __future__ import annotations

from surgery_app import storage_local


def _use_sheets() -> bool:
    """gsheets 接続が secrets に設定されていればクラウド保存を使う。"""
    try:
        import streamlit as st
        return "gsheets" in st.secrets.get("connections", {})
    except Exception:
        return False


def _backend():
    if _use_sheets():
        from surgery_app import storage_sheets
        return storage_sheets
    return storage_local


def new_case_id() -> str:
    return _backend().new_case_id()


def save_image(case_id, image, label):
    return _backend().save_image(case_id, image, label)


def save_case(record):
    return _backend().save_case(record)


def load_index():
    return _backend().load_index()


def load_case(case_id):
    return _backend().load_case(case_id)


def load_all_cases():
    return _backend().load_all_cases()


def update_outcome(case_id, outcome, extra_note=""):
    return _backend().update_outcome(case_id, outcome, extra_note)


def cases_dataframe():
    return _backend().cases_dataframe()
