"""検査値（ラボデータ）の定義。

300症例規模の研究データセット化を見据え、検査値は区分(良好/不良)ではなく
実数値で記録する。各項目は数値入力とし、未測定は空欄(None)として扱う。

結腸捻転で記録する項目（ユーザー指定）:
  Ht / 血中乳酸 / 白血球数 / 腹水中乳酸 / 血中K
小腸絞扼でも同じ全身指標を用いる。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LabField:
    key: str
    label: str
    unit: str
    min_value: float
    max_value: float
    step: float
    help: str


# 記録する検査値（この5項目のみ）
LAB_FIELDS: list[LabField] = [
    LabField("ht", "Ht（ヘマトクリット）", "%", 0.0, 90.0, 0.1,
             "脱水・循環状態の指標。"),
    LabField("blood_lactate", "血中乳酸値", "mmol/L", 0.0, 40.0, 0.1,
             "全身の組織灌流の指標。高値は予後不良の参考。"),
    LabField("wbc", "白血球数", "/µL", 0.0, 50000.0, 100.0,
             "炎症・エンドトキシン血症の参考。"),
    LabField("periton_lactate", "腹水中乳酸値", "mmol/L", 0.0, 40.0, 0.1,
             "腸管局所の障害の指標。血中乳酸との差が大きいと腸管虚血を示唆。"),
    LabField("blood_k", "血中カリウム（K）", "mEq/L", 0.0, 12.0, 0.1,
             "電解質・全身状態の参考。"),
]
