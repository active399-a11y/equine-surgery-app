"""症例CSVの研究用集計スターター。

馬の開腹手術（結腸捻転・小腸絞扼）アプリが出力する症例CSV（1行=1症例、
日本語列名）を読み込み、「切除した群 vs 温存した群」などで色値・検査値を
比較するための要約を標準出力に表示し、まとめを CSV にも保存する。

使い方:
    python analysis/summarize_cases.py <equine_cases.csv のパス>
    （引数省略時は ./equine_cases.csv を読む）

設計方針:
- 列が欠けていてもクラッシュせず、存在する列だけ集計する。
- 数値列は to_numeric(errors="coerce") で安全に変換する。
- surgery_app.config が import できれば columns() を参照して列名のズレに強くする。
  import できない場合は文字列ベースのフォールバックで動く。
"""

from __future__ import annotations

import os
import sys

import pandas as pd

# ---- プロジェクトルートを sys.path に足して config を import できるようにする ----
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 列名の既定値（config が import できない場合のフォールバック）
META = {
    "case_id": "症例ID",
    "saved_at": "保存日時",
    "condition": "病態",
    "decision": "最終判断",
    "outcome": "転帰",
}
# 検査値の表示列名（labs.py の label(unit) と一致）
LAB_COLS_FALLBACK = [
    "Ht（ヘマトクリット）(%)",
    "血中乳酸値(mmol/L)",
    "白血球数(/µL)",
    "腹水中乳酸値(mmol/L)",
    "血中カリウム（K）(mEq/L)",
]

# config から正確な列名を取り出せれば差し替える
ALL_COLUMNS: list[str] | None = None
try:
    from surgery_app import config as _config  # type: ignore
    from surgery_app import labs as _labs  # type: ignore

    ALL_COLUMNS = _config.columns()
    META = {k: v for k, v in _config.META_COLS}
    LAB_COLS = [f"{f.label}({f.unit})" for f in _labs.LAB_FIELDS]
except Exception:  # noqa: BLE001  (フォールバックで動かすため広く捕捉)
    LAB_COLS = list(LAB_COLS_FALLBACK)


# ---- 判定基準 ----
# 最終判断のうち「切除する」だけを切除群、それ以外を非切除群とする。
DECISION_RESECT = "切除する"
# 転帰のうち生存とみなす値 / 死亡とみなす値（app.py の選択肢に対応）
OUTCOME_SURVIVE = {"生存・経過良好"}
OUTCOME_DEAD = {"死亡・安楽殺"}


def load_csv(path: str) -> pd.DataFrame:
    """CSV を読み込む。utf-8-sig（BOM付き）も試す。"""
    last_err: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError as e:
            last_err = e
            continue
    # ここまで来たら最後のエラーを投げる
    raise last_err if last_err else RuntimeError("CSV読み込みに失敗しました")


def existing(df: pd.DataFrame, cols: list[str]) -> list[str]:
    """df に実在する列だけ返す（欠損列はスキップ）。"""
    return [c for c in cols if c in df.columns]


def numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    """列を安全に数値化（変換不能はNaN）。"""
    return pd.to_numeric(df[col], errors="coerce")


def value_counts_section(df: pd.DataFrame, col: str, title: str) -> None:
    print(f"\n--- {title} ---")
    if col not in df.columns:
        print(f"  （列「{col}」が見つかりません。スキップ）")
        return
    vc = df[col].fillna("（未記入）").value_counts(dropna=False)
    for name, n in vc.items():
        print(f"  {name}: {n}")


def split_by_decision(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str | None]:
    """最終判断で 切除群 / 非切除群 に二分する。

    判断列が無ければ (空, 空, None) を返す。
    """
    dcol = META.get("decision", "最終判断")
    if dcol not in df.columns:
        return df.iloc[0:0], df.iloc[0:0], None
    is_resect = df[dcol].astype("string").str.strip() == DECISION_RESECT
    return df[is_resect], df[~is_resect], dcol


def summarize_numeric_by_group(
    groups: dict[str, pd.DataFrame],
    cols: list[str],
    df_all: pd.DataFrame,
) -> pd.DataFrame:
    """群ごとに各数値列の n/mean/median をまとめた縦長DataFrameを返す。"""
    cols = existing(df_all, cols)
    records: list[dict] = []
    for col in cols:
        rec: dict = {"指標": col}
        for gname, gdf in groups.items():
            s = numeric_series(gdf, col).dropna() if len(gdf) else pd.Series(dtype=float)
            rec[f"{gname}_n"] = int(s.count())
            rec[f"{gname}_mean"] = round(float(s.mean()), 2) if s.count() else None
            rec[f"{gname}_median"] = round(float(s.median()), 2) if s.count() else None
        records.append(rec)
    return pd.DataFrame(records)


def print_table(df: pd.DataFrame, title: str) -> None:
    print(f"\n=== {title} ===")
    if df.empty:
        print("  （対象列がありません。スキップ）")
        return
    with pd.option_context(
        "display.max_columns", None,
        "display.width", 200,
        "display.unicode.east_asian_width", True,
    ):
        print(df.to_string(index=False))


def color_columns(df: pd.DataFrame) -> list[str]:
    """存在する _暗さ と _赤み 列をすべて拾う。"""
    return [c for c in df.columns if c.endswith("_暗さ") or c.endswith("_赤み")]


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else "equine_cases.csv"
    if not os.path.exists(path):
        print(f"CSVが見つかりません: {path}", file=sys.stderr)
        return 1

    df = load_csv(path)

    print("=" * 60)
    print(f"症例CSV要約: {path}")
    print("=" * 60)

    # a) 件数系
    total = len(df)
    print(f"\n総症例数: {total}")
    value_counts_section(df, META.get("condition", "病態"), "病態別件数")
    value_counts_section(df, META.get("outcome", "転帰"), "転帰別件数")
    value_counts_section(df, META.get("decision", "最終判断"), "最終判断別件数")

    # 切除群 / 非切除群 に二分
    resect_df, keep_df, dcol = split_by_decision(df)
    if dcol is None:
        print("\n（「最終判断」列が無いため群別比較はスキップします）")
        groups: dict[str, pd.DataFrame] = {"全症例": df}
    else:
        groups = {
            "切除群": resect_df,
            "非切除群": keep_df,
        }
        print(f"\n群分け（最終判断=「{DECISION_RESECT}」を切除群）:"
              f" 切除群 n={len(resect_df)} / 非切除群 n={len(keep_df)}")

    # b) 検査値の群別比較
    lab_summary = summarize_numeric_by_group(groups, LAB_COLS, df)
    print_table(lab_summary, "検査値の群別比較（mean/median/n）")

    # c) 色指標（_暗さ / _赤み）の群別比較
    ccols = color_columns(df)
    color_summary = summarize_numeric_by_group(groups, ccols, df)
    print_table(color_summary, "色指標（暗さ/赤み）の群別比較（mean/median/n）")

    # d) 転帰別の検査値要約（生存 vs 死亡・安楽殺）
    ocol = META.get("outcome", "転帰")
    outcome_summary = pd.DataFrame()
    if ocol in df.columns:
        ser = df[ocol].astype("string").str.strip()
        outcome_groups = {
            "生存群": df[ser.isin(OUTCOME_SURVIVE)],
            "死亡・安楽殺群": df[ser.isin(OUTCOME_DEAD)],
        }
        outcome_summary = summarize_numeric_by_group(outcome_groups, LAB_COLS, df)
        print_table(outcome_summary, "転帰別の検査値要約（生存 vs 死亡・安楽殺）")
    else:
        print(f"\n（「{ocol}」列が無いため転帰別要約はスキップ）")

    # ---- まとめを CSV に保存 ----
    out_path = os.path.join(_THIS_DIR, "summary_output.csv")
    parts: list[pd.DataFrame] = []
    if not lab_summary.empty:
        t = lab_summary.copy()
        t.insert(0, "区分", "検査値(最終判断別)")
        parts.append(t)
    if not color_summary.empty:
        t = color_summary.copy()
        t.insert(0, "区分", "色指標(最終判断別)")
        parts.append(t)
    if not outcome_summary.empty:
        t = outcome_summary.copy()
        t.insert(0, "区分", "検査値(転帰別)")
        parts.append(t)

    if parts:
        combined = pd.concat(parts, ignore_index=True, sort=False)
    else:
        combined = pd.DataFrame(columns=["区分", "指標"])
    combined.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nまとめを保存しました: {out_path}")
    print(f"  （{len(combined)}行 / 列: {list(combined.columns)}）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
