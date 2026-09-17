# -*- coding: utf-8 -*-
"""关卡数据。所有关卡都由 tools/check_levels.py 验证可通关。"""
from game_logic import Arrow, Level


def _arrows(*items) -> tuple:
    return tuple(Arrow(r, c, d) for r, c, d in items)


def _ring_arrows(grid_size: int, layers: int) -> tuple:
    """同心环关卡：外层朝外先飞出，然后内层依次解封。"""
    arrows = []
    for layer in range(layers):
        for r in range(grid_size):
            for c in range(grid_size):
                depth = min(r, c, grid_size - 1 - r, grid_size - 1 - c)
                if depth != layer:
                    continue
                if r == layer:
                    direction = "up"
                elif r == grid_size - 1 - layer:
                    direction = "down"
                elif c == layer:
                    direction = "left"
                else:
                    direction = "right"
                arrows.append(Arrow(r, c, direction))
    return tuple(arrows)


LEVELS = (
    Level("第 1 关", 5, 3, _arrows(
        (0, 4, "right"), (0, 3, "right"), (0, 2, "right"),
        (4, 0, "left"), (4, 1, "left"), (4, 2, "left"),
        (2, 0, "up"), (3, 0, "up"),
    )),
    Level("第 2 关", 5, 3, _arrows(
        (0, 4, "right"), (0, 3, "right"), (0, 2, "right"), (0, 1, "right"),
        (4, 0, "left"), (4, 1, "left"), (4, 2, "left"), (4, 3, "left"),
        (2, 0, "up"), (2, 1, "up"), (2, 2, "up"), (2, 3, "up"), (2, 4, "up"),
    )),
    Level("第 3 关", 6, 5, _arrows(
        (0, 5, "right"), (0, 4, "right"), (0, 3, "right"), (0, 2, "right"),
        (5, 0, "left"), (5, 1, "left"), (5, 2, "left"), (5, 3, "left"),
        (1, 0, "down"), (2, 0, "down"), (3, 0, "down"),
        (4, 5, "up"), (3, 5, "up"), (2, 5, "up"), (1, 5, "up"),
        (2, 2, "right"), (2, 3, "right"), (3, 2, "left"), (3, 3, "left"),
    )),
    Level("第 4 关", 6, 5, _ring_arrows(6, 2)),
    Level("第 5 关", 7, 5, _ring_arrows(7, 2)),
    Level("第 6 关", 7, 6, _ring_arrows(7, 3)),
)