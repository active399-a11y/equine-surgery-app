"""pytest 共通設定。

プロジェクトルートを sys.path に入れ、`surgery_app` パッケージを
どこから pytest を起動しても import できるようにする。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
