"""手动重建一言语料库（薄封装 server.quotes.refresh_library）。

用法（项目根目录）：
    ./.venv/Scripts/python.exe scripts/update_quotes.py

拉取 hitokoto-osc/sentences-bundle 12 个分类文件（加固 https 拉取），按内置规则
（4–28 字、去重、from≤24 字）筛选，原子写 data/quotes_library.json 并热替换。
语料协议 AGPL-3.0：再分发保留 license/source 字段与协议声明。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server import quotes


def main() -> None:
    result = quotes.refresh_library(force=True)
    if result.get("ok"):
        print(f"重建完成：{result['count']} 条（updated={result['updated']}）→ {quotes.LIBRARY_DATA_PATH}")
    else:
        print(f"刷新失败：{result.get('error')}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
