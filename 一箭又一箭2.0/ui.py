# -*- coding: utf-8 -*-
"""UI 组件：字体、按钮、棋盘布局、箭头精灵、飞出特效。"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

import pygame

from game_logic import Arrow
from settings import (
    SCREEN_W,
    SCREEN_H,
    WHITE,
    BLACK,
    GRAY,
    DARK_GRAY,
    BLUE,
    GREEN,
    RED,
    YELLOW,
    PANEL_COLOR,
    PANEL_LIGHT,
    GRID_COLOR,
    ARROW_COLOR,
    ARROW_BLOCKED_COLOR,
    ARROW_HINT_COLOR,
)

# 像素坐标方向 (x 增量, y 增量)
PIXEL_DIRS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

# 系统中文字体候选。match_font 找不到时返回 None，不会抛异常。
FONT_NAMES = (
    "microsoftyahei",
    "msyh",
    "simhei",
    "simsun",
    "notosanscjksc",
    "sourcehansanssc",
    "pingfangsc",
    "heitisc",
    "wenquanyimicrohei",
)


def load_font(size: int) -> pygame.font.Font:
    """优先加载项目自带字体，其次查找系统中文字体。"""
    bundled = Path(__file__).resolve().parent / "assets" / "fonts" / "game_font.ttf"
    if bundled.is_file():
        return pygame.font.Font(str(bundled), size)

    for name in FONT_NAMES:
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)

    print("[提示] 未找到中文字体，建议把开源中文字体放到 assets/fonts/game_font.ttf")
    return pygame.font.Font(None, size)


def _lighten(color: Tuple[int, int, int], amount: int = 30) -> Tuple[int, int, int]:
    return tuple(min(255, c + amount) for c in color)


class Button:
    def __init__(
        self,
        rect,
        text: str,
        callback: Optional[Callable[[], None]] = None,
        color: Tuple[int, int, int] = BLUE,
        text_color: Tuple[int, int, int] = WHITE,
        enabled: bool = True,
    ):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.color = color
        self.text_color = text_color
        self.enabled = enabled
        self.hovered = False

    def update_hover(self, pos) -> None:
        self.hovered = self.enabled and self.rect.collidepoint(pos)

    def is_clicked(self, pos) -> bool:
        return self.enabled and self.rect.collidepoint(pos)

    def invoke(self) -> None:
        if self.enabled and self.callback:
            self.callback()

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if not self.enabled:
            color = DARK_GRAY
            text_color = GRAY
        else:
            color = _lighten(self.color) if self.hovered else self.color
            text_color = self.text_color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=10)
        text = font.render(self.text, True, text_color)
        surface.blit(text, text.get_rect(center=self.rect.center))


@dataclass
class BoardLayout:
    """棋盘矩形和格子坐标换算。"""

    rect: pygame.Rect
    grid_size: int

    @property
    def cell(self) -> int:
        return self.rect.width // self.grid_size

    def center(self, row: int, col: int) -> Tuple[int, int]:
        cell = self.cell
        return (self.rect.x + col * cell + cell // 2,
                self.rect.y + row * cell + cell // 2)

    def cell_rect(self, row: int, col: int) -> pygame.Rect:
        cell = self.cell
        return pygame.Rect(self.rect.x + col * cell,
                           self.rect.y + row * cell,
                           cell, cell)

    def cell_at(self, pos) -> Optional[Tuple[int, int]]:
        if not self.rect.collidepoint(pos):
            return None
        cell = self.cell
        col = (pos[0] - self.rect.x) // cell
        row = (pos[1] - self.rect.y) // cell
        if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
            return int(row), int(col)
        return None


def draw_arrow(
    surface: pygame.Surface,
    cx: float,
    cy: float,
    size: float,
    direction: str,
    color: Tuple[int, int, int],
) -> None:
    """绘制一个带箭杆的箭头，size 为头尾方向的半长。"""
    dx, dy = PIXEL_DIRS[direction]
    px, py = -dy, dx  # 垂直方向

    tip = (cx + dx * size, cy + dy * size)
    base = (cx - dx * size * 0.18, cy - dy * size * 0.18)
    left = (base[0] + px * size * 0.68, base[1] + py * size * 0.68)
    right = (base[0] - px * size * 0.68, base[1] - py * size * 0.68)
    tail = (cx - dx * size * 0.95, cy - dy * size * 0.95)
    width = max(3, int(size * 0.36))

    pygame.draw.line(surface, color, tail, base, width)
    pygame.draw.polygon(surface, color, [tip, left, right])


class ArrowSprite:
    """棋盘上的箭头视觉对象，负责碰撞/提示动画。"""

    def __init__(self, arrow: Arrow, layout: BoardLayout):
        self.arrow = arrow
        self.layout = layout
        self.cx, self.cy = layout.center(arrow.row, arrow.col)
        self.cell = layout.cell
        self.size = layout.cell * 0.30

        self.state = "idle"          # idle / bumping / shaking
        self.offset = [0.0, 0.0]
        self.bump_t = 0.0
        self.bump_duration = 0.32
        self.shake_t = 0.0
        self.shake_duration = 0.28
        self.hint_t = 0.0

    def start_bump(self) -> None:
        self.state = "bumping"
        self.bump_t = 0.0

    def show_hint(self) -> None:
        self.hint_t = 1.4

    def update(self, dt: float) -> None:
        if self.hint_t > 0:
            self.hint_t = max(0.0, self.hint_t - dt)

        if self.state == "bumping":
            self.bump_t += dt
            t = min(self.bump_t / self.bump_duration, 1.0)
            if t < 0.55:
                k = math.sin(t / 0.55 * math.pi / 2)
            else:
                k = math.cos((t - 0.55) / 0.45 * math.pi / 2)
            dx, dy = PIXEL_DIRS[self.arrow.direction]
            dist = self.cell * 0.28
            self.offset = [dx * dist * k, dy * dist * k]
            if t >= 1.0:
                self.state = "shaking"
                self.shake_t = self.shake_duration
                self.offset = [0.0, 0.0]

        elif self.state == "shaking":
            self.shake_t -= dt
            if self.shake_t <= 0:
                self.state = "idle"
                self.offset = [0.0, 0.0]
            else:
                dx, dy = PIXEL_DIRS[self.arrow.direction]
                px, py = -dy, dx
                ratio = self.shake_t / self.shake_duration
                amp = math.sin((1 - ratio) * math.pi * 4) * self.cell * 0.10 * ratio
                self.offset = [px * amp, py * amp]

    def draw(self, surface: pygame.Surface) -> None:
        x = self.cx + self.offset[0]
        y = self.cy + self.offset[1]

        if self.hint_t > 0:
            glow = pygame.Surface((self.cell, self.cell), pygame.SRCALPHA)
            pygame.draw.circle(
                glow,
                (255, 208, 82, 80),
                (self.cell // 2, self.cell // 2),
                self.cell // 2 - 4,
            )
            surface.blit(glow, (x - self.cell // 2, y - self.cell // 2))

        color = ARROW_COLOR
        if self.hint_t > 0:
            color = ARROW_HINT_COLOR
        if self.state in ("bumping", "shaking"):
            color = ARROW_BLOCKED_COLOR

        # 轻微阴影，增强可读性
        draw_arrow(surface, x + 2, y + 3, self.size, self.arrow.direction, (16, 18, 28))
        draw_arrow(surface, x, y, self.size, self.arrow.direction, color)


class FlyingArrow:
    """飞出特效；逻辑棋盘上的箭头已经移除，这个是纯视觉副本。"""

    def __init__(self, arrow: Arrow, x: float, y: float, cell_size: int):
        self.arrow = arrow
        self.x = float(x)
        self.y = float(y)
        self.size = cell_size * 0.30
        self.speed = cell_size * 13.0   # 约 13 格/秒

    def update(self, dt: float) -> bool:
        dx, dy = PIXEL_DIRS[self.arrow.direction]
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
        return not (
            self.x < -140 or self.x > SCREEN_W + 140
            or self.y < -140 or self.y > SCREEN_H + 140
        )

    def draw(self, surface: pygame.Surface) -> None:
        draw_arrow(surface, self.x, self.y, self.size, self.arrow.direction, ARROW_COLOR)