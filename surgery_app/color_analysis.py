"""漿膜・粘膜の色を客観的に数値化するモジュール。

文献上、腸管生存性の視覚的評価（「黒っぽい/ピンク」という主観）は
最も簡便だが最も不正確とされる。本モジュールは、撮影画像の指定領域
(ROI: Region Of Interest) の色を RGB / HSV で数値化し、主観のばらつきを
減らすことを目的とする。これは診断ではなく「客観的な記録」のための道具。

OpenCV は使わず Pillow + NumPy のみで実装している。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
from PIL import Image, ImageDraw


@dataclass
class ColorMetrics:
    """ROI（指定領域）の色指標。すべて参考値であり診断値ではない。"""

    # 平均 RGB（0-255）
    r: float
    g: float
    b: float
    # 平均 HSV（H:0-360, S:0-100, V:0-100）
    h: float
    s: float
    v: float
    # 赤み指標 = R -(G+B)/2。漿膜のピンク/赤の強さの目安（高いほど赤い）
    redness: float
    # 暗さ指標 = 255 - V換算(0-255)。壊死域は暗くなる傾向（高いほど暗い）
    darkness: float
    # ROI内の画素数（サンプルの信頼性の目安）
    pixel_count: int

    def to_dict(self) -> dict:
        return asdict(self)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_roi(
    cx_pct: float,
    cy_pct: float,
    size_pct: float,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    """中心座標(%)とサイズ(%)から、画素単位の矩形 (left, top, right, bottom) を返す。

    パーセント指定にすることで、画像の解像度が変わっても同じ相対位置を指せる。
    """
    cx = cx_pct / 100.0 * width
    cy = cy_pct / 100.0 * height
    # size_pct は短辺に対する一辺の割合
    half = size_pct / 100.0 * min(width, height) / 2.0

    left = int(_clamp(cx - half, 0, width - 1))
    top = int(_clamp(cy - half, 0, height - 1))
    right = int(_clamp(cx + half, left + 1, width))
    bottom = int(_clamp(cy + half, top + 1, height))
    return left, top, right, bottom


def _rgb_to_hsv_array(rgb: np.ndarray) -> np.ndarray:
    """(N,3) の RGB(0-255) を HSV(H:0-360, S:0-100, V:0-100) に変換する。"""
    arr = rgb.astype(np.float64) / 255.0
    r, g, b = arr[:, 0], arr[:, 1], arr[:, 2]
    mx = np.max(arr, axis=1)
    mn = np.min(arr, axis=1)
    diff = mx - mn

    # 色相 H
    h = np.zeros_like(mx)
    mask = diff > 1e-9
    # 最大成分ごとに計算
    r_max = (mx == r) & mask
    g_max = (mx == g) & mask
    b_max = (mx == b) & mask
    h[r_max] = ((g[r_max] - b[r_max]) / diff[r_max]) % 6
    h[g_max] = ((b[g_max] - r[g_max]) / diff[g_max]) + 2
    h[b_max] = ((r[b_max] - g[b_max]) / diff[b_max]) + 4
    h = h * 60.0

    # 彩度 S, 明度 V
    s = np.zeros_like(mx)
    s[mx > 1e-9] = diff[mx > 1e-9] / mx[mx > 1e-9]
    v = mx

    return np.stack([h, s * 100.0, v * 100.0], axis=1)


def analyze_roi(image: Image.Image, roi: tuple[int, int, int, int]) -> ColorMetrics:
    """画像の ROI 内の色を解析して ColorMetrics を返す。"""
    rgb_image = image.convert("RGB")
    left, top, right, bottom = roi
    crop = rgb_image.crop((left, top, right, bottom))
    pixels = np.asarray(crop).reshape(-1, 3).astype(np.float64)

    if pixels.size == 0:
        return ColorMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)

    mean_rgb = pixels.mean(axis=0)
    hsv = _rgb_to_hsv_array(pixels)
    mean_hsv = hsv.mean(axis=0)

    redness = float(mean_rgb[0] - (mean_rgb[1] + mean_rgb[2]) / 2.0)
    darkness = float(255.0 - mean_hsv[2] / 100.0 * 255.0)

    return ColorMetrics(
        r=float(mean_rgb[0]),
        g=float(mean_rgb[1]),
        b=float(mean_rgb[2]),
        h=float(mean_hsv[0]),
        s=float(mean_hsv[1]),
        v=float(mean_hsv[2]),
        redness=redness,
        darkness=darkness,
        pixel_count=int(pixels.shape[0]),
    )


def draw_roi_overlay(
    image: Image.Image,
    roi: tuple[int, int, int, int],
    color: tuple[int, int, int] = (0, 200, 255),
) -> Image.Image:
    """ROIの矩形を画像に重ねて描画した新しい画像を返す（プレビュー用）。"""
    preview = image.convert("RGB").copy()
    draw = ImageDraw.Draw(preview)
    left, top, right, bottom = roi
    # 画像サイズに応じて線幅を調整
    line_width = max(2, int(min(preview.size) * 0.005))
    draw.rectangle([left, top, right, bottom], outline=color, width=line_width)
    return preview


def viability_hint(
    metrics: ColorMetrics,
    value_threshold: float = 70.0,
    saturation_threshold: float = 60.0,
) -> tuple[str, str]:
    """色レンジから3段階の参考ヒントを返す（(ラベル, レベル)）。

    レベルは ok/warn/alert。閾値は「正解」が存在しないため仮の値であり、
    過去の術中写真（実際に切除した症例の色 / 温存した症例の色）で必ず調整すること。

    判定の考え方（文献的な傾向。診断ではない）:
      - 明度Vが低い   → 黒色化＝壊死の疑い
      - 彩度Sが低い   → 色あせ＝灌流低下の疑い（判定不能）
      - いずれも十分   → 生存寄り
    """
    if metrics.v < value_threshold:
        return ("壊死寄り（要注意）", "alert")
    if metrics.s < saturation_threshold:
        return ("判定不能（追加評価を）", "warn")
    return ("生存寄り", "ok")


def compare_redness(current: ColorMetrics, baseline: ColorMetrics) -> float | None:
    """基準画像(整復前など)に対する赤みの変化率(%)を返す。

    例: +30 なら「赤みが30%回復」。基準が0付近で計算不能な場合は None。
    """
    if abs(baseline.redness) < 1e-6:
        return None
    return (current.redness - baseline.redness) / abs(baseline.redness) * 100.0
