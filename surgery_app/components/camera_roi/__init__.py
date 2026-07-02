"""アプリ内カメラ＋ドラッグ式ROI選択コンポーネント。

背面カメラのライブ映像＋シャッターで撮影し、撮った画像上で解析点(◇)を指で
ドラッグして決める。戻り値は撮影画像(dataURL)と解析点・枠サイズ(いずれも%)。
色解析は Python 側の既存処理を再利用する。
"""

from __future__ import annotations

import os

import streamlit.components.v1 as components

_DIR = os.path.dirname(os.path.abspath(__file__))
_component = components.declare_component(
    "equine_camera_roi", path=os.path.join(_DIR, "frontend")
)


def camera_roi_input(size_default: int = 25, key: str | None = None) -> dict | None:
    """アプリ内カメラを表示し、確定時に {image, cx, cy, size, ts} を返す。

    - image: 撮影画像の dataURL (image/jpeg)
    - cx, cy: 解析点の中心（画像に対する%）
    - size: 枠の一辺（短辺に対する%）
    """
    return _component(size_default=size_default, key=key, default=None)
