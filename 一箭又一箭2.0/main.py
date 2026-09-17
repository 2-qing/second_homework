# -*- coding: utf-8 -*-
"""一箭又一箭：主程序与 pygame 界面。

运行方式：
    pip install -r requirements.txt
    python main.py
"""
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import sys
from functools import partial

import pygame

from game_logic import GameState
from levels import LEVELS
from settings import (
    SCREEN_W,
    SCREEN_H,
    FPS,
    WHITE,
    BLACK,
    GRAY,
    DARK_GRAY,
    BLUE,
    GREEN,
    RED,
    YELLOW,
    BG_COLOR,
    PANEL_COLOR,
    PANEL_LIGHT,
    GRID_COLOR,
    OVERLAY_COLOR,
)
from ui import ArrowSprite, BoardLayout, Button, FlyingArrow, load_font


def make_layout(grid_size: int) -> BoardLayout:
    max_w = SCREEN_W - 160
    max_h = SCREEN_H - 238
    cell = min(96, max_w // grid_size, max_h // grid_size)
    size = cell * grid_size
    x = (SCREEN_W - size) // 2
    y = 128 + (max_h - size) // 2
    return BoardLayout(pygame.Rect(x, y, size, size), grid_size)


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("一箭又一箭")

        # 关键：关闭输入法文本输入，否则中文输入法会截获 H / Z 等字母键
        try:
            pygame.key.stop_text_input()
        except AttributeError:
            pass

        self._hotkey_prev = {pygame.K_h: False, pygame.K_z: False}
        self._hotkey_last = {pygame.K_h: -1000, pygame.K_z: -1000}
        self.clock = pygame.time.Clock()

        self.fonts = {
            "tiny": load_font(18),
            "small": load_font(22),
            "medium": load_font(28),
            "large": load_font(48),
            "title": load_font(72),
            "button": load_font(26),
        }

        self.logic = GameState(LEVELS)
        self.state = "start"          # start / playing / win / lose
        self.selecting_level = False
        self.buttons = []

        self.layout: BoardLayout = make_layout(self.logic.level.grid_size)
        self.sprites = {}
        self.effects = []
        self.hover_cell = None
        self.message = ""
        self.message_timer = 0.0
        self.transition_timer = 0.0
        self.transition_kind = None   # win / lose
        self.running = True

        self._reset_view()
        self._build_start_buttons()

    # ---------- 状态切换 ----------
    def _reset_view(self) -> None:
        self.layout = make_layout(self.logic.level.grid_size)
        self.sprites = {
            (a.row, a.col): ArrowSprite(a, self.layout)
            for a in self.logic.board.arrows
        }
        self.effects.clear()
        self.hover_cell = None
        self.message = ""
        self.message_timer = 0.0
        self.transition_timer = 0.0
        self.transition_kind = None

    def _rebuild_sprites(self) -> None:
        self.sprites = {
            (a.row, a.col): ArrowSprite(a, self.layout)
            for a in self.logic.board.arrows
        }
        self.effects.clear()
        self.hover_cell = None

    def start_new_game(self) -> None:
        self.logic.level_index = 0
        self.logic.reset()
        self.state = "playing"
        self._reset_view()
        self._build_game_buttons()

    def start_level(self, index: int) -> None:
        self.logic.level_index = index
        self.logic.reset()
        self.state = "playing"
        self._reset_view()
        self._build_game_buttons()

    def restart_level(self) -> None:
        self.logic.reset()
        self.state = "playing"
        self._reset_view()
        self._build_game_buttons()

    def next_level(self) -> None:
        if self.logic.next_level():
            self.state = "playing"
            self._reset_view()
            self._build_game_buttons()
        else:
            self.start_new_game()

    def go_menu(self) -> None:
        self.state = "start"
        self.selecting_level = False
        self._build_start_buttons()

    def quit_game(self) -> None:
        self.running = False

    def _toggle_level_select(self) -> None:
        self.selecting_level = not self.selecting_level
        self._build_start_buttons()

    # ---------- 按钮 ----------
    def _build_start_buttons(self) -> None:
        self.buttons = []
        if self.selecting_level:
            count = len(LEVELS)
            per_row = 3
            bw, bh, gap = 150, 54, 18
            total_w = per_row * bw + (per_row - 1) * gap
            start_x = (SCREEN_W - total_w) // 2
            start_y = 390
            for i in range(count):
                row, col = divmod(i, per_row)
                rect = (start_x + col * (bw + gap),
                        start_y + row * (bh + gap), bw, bh)
                self.buttons.append(
                    Button(rect, f"第 {i + 1} 关",
                           partial(self.start_level, i), color=BLUE)
                )
            rows = (count + per_row - 1) // per_row
            back_y = start_y + rows * (bh + gap) + 6
            self.buttons.append(
                Button((SCREEN_W // 2 - 90, back_y, 180, 50),
                       "返回", self._toggle_level_select, color=DARK_GRAY)
            )
        else:
            self.buttons = [
                Button((SCREEN_W // 2 - 120, 390, 240, 58),
                       "开始游戏", self.start_new_game, color=GREEN),
                Button((SCREEN_W // 2 - 120, 462, 240, 58),
                       "选择关卡", self._toggle_level_select, color=BLUE),
                Button((SCREEN_W // 2 - 120, 534, 240, 58),
                       "退出游戏", self.quit_game, color=DARK_GRAY),
            ]

    def _build_game_buttons(self) -> None:
        self.buttons = [
            Button((SCREEN_W - 150, 26, 124, 44),
                   "重新开始", self.restart_level, color=BLUE),
            Button((SCREEN_W // 2 - 195, SCREEN_H - 60, 120, 44),
                   "提示 H", self.do_hint, color=PANEL_LIGHT),
            Button((SCREEN_W // 2 - 60, SCREEN_H - 60, 120, 44),
                   "撤销 Z", self.do_undo, color=PANEL_LIGHT),
            Button((SCREEN_W // 2 + 75, SCREEN_H - 60, 120, 44),
                   "主菜单", self.go_menu, color=PANEL_LIGHT),
        ]

    def _build_win_buttons(self) -> None:
        self.buttons = []
        if self.logic.is_last_level:
            self.buttons.append(
                Button((SCREEN_W // 2 - 130, 430, 260, 58),
                       "再玩一次", self.start_new_game, color=GREEN)
            )
        else:
            self.buttons.append(
                Button((SCREEN_W // 2 - 130, 430, 260, 58),
                       "下一关", self.next_level, color=GREEN)
            )
        self.buttons.append(
            Button((SCREEN_W // 2 - 130, 505, 260, 58),
                   "返回主菜单", self.go_menu, color=BLUE)
        )

    def _build_lose_buttons(self) -> None:
        self.buttons = [
            Button((SCREEN_W // 2 - 130, 430, 260, 58),
                   "重新开始", self.restart_level, color=GREEN),
            Button((SCREEN_W // 2 - 130, 505, 260, 58),
                   "返回主菜单", self.go_menu, color=BLUE),
        ]

    # ---------- 输入 ----------
    def handle_motion(self, pos) -> None:
        for button in self.buttons:
            button.update_hover(pos)
        if self.state == "playing" and self.transition_timer <= 0:
            self.hover_cell = self.layout.cell_at(pos)
        else:
            self.hover_cell = None

    def handle_click(self, pos) -> None:
        for button in self.buttons:
            if button.is_clicked(pos):
                button.invoke()
                return

        if self.state != "playing" or self.transition_timer > 0:
            return

        cell = self.layout.cell_at(pos)
        if cell is None:
            return

        sprite = self.sprites.get(cell)
        # 正在播放碰撞/提示动画的箭头不接受点击，避免连续扣失误
        if sprite is not None and sprite.state != "idle":
            return

        row, col = cell
        result = self.logic.click(row, col)

        if result.kind == "flew":
            sprite = self.sprites.pop(cell, None)
            if sprite is not None:
                self.effects.append(
                    FlyingArrow(result.arrow, sprite.cx, sprite.cy, self.layout.cell)
                )
            if self.logic.status == "win":
                self.transition_kind = "win"
                self.transition_timer = 0.9

        elif result.kind == "blocked":
            if sprite is not None:
                sprite.start_bump()
            self.message = f"被挡住了！剩余失误：{self.logic.mistakes_left}"
            self.message_timer = 1.2
            if self.logic.status == "lose":
                self.transition_kind = "lose"
                self.transition_timer = 0.85

    def do_hint(self) -> None:
        if self.state != "playing" or self.transition_timer > 0:
            return
        arrow = self.logic.hint()
        if arrow is None:
            self.message = "当前没有可以飞出的箭头"
        else:
            sprite = self.sprites.get((arrow.row, arrow.col))
            if sprite is not None:
                sprite.show_hint()
            self.message = "提示：高亮箭头现在可以飞出"
        self.message_timer = 1.4

    def do_undo(self) -> None:
        if self.state != "playing" or self.transition_timer > 0:
            return
        if self.logic.undo():
            self._rebuild_sprites()
            self.message = "已撤销上一步"
        else:
            self.message = "没有可以撤销的操作"
        self.message_timer = 1.2

    def handle_key(self, event) -> None:
        """同时兼容 event.key 和 event.unicode，防止键盘布局差异。"""
        key = event.key
        text = (event.unicode or "").lower()

        if key == pygame.K_ESCAPE:
            if self.state != "start":
                self.go_menu()
        elif (key == pygame.K_h or text == "h") and self.state == "playing":
            self._trigger_hotkey(pygame.K_h, self.do_hint)
        elif (key == pygame.K_z or text == "z") and self.state == "playing":
            self._trigger_hotkey(pygame.K_z, self.do_undo)
        elif key == pygame.K_r and self.state in ("playing", "win", "lose"):
            self.restart_level()
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            if self.state == "start" and not self.selecting_level:
                self.start_new_game()
            elif self.state == "win":
                if self.logic.is_last_level:
                    self.start_new_game()
                else:
                    self.next_level()
            elif self.state == "lose":
                self.restart_level()

    def _handle_text_input(self, text: str) -> None:
        """TEXTINPUT 兜底：某些输入法环境下 KEYDOWN 可能被吞掉。"""
        text = text.lower()
        if self.state != "playing":
            return
        if text == "h":
            self._trigger_hotkey(pygame.K_h, self.do_hint)
        elif text == "z":
            self._trigger_hotkey(pygame.K_z, self.do_undo)

    def _trigger_hotkey(self, key: int, action) -> None:
        """防止 KEYDOWN 和轮询在同一帧触发两次。"""
        now = pygame.time.get_ticks()
        if now - self._hotkey_last.get(key, -1000) < 120:
            return
        self._hotkey_last[key] = now
        action()

    def _poll_hotkeys(self) -> None:
        """备用方案：不依赖 KEYDOWN 事件，轮询物理键盘状态。"""
        keys = pygame.key.get_pressed()
        for key, action in ((pygame.K_h, self.do_hint), (pygame.K_z, self.do_undo)):
            pressed = keys[key]
            was_pressed = self._hotkey_prev.get(key, False)
            if pressed and not was_pressed and self.state == "playing":
                self._trigger_hotkey(key, action)
            self._hotkey_prev[key] = pressed

    # ---------- 更新 ----------
    def update(self, dt: float) -> None:
        self._poll_hotkeys()

        for sprite in self.sprites.values():
            sprite.update(dt)

        for effect in self.effects[:]:
            if not effect.update(dt):
                self.effects.remove(effect)

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

        if self.transition_timer > 0:
            self.transition_timer -= dt
            if self.transition_timer <= 0:
                if self.transition_kind == "win":
                    self.state = "win"
                    self._build_win_buttons()
                elif self.transition_kind == "lose":
                    self.state = "lose"
                    self._build_lose_buttons()
                self.transition_kind = None

    # ---------- 绘制 ----------
    def draw(self) -> None:
        self.screen.fill(BG_COLOR)
        if self.state == "start":
            self._draw_start()
        else:
            self._draw_scene(include_game_buttons=(self.state == "playing"))
            if self.state == "win":
                self._draw_result_overlay(True)
            elif self.state == "lose":
                self._draw_result_overlay(False)

    def _draw_start(self) -> None:
        title = self.fonts["title"].render("一箭又一箭", True, YELLOW)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 150)))

        subtitle = self.fonts["medium"].render(
            "点击箭头，让它沿方向飞出棋盘", True, WHITE
        )
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_W // 2, 225)))

        if self.selecting_level:
            tip = self.fonts["medium"].render("选择关卡", True, WHITE)
            self.screen.blit(tip, tip.get_rect(center=(SCREEN_W // 2, 320)))
        else:
            lines = [
                "规则：点击箭头后，检查它前方是否还有其他箭头。",
                "前方无阻挡：箭头飞出并消除；有阻挡：碰撞，失误 -1。",
                "清空全部箭头即可进入下一关，失误耗尽则本关失败。",
            ]
            for i, line in enumerate(lines):
                text = self.fonts["small"].render(line, True, GRAY)
                self.screen.blit(text, text.get_rect(center=(SCREEN_W // 2, 300 + i * 32)))

        for button in self.buttons:
            button.draw(self.screen, self.fonts["button"])

        footer = self.fonts["tiny"].render(
            "Pygame 课程设计 · 支持鼠标点击 / 键盘 H Z R Esc", True, DARK_GRAY
        )
        self.screen.blit(footer, footer.get_rect(center=(SCREEN_W // 2, SCREEN_H - 28)))

    def _draw_scene(self, include_game_buttons: bool) -> None:
        self._draw_hud()
        self._draw_board()
        if include_game_buttons:
            for button in self.buttons:
                button.draw(self.screen, self.fonts["button"])

    def _draw_hud(self) -> None:
        pygame.draw.rect(self.screen, PANEL_COLOR, (0, 0, SCREEN_W, 112))
        pygame.draw.line(self.screen, GRID_COLOR, (0, 112), (SCREEN_W, 112), 2)

        level = self.logic.level
        self.screen.blit(
            self.fonts["medium"].render(level.name, True, WHITE), (28, 24)
        )
        self.screen.blit(
            self.fonts["small"].render(
                f"剩余箭头：{self.logic.board.remaining}", True, GRAY
            ),
            (28, 68),
        )
        self.screen.blit(
            self.fonts["small"].render(
                f"失误次数：{self.logic.mistakes_left} / {self.logic.mistakes_total}",
                True,
                GRAY,
            ),
            (240, 68),
        )
        self.screen.blit(
            self.fonts["tiny"].render(
                "H 提示    Z 撤销    R 重新开始    Esc 菜单", True, DARK_GRAY
            ),
            (455, 72),
        )

    def _draw_board(self) -> None:
        layout = self.layout
        pygame.draw.rect(self.screen, PANEL_COLOR, layout.rect, border_radius=14)
        pygame.draw.rect(self.screen, GRID_COLOR, layout.rect, 2, border_radius=14)

        cell = layout.cell
        for i in range(layout.grid_size + 1):
            x = layout.rect.x + i * cell
            y = layout.rect.y + i * cell
            pygame.draw.line(
                self.screen, GRID_COLOR,
                (x, layout.rect.y), (x, layout.rect.bottom), 1
            )
            pygame.draw.line(
                self.screen, GRID_COLOR,
                (layout.rect.x, y), (layout.rect.right, y), 1
            )

        if self.hover_cell is not None and self.hover_cell in self.sprites:
            rect = layout.cell_rect(*self.hover_cell)
            glow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            glow.fill((255, 255, 255, 22))
            self.screen.blit(glow, (rect.x, rect.y))

        for sprite in self.sprites.values():
            sprite.draw(self.screen)
        for effect in self.effects:
            effect.draw(self.screen)

        if self.message_timer > 0:
            message = self.fonts["small"].render(self.message, True, YELLOW)
            self.screen.blit(
                message,
                message.get_rect(center=(SCREEN_W // 2, layout.rect.bottom + 22)),
            )

    def _draw_result_overlay(self, win: bool) -> None:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))

        if win:
            title_text = "全部通关！" if self.logic.is_last_level else "本关通关！"
            title_color = GREEN
            sub_text = "你已清除当前关卡的全部箭头"
        else:
            title_text = "挑战失败"
            title_color = RED
            sub_text = f"失误次数已用完，来再试一次吧"

        title = self.fonts["large"].render(title_text, True, title_color)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 235)))

        sub = self.fonts["medium"].render(
            f"{self.logic.level.name} · {sub_text}", True, WHITE
        )
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, 315)))

        tip = self.fonts["small"].render(
            "点击按钮继续，或按空格键", True, GRAY
        )
        self.screen.blit(tip, tip.get_rect(center=(SCREEN_W // 2, 365)))

        for button in self.buttons:
            button.draw(self.screen, self.fonts["button"])

    # ---------- 主循环 ----------
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_motion(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
                elif event.type == pygame.TEXTINPUT:
                    self._handle_text_input(event.text)
                elif event.type == pygame.KEYUP:
                    if event.key in self._hotkey_prev:
                        self._hotkey_prev[event.key] = False

            self.update(dt)
            self.draw()
            pygame.display.flip()


def main() -> int:
    try:
        app = App()
        app.run()
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
