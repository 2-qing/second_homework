# -*- coding: utf-8 -*-
"""游戏核心逻辑（不依赖 pygame，可直接单元测试）。

方向统一用 (行增量, 列增量) 表示，避免和像素坐标 (dx, dy) 混淆。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

GRID_DIRS: Dict[str, Tuple[int, int]] = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}


@dataclass(frozen=True)
class Arrow:
    row: int
    col: int
    direction: str

    def __post_init__(self) -> None:
        if self.direction not in GRID_DIRS:
            raise ValueError(f"非法方向: {self.direction!r}")

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.row, self.col)


@dataclass(frozen=True)
class Level:
    name: str
    grid_size: int
    mistakes: int
    arrows: Tuple[Arrow, ...]


@dataclass(frozen=True)
class ClickResult:
    """一次点击的结果，供界面层决定播放飞出还是碰撞动画。"""

    kind: str                       # flew / blocked / empty / ignored
    arrow: Optional[Arrow] = None
    blockers: Tuple[Arrow, ...] = ()


class Board:
    """棋盘模型：负责路径检测、箭头增删。"""

    def __init__(self, grid_size: int, arrows: Iterable[Arrow]):
        if grid_size < 1:
            raise ValueError("grid_size 必须为正整数")
        self.grid_size = grid_size
        self.arrows: List[Arrow] = list(arrows)
        self.cells: Dict[Tuple[int, int], Arrow] = {}

        for arrow in self.arrows:
            r, c = arrow.pos
            if not (0 <= r < grid_size and 0 <= c < grid_size):
                raise ValueError(f"箭头越界: {arrow}")
            if arrow.pos in self.cells:
                raise ValueError(f"箭头坐标重复: {arrow.pos}")
            self.cells[arrow.pos] = arrow

    @property
    def remaining(self) -> int:
        return len(self.arrows)

    def at(self, row: int, col: int) -> Optional[Arrow]:
        return self.cells.get((row, col))

    def blockers(self, arrow: Arrow) -> List[Arrow]:
        """返回 arrow 前方、箭头与棋盘边界之间的所有箭头。"""
        dr, dc = GRID_DIRS[arrow.direction]
        r, c = arrow.row + dr, arrow.col + dc
        result: List[Arrow] = []
        n = self.grid_size
        while 0 <= r < n and 0 <= c < n:
            other = self.cells.get((r, c))
            if other is not None:
                result.append(other)
            r += dr
            c += dc
        return result

    def can_fly(self, arrow: Arrow) -> bool:
        return not self.blockers(arrow)

    def remove(self, arrow: Arrow) -> None:
        if self.cells.get(arrow.pos) is not arrow:
            raise KeyError(f"箭头不在棋盘上: {arrow}")
        self.cells.pop(arrow.pos)
        self.arrows.remove(arrow)

    def snapshot(self) -> Tuple[Arrow, ...]:
        return tuple(self.arrows)


class GameState:
    """关卡状态、失误、胜负、撤销历史。"""

    def __init__(self, levels: Iterable[Level], level_index: int = 0):
        self.levels = tuple(levels)
        if not self.levels:
            raise ValueError("至少需要一个关卡")
        self.level_index = level_index
        self.history: List[Tuple[Tuple[Arrow, ...], int]] = []
        self.undo_limit = 100
        self.reset()

    @property
    def level(self) -> Level:
        return self.levels[self.level_index]

    @property
    def is_last_level(self) -> bool:
        return self.level_index >= len(self.levels) - 1

    def reset(self) -> None:
        level = self.level
        self.board = Board(level.grid_size, level.arrows)
        self.mistakes_left = level.mistakes
        self.mistakes_total = level.mistakes
        self.status = "playing"      # playing / win / lose
        self.history.clear()

    def _push_history(self) -> None:
        self.history.append((self.board.snapshot(), self.mistakes_left))
        if len(self.history) > self.undo_limit:
            self.history.pop(0)

    def click(self, row: int, col: int) -> ClickResult:
        if self.status != "playing":
            return ClickResult("ignored")

        arrow = self.board.at(row, col)
        if arrow is None:
            return ClickResult("empty")

        self._push_history()
        blockers = self.board.blockers(arrow)
        if not blockers:
            self.board.remove(arrow)
            if self.board.remaining == 0:
                self.status = "win"
            return ClickResult("flew", arrow=arrow)

        self.mistakes_left -= 1
        if self.mistakes_left <= 0:
            self.status = "lose"
        return ClickResult("blocked", arrow=arrow, blockers=tuple(blockers))

    def undo(self) -> bool:
        if not self.history:
            return False
        arrows, mistakes = self.history.pop()
        self.board = Board(self.board.grid_size, arrows)
        self.mistakes_left = mistakes
        self.status = "playing"
        return True

    def hint(self) -> Optional[Arrow]:
        """返回一个当前可以飞出的箭头。有解关卡中必定存在。"""
        return next((a for a in self.board.arrows if self.board.can_fly(a)), None)

    def next_level(self) -> bool:
        if self.is_last_level:
            return False
        self.level_index += 1
        self.reset()
        return True


def solve(level: Level) -> Optional[List[Arrow]]:
    """贪心求解；返回点击顺序，无解返回 None。

    性质：删除箭头只会减少阻挡、不会增加阻挡。
    所以只要当前存在可飞箭头，先删它一定不会让有解变无解。
    """
    board = Board(level.grid_size, level.arrows)
    order: List[Arrow] = []
    while board.remaining:
        nxt = next((a for a in board.arrows if board.can_fly(a)), None)
        if nxt is None:
            return None
        board.remove(nxt)
        order.append(nxt)
    return order


def is_solvable(level: Level) -> bool:
    return solve(level) is not None
