# 馬開腹手術 判断支援アプリ — プロジェクト指示書 (CLAUDE.md)

このファイルは Claude Code が起動時に自動で読む文脈ファイル。新しいセッションでも
ここを読めば全体像を把握して自走できる。

## 目的（何を作っているか）
馬の急性腹症手術（**結腸捻転 / 小腸絞扼**）の術中に、腸管の「**切除すべきか否か**」の
判断を**支援・記録**するアプリ。

- 結腸捻転 → 結腸骨盤曲の**漿膜と粘膜**を撮影して色を客観評価。
- 小腸絞扼 → **切除ライン**（健常部と病変部の境界）を撮影して所見を整理。

## 最重要の設計思想（必ず守る）
腸管生存性の視覚的評価は獣医外科で最も難しく、漿膜色の主観評価は
「最も簡便だが最も不正確」とされる。整復後に漿膜色が回復しても粘膜生存性とは相関しない。

→ したがって本アプリは **AIが切除を「決める」装置ではない**。
   外科医の判断材料を **客観的に数値化し、所見を構造化して記録する支援ツール** に徹する。
   UI・文言でも常に「最終判断は術者」「診断機器ではない」ことを明示すること。

## アプリ構成（2026-06-15 統合版）
1症例＝1記録に統合。`app.py` は単一ページで上から順に入力し、1ボタンで保存する。
- **撮影は最小限のターゲットのみ**:
  - 結腸捻転 → ①結腸全体（漿膜） ②結腸骨盤曲・切開部の粘膜（この2か所だけ）
  - 小腸絞扼 → 切除ライン（1か所）
- **検査値は実数値で記録**（区分ではなく数値。研究データ化のため）: Ht / 血中乳酸 / 白血球数 /
  腹水中乳酸 / 血中K の5項目のみ（`surgery_app/labs.py`）。主観的な所見チェックリストは廃止。
- 各撮影で色診断（赤み/暗さ/HSV＋生存寄り/判定不能/壊死寄りの3段階ヒント）。
- 規模感: 年60頭 → 300症例貯まれば研究データとして価値。保存JSONは1症例1ファイルで後解析しやすい形。

## 1ヶ月MVPのスコープ（やること / やらないこと）
- やる: ①色の客観的数値化 ②検査値の実数値記録 ③症例記録（統合）。すべて機械学習なし。
- やらない: AIによる腸管診断モデルの学習（教師データが数百〜数千枚必要で1ヶ月では不可能）。
  → 症例記録機能で貯めたデータが、将来のAI学習データセットと症例報告の素材になる（第2段階）。

## 技術スタック（決定済み）
- **Streamlit**（Pythonのみで完結。ユーザーはPython初級）。
- 画像処理は **Pillow + NumPy**。**OpenCVは使わない**
  （Python 3.14 ではOpenCVのビルド済みwheelが無いため。色解析は自前実装で代替済み）。
- スマホ対応は **PWA / ブラウザ**。ネイティブアプリ（Swift/Kotlin・ストア審査）は1ヶ月では非対象。
- カメラは `st.camera_input`（写真撮影）+ ファイルアップロード。
  ※ streamlit-webrtc（ライブ映像）は使っていない。写真解析には camera_input の方が
    iPhone Safari で安定し、初級者にも扱いやすいという判断。

## 環境
- Windows 11 / Python 3.14.5 / Streamlit 1.57 / Pillow 12 / NumPy 2.4 / pandas 3。
- 起動: `streamlit run app.py`
- スマホ実機テストには HTTPS が必須（iPhone Safari はHTTPSでないとカメラ不可）。READMEのngrok手順参照。

## ファイル構成
```
equine-surgery-app/
├─ app.py                     # Streamlit本体（3タブ: 撮影&色解析 / チェックリスト / 症例記録）
├─ start_app.ps1 / アプリ起動.bat  # ローカル起動ランチャー（Streamlit+トンネル+QR）
├─ DEPLOY.md                  # クラウド常時稼働(Streamlit Cloud+Googleシート)の手順
├─ tests/                     # pytest 27件（color/labs/config/storage_local/storage_sheets[fake]）
├─ analysis/summarize_cases.py # 研究用集計(切除vs温存・生存vs死亡の色値/検査値比較)
├─ .github/workflows/ci.yml   # push/PRでpytest自動実行(Python3.12)
├─ assets/app_icon_*.png      # iPad/iPhoneアプリ用アイコン（PWA）
├─ .streamlit/secrets.toml.example  # gsheets接続の雛形（実secretsはgitignore）
├─ surgery_app/
│  ├─ color_analysis.py       # ROIの色をRGB/HSVで数値化＋3段階ヒント（Pillow+NumPy）
│  ├─ labs.py                 # 記録する検査値5項目の定義（Ht/乳酸/WBC/腹水乳酸/K）
│  ├─ config.py               # 撮影ターゲット・列定義・フラット化（app/storage共通）
│  ├─ pwa.py                  # 起動時にStreamlitのindex.htmlへApple用PWAメタを注入
│  ├─ storage.py              # 保存先の切替役（secretsにgsheetsがあればクラウド）
│  ├─ storage_local.py        # ローカルファイル保存（data/）
│  └─ storage_sheets.py       # Googleスプレッドシート保存（クラウド常時稼働用）
├─ data/                      # 症例データ（.gitignore済み・外部送信しない）
├─ requirements.txt
├─ README.md                  # セットアップ・HTTPS手順・使い方・倫理メモ・ロードマップ
└─ .streamlit/config.toml
```

## データ取り扱いの原則（厳守）
- 馬主・個人を特定できる情報は保存しない（症例IDは匿名の日時+乱数）。
- データは `data/` にローカル保存のみ。外部送信しない。リポジトリに含めない。
- 院内では「研究・記録目的の試用、正式な診断機器ではない」ことを明示してから使う。

## テスト方法
- コアロジック: `python -c "..."` で color_analysis / checklist / storage を直接検証。
- レンダリング: `streamlit.testing.v1.AppTest` で `app.py` を実行し例外0を確認。

## ロードマップ上の現在地と次の一手
- 第1週(カメラ表示) / 第2週(色解析) / 第3週(チェックリスト+記録) のコア機能は**実装済み**。
- 次の一手: ①スマホ実機でHTTPS経由のカメラ動作確認（README手順） 
  ②過去の術中写真があれば色レンジ閾値を調整 ③第4週=現場投入の運用設計（誰が滅菌野外で操作するか）。

## コーディング方針
- UIとコメントは日本語。Python初級者が読んで理解できる平易さを保つ。
- 追加依存はできるだけ増やさない（既にインストール済みのもので完結させる）。
