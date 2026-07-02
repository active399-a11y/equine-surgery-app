"""Googleスプレッドシートを保存先にするバックエンド（クラウド常時稼働用）。

Streamlit Cloud はファイルが永続化されない（再起動で消える）ため、症例データは
Googleスプレッドシートに1行＝1症例で書き込む。ユーザーはそのシートを表計算として
そのまま閲覧でき、CSV要望とも一致する。

実装メモ:
  st-gsheets-connection の update/create はワークシート情報をキャッシュし、
  実在するタブを「無い」と誤判定することがあったため、ここでは gspread を直接使い、
  毎回スプレッドシートを開いて get-or-create する確実な方式にしている。

接続情報は Streamlit secrets の [connections.gsheets] に置く（DEPLOY.md 参照）。
画像のクラウド永続保存は本MVPでは行わない（数値データのみシートに蓄積）。
"""

from __future__ import annotations

from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from gspread_dataframe import get_as_dataframe, set_with_dataframe

from surgery_app import config

WORKSHEET = "cases"

# サービスアカウントJSONに含まれるキーだけを認証に渡す（spreadsheet等の余分は除く）
_SA_KEYS = {
    "type", "project_id", "private_key_id", "private_key", "client_email",
    "client_id", "auth_uri", "token_uri", "auth_provider_x509_cert_url",
    "client_x509_cert_url", "universe_domain",
}


def _secrets() -> dict:
    return dict(st.secrets["connections"]["gsheets"])


@st.cache_resource(show_spinner=False)
def _client() -> gspread.Client:
    sa = {k: v for k, v in _secrets().items() if k in _SA_KEYS}
    return gspread.service_account_from_dict(sa)


def _worksheet() -> gspread.Worksheet:
    """毎回スプレッドシートを開き、書き込み先のタブを返す（新規作成はしない）。

    タブ名 cases を寛容に照合（前後空白・大文字小文字を無視）。
    見つからなければ最初のタブを使う。add_worksheet は呼ばないため
    『addSheet already exists』エラーは発生し得ない。
    """
    sh = _client().open_by_url(_secrets()["spreadsheet"])
    worksheets = sh.worksheets()
    for ws in worksheets:
        if ws.title.strip().lower() == WORKSHEET:
            return ws
    return worksheets[0]


@st.cache_data(ttl=300, show_spinner=False)
def _read_df() -> pd.DataFrame:
    """シート全体をDataFrameで読む。空・未作成時は定義列の空表を返す。

    毎操作でAPIを叩くと重いため結果をキャッシュ（保存/更新時に破棄）。
    """
    try:
        ws = _worksheet()
        df = get_as_dataframe(ws, evaluate_formulas=True)
        df = df.dropna(how="all")
        for col in config.columns():
            if col not in df.columns:
                df[col] = None
        return df[config.columns()]
    except Exception:
        return pd.DataFrame(columns=config.columns())


def _clear_cache() -> None:
    try:
        _read_df.clear()
    except Exception:
        pass


def _write_df(df: pd.DataFrame) -> None:
    ws = _worksheet()
    ws.clear()
    set_with_dataframe(ws, df[config.columns()])
    _clear_cache()  # 書き込んだら次の読み込みは最新を取得


def save_case(record: dict) -> str:
    case_id = record.get("case_id") or new_case_id()
    record["case_id"] = case_id
    record.setdefault("saved_at", datetime.now().isoformat(timespec="seconds"))

    df = _read_df()
    df = df[df["症例ID"] != case_id]  # 同IDがあれば置換
    new_row = pd.DataFrame([config.flatten_record(record)], columns=config.columns())
    df = pd.concat([df, new_row], ignore_index=True)
    df = df.sort_values("保存日時", ascending=False, na_position="last")
    _write_df(df)
    return case_id


def load_index() -> list[dict]:
    df = _read_df()
    out = []
    for _, r in df.iterrows():
        if not r.get("症例ID"):
            continue
        out.append({
            "case_id": r.get("症例ID"),
            "saved_at": r.get("保存日時"),
            "condition": r.get("病態"),
            "decision": r.get("最終判断"),
            "outcome": r.get("転帰"),
        })
    return out


def load_case(case_id: str) -> dict | None:
    df = _read_df()
    hit = df[df["症例ID"] == case_id]
    if hit.empty:
        return None
    r = hit.iloc[0]
    return {
        "case_id": r.get("症例ID"),
        "saved_at": r.get("保存日時"),
        "condition": r.get("病態"),
        "decision": r.get("最終判断"),
        "outcome": r.get("転帰"),
        "notes": r.get("メモ"),
    }


def load_all_cases() -> list[dict]:
    """シートの全行をそのまま（フラットな）辞書のリストで返す。"""
    return _read_df().to_dict(orient="records")


def cases_dataframe() -> pd.DataFrame:
    """全症例をフラット表（DataFrame）で返す。シートはすでにフラットなのでそのまま。"""
    return _read_df()


def update_outcome(case_id: str, outcome: str, extra_note: str = "") -> bool:
    df = _read_df()
    mask = df["症例ID"] == case_id
    if not mask.any():
        return False
    df.loc[mask, "転帰"] = outcome
    if extra_note.strip():
        prev = df.loc[mask, "メモ"].fillna("").iloc[0]
        df.loc[mask, "メモ"] = (str(prev) + "\n" + extra_note).strip()
    _write_df(df)
    return True


def save_image(case_id: str, image, label: str) -> str:
    """クラウドでは画像の永続保存は行わない（数値のみシートに蓄積）。"""
    return ""


def new_case_id() -> str:
    import uuid
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"
