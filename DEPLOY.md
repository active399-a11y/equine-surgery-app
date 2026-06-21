# クラウド常時稼働 デプロイ手順（会社iPadで常用するため）

固定URLで・PC不要・どこからでもアクセスでき、症例データはGoogleスプレッドシートに
蓄積されます。設定は最初の一度だけ。所要 30〜60分。

> アカウントが必要なステップ（GitHub / Google / Streamlit）はDamiさん自身の操作が必要です。
> 各ステップで詰まったら、画面の表示を伝えてくれれば一緒に進めます。

---

## 全体像
```
あなたのPC ──push──> GitHub（コード置き場）
                        │
                        ▼
                 Streamlit Cloud（アプリを常時稼働・固定URL）
                        │  読み書き
                        ▼
            Googleスプレッドシート（症例データが溜まる＝表計算）
                        ▲
                 会社のiPad（アイコンから起動）
```

---

## STEP 1. GitHub にコードを上げる ✅ 完了済み
- リポジトリ作成・push済み: https://github.com/active399-a11y/equine-surgery-app （Private・ブランチ`main`）
- 以降コードを直したら `git push` で自動反映されます（data/ と secrets.toml は除外設定済み）。

---

## STEP 2. Googleスプレッドシートと「サービスアカウント」を用意
アプリがシートに書き込むための鍵を作ります。

### 2-1. スプレッドシート作成
1. https://sheets.google.com で新規スプレッドシート作成。名前は任意（例: 馬開腹症例DB）。
2. 左下のシートタブ名を `cases` に変更。
3. ブラウザのURL（`https://docs.google.com/spreadsheets/d/●●●●/edit`）を控える。

### 2-2. サービスアカウント作成（Google Cloud）
1. https://console.cloud.google.com → 上部でプロジェクト新規作成（例: equine-app）。
2. 「APIとサービス」→「ライブラリ」で **Google Sheets API** を検索し「有効にする」。
   （同様に **Google Drive API** も有効化）
3. 「APIとサービス」→「認証情報」→「認証情報を作成」→「サービスアカウント」。
   名前を付けて作成（権限はスキップで可）。
4. 作ったサービスアカウントを開く →「キー」タブ →「鍵を追加」→「新しい鍵」→ **JSON** → ダウンロード。
5. ダウンロードしたJSONを開き、`client_email`（〜@〜.iam.gserviceaccount.com）をコピー。
6. **2-1のスプレッドシートを開き、右上「共有」で、その client_email を「編集者」で共有**。
   ← これを忘れると書き込めません。

---

## STEP 3. Streamlit Cloud でアプリを公開 ✅ 完了済み
- デプロイ済み・固定URL: **https://equine-surgery-app-drixvmffbujfp7dj38lguu.streamlit.app/**
- これ以降、コードを直して `git push` すると自動で再デプロイされます。
- ※ Secrets（Googleシート連携）は未設定。設定するまではデータが永続化されません（STEP 2 を後で実施）。
  設定方法: Streamlit Cloud の対象アプリ →「⋮」or Manage app →「Settings」→「Secrets」に
  `.streamlit/secrets.toml.example` の形式で貼り付け → Save（自動再起動）。

---

## STEP 3.5. ★アプリを「公開」にする（最重要・朝イチでこれ）
現状、アプリを開くと **ログイン画面に飛びます**（=非公開設定）。iPadでログインなしに使うには公開にします。
1. https://share.streamlit.io → 対象アプリの「⋮」→ **Settings** →「Sharing」。
2. 「Who can view this app」を **「This app is public」/「Anyone with the link」** に変更して保存。
   - これで誰でもURL/QRから直接開けます（クリニック用ツール・個人情報は入力しない前提）。
   - ※ 逆に「院外からは触らせたくない」なら非公開のまま、各iPadで一度ログイン運用でもOK（よりセキュア）。

---

## STEP 4. 会社のiPadにアイコンを置く
1. iPadのSafariで固定URL（上記）を開く。※QRコードはチャットに生成済み。
2. 共有ボタン（□に↑）→ **「ホーム画面に追加」**。
3. 名前「馬開腹判断支援」・専用アイコンが出るので「追加」。
4. ホーム画面のアイコンから、全画面のアプリとして起動できます。

これで毎回タップ一つ・どこでも・（STEP 2 設定後は）データはスプレッドシートに自動蓄積されます。

---

## 補足
- **データの置き場所**: 症例の数値（色値・検査値・転帰）はGoogleスプレッドシートに保存され、
  そのまま表計算として開けます。馬主等の個人情報は入力しない運用にしてください。
- **画像**: クラウド版では術中画像の永続保存は行いません（数値のみ蓄積）。画像も残したい場合は
  Google Drive連携を追加できます（要相談）。
- **ローカルでも動く**: secrets未設定なら従来どおり `data/` にローカル保存されます（`アプリ起動.bat`）。
