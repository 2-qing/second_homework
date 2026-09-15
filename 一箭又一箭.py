import pygame
import sys
import math

# 初始化
pygame.init()

# 屏幕设置
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("一箭又一箭")

# 颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
BLUE = (70, 130, 180)
GREEN = (60, 179, 113)
RED = (220, 20, 60)
YELLOW = (255, 215, 0)
BG_COLOR = (30, 30, 40)
GRID_COLOR = (60, 60, 70)
ARROW_COLOR = (255, 255, 255)
ARROW_BLOCKED_COLOR = (255, 100, 100)

# 字体（尝试使用中文字体，若失败则回退）
try:
    font_small = pygame.font.SysFont("simhei", 20)
    font_medium = pygame.font.SysFont("simhei", 28)
    font_large = pygame.font.SysFont("simhei", 48)
    font_title = pygame.font.SysFont("simhei", 64)
except:
    font_small = pygame.font.SysFont("arial", 20)
    font_medium = pygame.font.SysFont("arial", 28)
    font_large = pygame.font.SysFont("arial", 48)
    font_title = pygame.font.SysFont("arial", 64)

# 方向向量
DIRS = {
    'up': (0, -1),
    'down': (0, 1),
    'left': (-1, 0),
    'right': (1, 0)
}

# 关卡数据（每个关卡都经过手工验证可通关）
LEVELS = [
    {
        'name': '第 1 关',
        'grid_size': 5,
        'mistakes': 3,
        'arrows': [
            (0,4,'right'), (0,3,'right'), (0,2,'right'),
            (4,0,'left'), (4,1,'left'), (4,2,'left'),
            (2,0,'up'), (3,0,'up')
        ]
    },
    {
        'name': '第 2 关',
        'grid_size': 5,
        'mistakes': 3,
        'arrows': [
            (0,4,'right'), (0,3,'right'), (0,2,'right'), (0,1,'right'),
            (4,0,'left'), (4,1,'left'), (4,2,'left'), (4,3,'left'),
            (2,0,'up'), (2,1,'up'), (2,2,'up'), (2,3,'up'), (2,4,'up')
        ]
    },
    {
        'name': '第 3 关',
        'grid_size': 6,
        'mistakes': 4,
        'arrows': [
            (0,5,'right'), (0,4,'right'), (0,3,'right'), (0,2,'right'),
            (5,0,'left'), (5,1,'left'), (5,2,'left'), (5,3,'left'),
            (1,0,'down'), (2,0,'down'), (3,0,'down'),
            (4,5,'up'), (3,5,'up'), (2,5,'up'), (1,5,'up'),
            (2,2,'right'), (2,3,'right'), (3,2,'left'), (3,3,'left')
        ]
    }
]

class Button:
    def __init__(self, x, y, w, h, text, color=BLUE, text_color=WHITE, callback=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.callback = callback
        self.hovered = False

    def draw(self, surface):
        color = self.color
        if self.hovered:
            color = tuple(min(255, c + 30) for c in color)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=8)
        text_surf = font_medium.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def update_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class Arrow:
    def __init__(self, row, col, direction, grid_size, board_rect):
        self.row = row
        self.col = col
        self.direction = direction
        self.grid_size = grid_size
        self.board_rect = board_rect
        self.state = 'idle'  # idle, flying, shaking
        self.anim_offset = [0, 0]
        self.shake_timer = 0
        self.fly_speed = 15
        self.update_pixel_pos()

    def update_pixel_pos(self):
        cell_size = self.board_rect.width // self.grid_size
        self.pixel_x = self.board_rect.x + self.col * cell_size + cell_size // 2
        self.pixel_y = self.board_rect.y + self.row * cell_size + cell_size // 2
        self.cell_size = cell_size

    def draw(self, surface):
        x = self.pixel_x + self.anim_offset[0]
        y = self.pixel_y + self.anim_offset[1]
        size = self.cell_size * 0.35
        color = ARROW_COLOR
        if self.state == 'shaking':
            color = ARROW_BLOCKED_COLOR

        if self.direction == 'right':
            points = [(x - size, y - size), (x + size, y), (x - size, y + size)]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.line(surface, color, (x - size, y), (x + size, y), 4)
        elif self.direction == 'left':
            points = [(x + size, y - size), (x - size, y), (x + size, y + size)]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.line(surface, color, (x + size, y), (x - size, y), 4)
        elif self.direction == 'up':
            points = [(x - size, y + size), (x, y - size), (x + size, y + size)]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.line(surface, color, (x, y + size), (x, y - size), 4)
        elif self.direction == 'down':
            points = [(x - size, y - size), (x, y + size), (x + size, y - size)]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.line(surface, color, (x, y - size), (x, y + size), 4)

    def update(self, dt):
        if self.state == 'flying':
            dx, dy = DIRS[self.direction]
            self.pixel_x += dx * self.fly_speed
            self.pixel_y += dy * self.fly_speed
            if (self.pixel_x < -100 or self.pixel_x > SCREEN_WIDTH + 100 or
                self.pixel_y < -100 or self.pixel_y > SCREEN_HEIGHT + 100):
                return False
        elif self.state == 'shaking':
            self.shake_timer -= dt
            if self.shake_timer <= 0:
                self.state = 'idle'
                self.anim_offset = [0, 0]
            else:
                offset = math.sin(self.shake_timer * 50) * 8
                self.anim_offset[0] = offset
                self.anim_offset[1] = offset * 0.5
        return True

class Game:
    def __init__(self):
        self.state = 'start'  # start, playing, win, lose
        self.current_level_index = 0
        self.arrows = []
        self.mistakes_left = 0
        self.total_mistakes = 0
        self.grid_size = 5
        self.board_rect = pygame.Rect(0, 0, 0, 0)
        self.buttons = []
        self.level_complete = False
        self.message = ""
        self.message_timer = 0
        self.init_level(0)
        self.create_start_buttons()

    def create_start_buttons(self):
        self.buttons = []
        btn_start = Button(SCREEN_WIDTH//2 - 100, 400, 200, 60, "开始游戏", GREEN, callback=self.start_game)
        self.buttons.append(btn_start)

    def create_game_buttons(self):
        self.buttons = []
        btn_restart = Button(SCREEN_WIDTH - 160, 20, 140, 40, "重新开始", BLUE, callback=self.restart_level)
        self.buttons.append(btn_restart)

    def create_win_buttons(self):
        self.buttons = []
        if self.current_level_index < len(LEVELS) - 1:
            btn_next = Button(SCREEN_WIDTH//2 - 100, 450, 200, 60, "下一关", GREEN, callback=self.next_level)
            self.buttons.append(btn_next)
        else:
            btn_restart = Button(SCREEN_WIDTH//2 - 100, 450, 200, 60, "再玩一次", GREEN, callback=self.start_game)
            self.buttons.append(btn_restart)
        btn_menu = Button(SCREEN_WIDTH//2 - 100, 530, 200, 60, "返回主菜单", BLUE, callback=self.go_to_menu)
        self.buttons.append(btn_menu)

    def create_lose_buttons(self):
        self.buttons = []
        btn_restart = Button(SCREEN_WIDTH//2 - 100, 450, 200, 60, "重新开始", GREEN, callback=self.restart_level)
        self.buttons.append(btn_restart)
        btn_menu = Button(SCREEN_WIDTH//2 - 100, 530, 200, 60, "返回主菜单", BLUE, callback=self.go_to_menu)
        self.buttons.append(btn_menu)

    def start_game(self):
        self.current_level_index = 0
        self.init_level(0)
        self.state = 'playing'
        self.create_game_buttons()

    def go_to_menu(self):
        self.state = 'start'
        self.create_start_buttons()

    def init_level(self, index):
        self.current_level_index = index
        level = LEVELS[index]
        self.grid_size = level['grid_size']
        self.mistakes_left = level['mistakes']
        self.total_mistakes = level['mistakes']
        self.arrows = []
        board_size = min(SCREEN_WIDTH - 100, SCREEN_HEIGHT - 200)
        cell_size = board_size // self.grid_size
        board_size = cell_size * self.grid_size
        board_x = (SCREEN_WIDTH - board_size) // 2
        board_y = (SCREEN_HEIGHT - board_size) // 2 + 30
        self.board_rect = pygame.Rect(board_x, board_y, board_size, board_size)
        for (r, c, d) in level['arrows']:
            self.arrows.append(Arrow(r, c, d, self.grid_size, self.board_rect))
        self.level_complete = False
        self.message = ""
        self.message_timer = 0

    def restart_level(self):
        self.init_level(self.current_level_index)
        self.state = 'playing'
        self.create_game_buttons()

    def next_level(self):
        if self.current_level_index < len(LEVELS) - 1:
            self.current_level_index += 1
            self.init_level(self.current_level_index)
            self.state = 'playing'
            self.create_game_buttons()

    def can_fly(self, arrow):
        r, c, d = arrow.row, arrow.col, arrow.direction
        for other in self.arrows:
            if other is arrow or other.state == 'flying':
                continue
            if d == 'right' and other.row == r and other.col > c:
                return False
            elif d == 'left' and other.row == r and other.col < c:
                return False
            elif d == 'up' and other.col == c and other.row < r:
                return False
            elif d == 'down' and other.col == c and other.row > r:
                return False
        return True

    def handle_click(self, pos):
        if self.state != 'playing':
            return
        for btn in self.buttons:
            if btn.is_clicked(pos):
                if btn.callback:
                    btn.callback()
                return
        for arrow in self.arrows:
            if arrow.state != 'idle':
                continue
            dx = pos[0] - arrow.pixel_x
            dy = pos[1] - arrow.pixel_y
            if abs(dx) < arrow.cell_size * 0.4 and abs(dy) < arrow.cell_size * 0.4:
                if self.can_fly(arrow):
                    arrow.state = 'flying'
                else:
                    arrow.state = 'shaking'
                    arrow.shake_timer = 0.3
                    self.mistakes_left -= 1
                    self.message = "碰撞！失误 -1"
                    self.message_timer = 1.0
                    if self.mistakes_left <= 0:
                        self.state = 'lose'
                        self.create_lose_buttons()
                return

    def update(self, dt):
        if self.state == 'playing':
            for arrow in self.arrows[:]:
                if not arrow.update(dt):
                    self.arrows.remove(arrow)
            if len(self.arrows) == 0 and not self.level_complete:
                self.level_complete = True
                self.state = 'win'
                self.create_win_buttons()
            if self.message_timer > 0:
                self.message_timer -= dt
                if self.message_timer <= 0:
                    self.message = ""

    def draw(self, surface):
        surface.fill(BG_COLOR)
        if self.state == 'start':
            self.draw_start(surface)
        elif self.state == 'playing':
            self.draw_game(surface)
        elif self.state == 'win':
            self.draw_win(surface)
        elif self.state == 'lose':
            self.draw_lose(surface)

    def draw_start(self, surface):
        title = font_title.render("一箭又一箭", True, YELLOW)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 200))
        surface.blit(title, title_rect)
        subtitle = font_medium.render("点击箭头，让它飞出棋盘！", True, WHITE)
        sub_rect = subtitle.get_rect(center=(SCREEN_WIDTH//2, 300))
        surface.blit(subtitle, sub_rect)
        for btn in self.buttons:
            btn.draw(surface)

    def draw_game(self, surface):
        level = LEVELS[self.current_level_index]
        info_text = font_medium.render(f"{level['name']}  剩余箭头: {len(self.arrows)}  失误次数: {self.mistakes_left}", True, WHITE)
        surface.blit(info_text, (30, 30))
        pygame.draw.rect(surface, GRID_COLOR, self.board_rect, border_radius=10)
        cell_size = self.board_rect.width // self.grid_size
        for i in range(self.grid_size + 1):
            x = self.board_rect.x + i * cell_size
            y = self.board_rect.y + i * cell_size
            pygame.draw.line(surface, DARK_GRAY, (x, self.board_rect.y), (x, self.board_rect.bottom), 2)
            pygame.draw.line(surface, DARK_GRAY, (self.board_rect.x, y), (self.board_rect.right, y), 2)
        for arrow in self.arrows:
            arrow.draw(surface)
        if self.message_timer > 0:
            msg = font_medium.render(self.message, True, RED)
            msg_rect = msg.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 50))
            surface.blit(msg, msg_rect)
        for btn in self.buttons:
            btn.draw(surface)

    def draw_win(self, surface):
        text = font_large.render("通关！", True, GREEN)
        text_rect = text.get_rect(center=(SCREEN_WIDTH//2, 250))
        surface.blit(text, text_rect)
        for btn in self.buttons:
            btn.draw(surface)

    def draw_lose(self, surface):
        text = font_large.render("失败！", True, RED)
        text_rect = text.get_rect(center=(SCREEN_WIDTH//2, 250))
        surface.blit(text, text_rect)
        for btn in self.buttons:
            btn.draw(surface)

def main():
    clock = pygame.time.Clock()
    game = Game()
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game.state == 'playing':
                    game.handle_click(event.pos)
                else:
                    for btn in game.buttons:
                        if btn.is_clicked(event.pos):
                            if btn.callback:
                                btn.callback()
                            break
            elif event.type == pygame.MOUSEMOTION:
                for btn in game.buttons:
                    btn.update_hover(event.pos)
        game.update(dt)
        game.draw(screen)
        pygame.display.flip()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()