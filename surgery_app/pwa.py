"""iPad/iPhone でホーム画面に追加した時に「アプリ風」にするためのPWA設定。

Streamlit は <head> を直接いじれないため、起動時に Streamlit パッケージ内の
static/index.html へ Apple用メタタグとアイコンを注入する（冪等）。
これにより Safari の「ホーム画面に追加」で、専用アイコン・アプリ名・全画面表示になる。

ローカルでもクラウド(Streamlit Cloud)でも実行時に適用される。失敗してもアプリ本体は動く。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import streamlit as st

_MARKER = "<!-- equine-pwa -->"
_ASSETS = Path(__file__).resolve().parent.parent / "assets"

_HEAD = """{marker}
<link rel="apple-touch-icon" href="./app_icon_180.png">
<link rel="icon" type="image/png" href="./app_icon_180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="馬開腹判断支援">
"""


def _static_dir() -> Path | None:
    try:
        import streamlit as _s
        return Path(_s.__file__).resolve().parent / "static"
    except Exception:
        return None


@st.cache_resource
def enable() -> bool:
    """index.html にPWAメタを1度だけ注入し、アイコンを配置する。"""
    static = _static_dir()
    if static is None:
        return False
    index = static / "index.html"
    try:
        # アイコンを static にコピー（href から参照可能にする）
        for name in ("app_icon_180.png", "app_icon_512.png"):
            src = _ASSETS / name
            if src.exists():
                shutil.copyfile(src, static / name)

        html = index.read_text(encoding="utf-8")
        if _MARKER in html:
            return True  # 既に注入済み
        if "<head>" in html:
            html = html.replace("<head>", "<head>\n" + _HEAD.format(marker=_MARKER), 1)
            index.write_text(html, encoding="utf-8")
            return True
    except Exception:
        return False
    return False
