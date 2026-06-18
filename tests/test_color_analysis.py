"""color_analysis モジュールのテスト。

単色画像（PIL.Image.new）で色指標が期待どおりの大小関係になるかを確認する。
診断の正確さではなく「数値化ロジックが一貫しているか」を検証する。
"""

from __future__ import annotations

from PIL import Image

from surgery_app.color_analysis import (
    analyze_roi,
    compare_redness,
    normalize_roi,
    viability_hint,
)


def _solid(rgb: tuple[int, int, int], size: int = 40) -> Image.Image:
    """指定色の単色画像を返す。"""
    return Image.new("RGB", (size, size), rgb)


def _metrics(rgb: tuple[int, int, int]):
    img = _solid(rgb)
    roi = (0, 0, img.width, img.height)
    return analyze_roi(img, roi)


def test_bright_pink_vs_dark_redness_and_darkness():
    """明るいピンクは暗い色より redness が大きく darkness が小さい。"""
    bright = _metrics((220, 120, 130))
    dark = _metrics((40, 20, 25))

    assert bright.redness > dark.redness
    assert bright.darkness < dark.darkness


def test_viability_hint_levels():
    """暗い→alert、低彩度の淡色→warn、鮮やかな赤→ok。"""
    dark = _metrics((40, 20, 25))
    pale = _metrics((180, 170, 168))
    vivid = _metrics((220, 80, 90))

    assert viability_hint(dark)[1] == "alert"
    assert viability_hint(pale)[1] == "warn"
    assert viability_hint(vivid)[1] == "ok"


def test_normalize_roi_within_image_bounds():
    """ROIは画像範囲内に収まり、left<right かつ top<bottom。"""
    width, height = 200, 150
    left, top, right, bottom = normalize_roi(50, 50, 30, width, height)

    assert 0 <= left < right <= width
    assert 0 <= top < bottom <= height


def test_normalize_roi_clamps_out_of_range_center():
    """中心が画像外でも範囲内に収まる。"""
    width, height = 200, 150
    left, top, right, bottom = normalize_roi(150, 150, 80, width, height)

    assert 0 <= left < right <= width
    assert 0 <= top < bottom <= height


def test_compare_redness_returns_none_when_baseline_zero():
    """base.redness が 0 付近のとき None を返す。"""
    # グレー（R=G=B）は redness が 0 になる
    baseline = _metrics((128, 128, 128))
    current = _metrics((220, 120, 130))

    assert abs(baseline.redness) < 1e-6
    assert compare_redness(current, baseline) is None


def test_compare_redness_returns_float_when_baseline_nonzero():
    """base.redness が非ゼロのとき変化率(float)を返す。"""
    baseline = _metrics((150, 120, 120))
    current = _metrics((220, 120, 120))

    result = compare_redness(current, baseline)
    assert isinstance(result, float)
    assert result > 0  # 赤みが増えている
