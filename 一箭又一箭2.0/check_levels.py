# -*- coding: utf-8 -*-
"""关卡自检：所有关卡必须存在通关顺序。提交/修改关卡后运行一次。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game_logic import solve          # noqa: E402
from levels import LEVELS             # noqa: E402


def main() -> int:
    failed = False
    for level in LEVELS:
        order = solve(level)
        if order is None:
            failed = True
            print(f"[失败] {level.name} 无解，请调整关卡数据！")
            continue
        print(f"[通过] {level.name}：{len(level.arrows)} 个箭头，{len(order)} 步可清空")
        print("   解法：" + " -> ".join(
            f"({a.row},{a.col},{a.direction})" for a in order
        ))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())