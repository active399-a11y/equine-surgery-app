"""馬開腹手術 判断支援アプリ — MVP（統合版）

結腸捻転・小腸絞扼の術中に、腸管の「切除すべきか否か」の判断を支援・記録する。
本アプリは診断・切除判断を行うものではなく、外科医の判断材料を客観化し、
1症例として記録する支援ツールである。

1症例＝1記録に統合：撮影（色診断）＋検査値＋最終判断・転帰を1画面で入力し、
1ボタンでまとめて保存する。300症例規模の研究データセット化を見据えた構成。

起動: streamlit run app.py  （または アプリ起動.bat）
"""

from __future__ import annotations

import streamlit as st
from PIL import Image

from surgery_app import color_analysis, config, labs, pwa, storage
from surgery_app.config import COLOR_TARGETS, SLOT_LABELS

# 背面カメラ（術野向き）コンポーネント。未導入環境では他手段にフォールバック。
try:
    from streamlit_back_camera_input import back_camera_input
    _HAS_BACK_CAMERA = True
except Exception:
    _HAS_BACK_CAMERA = False

st.set_page_config(page_title="馬開腹手術 判断支援", page_icon="🐴", layout="wide")

# iPad/iPhone で「ホーム画面に追加」した際にアプリ風（専用アイコン・全画面）にする
pwa.enable()


def _init_state() -> None:
    st.session_state.setdefault("case_id", storage.new_case_id())


_init_state()

st.title("🐴 馬開腹手術 判断支援アプリ")
st.caption(
    "結腸捻転・小腸絞扼の術中サポート（MVP）。診断・切除可否の決定は行いません。"
    "所見の客観的記録と整理が目的です。最終判断は必ず術者が行ってください。"
)

# 現在の保存先を明示
if storage.backend_name() == "gsheets":
    st.caption("💾 保存先: **Googleスプレッドシート（クラウドに永続保存）**")
else:
    st.warning(
        "💾 保存先: ローカル（このサーバーのディスク）。"
        "**クラウドではアプリ再起動でデータが消えます。** "
        "本番記録の前にGoogleスプレッドシート連携を設定してください（DEPLOY.md STEP 2）。",
        icon="⚠️",
    )

with st.sidebar:
    st.header("症例設定")
    condition = st.radio("対象病態", list(COLOR_TARGETS.keys()), key="condition")
    st.text_input("症例ID（匿名）", value=st.session_state.case_id, disabled=True,
                  help="馬主・個人情報は含めないでください。")
    if st.button("新しい症例を開始", width="stretch"):
        # 撮影画像・入力をクリア
        for key in list(st.session_state.keys()):
            if key.startswith(("img_", "src_", "back_", "cam_", "file_",
                               "cx_", "cy_", "sz_", "lab_")):
                del st.session_state[key]
        st.session_state.case_id = storage.new_case_id()
        st.rerun()

    st.divider()
    with st.expander("色診断の閾値（仮設定・任意）"):
        st.caption("正解は存在しないため仮の閾値です。過去症例で調整してください。")
        v_th = st.slider("壊死寄りと判定する明度V未満", 0, 100, 70)
        s_th = st.slider("判定不能とする彩度S未満", 0, 100, 60)

    st.warning(
        "⚠️ 研究・記録目的の試用ツールです。正式な診断機器ではありません。",
        icon="⚠️",
    )


def render_capture(slot_key: str, title: str, guidance: str,
                   v_th: int, s_th: int) -> tuple[object, str | None]:
    """1ターゲットの撮影＋色診断UIを描画し、(ColorMetrics, hint) を返す。"""
    st.markdown(f"#### {title}")
    st.caption(guidance)

    src_opts = (["背面カメラ"] if _HAS_BACK_CAMERA else []) + ["前面/PC", "ファイル"]
    src = st.radio("取得方法", src_opts, horizontal=True,
                   key=f"src_{slot_key}", label_visibility="collapsed")
    st.caption("📱 iPad/iPhoneで撮影ボタンが出ない時は「ファイル」→「写真を撮る」で"
               "純正カメラ（背面・シャッター付き）が使えます。")

    f = None
    if src == "背面カメラ":
        f = back_camera_input(key=f"back_{slot_key}")
    elif src == "前面/PC":
        f = st.camera_input("撮影", label_visibility="collapsed", key=f"cam_{slot_key}")
    else:
        f = st.file_uploader("画像（JPG/PNG／カメラ撮影）", type=["jpg", "jpeg", "png"],
                             key=f"file_{slot_key}",
                             help="iPad/iPhoneではここから純正カメラで撮影できます。")
    if f is not None:
        st.session_state[f"img_{slot_key}"] = Image.open(f)

    image = st.session_state.get(f"img_{slot_key}")
    if image is None:
        st.info("画像を取得すると色診断が表示されます。")
        return None, None

    c1, c2 = st.columns([1, 2])
    with c1:
        cx = st.slider("水平位置 %", 0, 100, 50, key=f"cx_{slot_key}")
        cy = st.slider("垂直位置 %", 0, 100, 50, key=f"cy_{slot_key}")
        size = st.slider("枠の大きさ %", 5, 80, 25, key=f"sz_{slot_key}")
    roi = color_analysis.normalize_roi(cx, cy, size, image.width, image.height)
    with c2:
        st.image(color_analysis.draw_roi_overlay(image, roi),
                 caption="水色の枠が解析対象", width="stretch")

    m = color_analysis.analyze_roi(image, roi)
    mc = st.columns(4)
    mc[0].metric("赤み指標", f"{m.redness:.1f}", help="R-(G+B)/2。高いほど赤い。")
    mc[1].metric("暗さ指標", f"{m.darkness:.0f}", help="高いほど暗い（壊死傾向）。")
    mc[2].metric("色相 H", f"{m.h:.0f}°")
    mc[3].metric("明度 V", f"{m.v:.0f}%")

    hint, lvl = color_analysis.viability_hint(m, v_th, s_th)
    {"ok": st.success, "warn": st.warning, "alert": st.error}[lvl](f"色ヒント: {hint}")
    return m, hint


# =========================================================================
# 1. 撮影と色診断
# =========================================================================
st.header("1. 撮影と色診断")
slots = COLOR_TARGETS[condition]
color_results: dict[str, tuple[object, str | None]] = {}
for i, (slot_key, title, guidance) in enumerate(slots):
    color_results[slot_key] = render_capture(slot_key, title, guidance, v_th, s_th)
    if i < len(slots) - 1:
        st.divider()

# =========================================================================
# 2. 検査値（実測値）
# =========================================================================
st.header("2. 検査値（実測値を入力）")
st.caption("未測定の項目は空欄のままで構いません。")
lab_values: dict[str, float | None] = {}
cols = st.columns(len(labs.LAB_FIELDS))
for col, fld in zip(cols, labs.LAB_FIELDS):
    with col:
        lab_values[fld.key] = st.number_input(
            f"{fld.label}\n（{fld.unit}）",
            min_value=fld.min_value, max_value=fld.max_value,
            value=None, step=fld.step, help=fld.help, key=f"lab_{fld.key}",
        )

# =========================================================================
# 3. 最終判断・転帰
# =========================================================================
st.header("3. 最終判断・転帰")
c1, c2 = st.columns(2)
with c1:
    decision = st.radio("最終判断（術者）",
                        ["未定", "切除しない", "切除する", "再評価", "判定不能"],
                        horizontal=True)
with c2:
    outcome = st.selectbox("転帰（後で更新可）",
                           ["未記入", "生存・経過良好", "合併症あり", "死亡・安楽殺", "不明"])
notes = st.text_area("メモ（馬主・個人情報は記入しないこと）", height=80)

# =========================================================================
# 4. 保存
# =========================================================================
st.header("4. 症例を保存")
if st.button("💾 この症例をまとめて保存", type="primary", width="stretch"):
    case_id = st.session_state.case_id
    color_record: dict[str, dict] = {}
    for slot_key, (m, hint) in color_results.items():
        if m is None:
            continue
        entry = {**m.to_dict(), "hint": hint, "label": SLOT_LABELS[slot_key]}
        img = st.session_state.get(f"img_{slot_key}")
        if img is not None:
            entry["image_path"] = storage.save_image(case_id, img, slot_key)
        color_record[slot_key] = entry

    record = {
        "case_id": case_id,
        "condition": condition,
        "color": color_record,
        "labs": lab_values,
        "decision": decision,
        "outcome": outcome,
        "notes": notes,
    }
    try:
        storage.save_case(record)
        st.success(f"症例 {case_id} を保存しました（撮影 {len(color_record)} か所・検査値含む）。")
    except Exception as e:  # クラウド接続不良などで落とさず原因を提示
        st.error(f"保存に失敗しました: {e}\n"
                 "クラウド保存の場合、シート共有・Secrets設定をご確認ください（DEPLOY.md）。")

st.divider()
st.header("保存済み症例 ・ 転帰更新 ・ 出力")
try:
    index = storage.load_index()
except Exception as e:
    st.error(f"症例一覧の読込に失敗しました: {e}")
    index = []
if not index:
    st.info("まだ保存された症例はありません。")
else:
    st.dataframe(
        index, width="stretch", hide_index=True,
        column_config={
            "case_id": "症例ID", "saved_at": "保存日時", "condition": "病態",
            "decision": "判断", "outcome": "転帰",
        },
    )
    _loc = ("Googleスプレッドシート（クラウド）" if storage.backend_name() == "gsheets"
            else "このPC内 data/（外部送信なし）")
    st.caption(f"合計 {len(index)} 症例。保存先: {_loc}。")

    # --- CSV出力（表計算で開ける） ---
    try:
        df = storage.cases_dataframe()
        csv = df.to_csv(index=False).encode("utf-8-sig")  # BOM付きでExcel文字化け回避
        st.download_button(
            "⬇ 結果一覧をCSVで出力（Excel等で開けます）",
            data=csv, file_name="equine_cases.csv", mime="text/csv", width="stretch",
        )
    except Exception as e:
        st.warning(f"CSV出力の生成に失敗しました: {e}")

    # --- 数日後に判明する転帰を後から更新 ---
    st.subheader("転帰を後から更新")
    st.caption("生存・死亡などの結果が判明したら、症例を選んで転帰だけ更新できます。")
    outcome_opts = ["未記入", "生存・経過良好", "合併症あり", "死亡・安楽殺", "不明"]
    labels = [f"{c['case_id']}　｜　{c.get('condition','')}　｜　現在: {c.get('outcome','未記入')}"
              for c in index]
    sel = st.selectbox("症例を選択", options=list(range(len(index))),
                       format_func=lambda i: labels[i])
    target_id = index[sel]["case_id"]
    cur = index[sel].get("outcome", "未記入")
    new_outcome = st.selectbox(
        "転帰", outcome_opts,
        index=outcome_opts.index(cur) if cur in outcome_opts else 0,
        key="upd_outcome",
    )
    add_note = st.text_area("追記メモ（任意・馬主情報は記入しない）", key="upd_note", height=70)
    if st.button("転帰を更新", key="upd_btn"):
        if storage.update_outcome(target_id, new_outcome, add_note):
            st.success(f"{target_id} の転帰を「{new_outcome}」に更新しました。")
            st.rerun()
        else:
            st.error("更新に失敗しました（症例が見つかりません）。")
