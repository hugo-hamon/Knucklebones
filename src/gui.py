import threading
import random
import time
import math
import sys

import knucklebones_rust
import pygame

from src.negamax import get_best_move
from src.utils import load_tt

# --- CONFIGURATION GRAPHIQUE ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 900

COLORS = {
    "bg_dark": (30, 33, 40),
    "bg_light": (45, 49, 59),
    "board_slot": (55, 60, 72),
    "text_main": (236, 240, 241),
    "accent": (97, 175, 239),
    "enemy": (224, 108, 117),
    "dice_bg": (245, 245, 245),
    "dice_dot": (40, 44, 52),
    "highlight": (152, 195, 121),
    "shadow": (20, 20, 25),
}

COLUMN_WIDTH = 100
COLUMN_HEIGHT = 240
MARGIN = 20


class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.02, 0.05)
        self.size = random.randint(4, 8)
        self.gravity = 0.2

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= self.decay

    def draw(self, surface):
        if self.life > 0:
            alpha = int(self.life * 255)
            s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                s, (*self.color, alpha), (self.size, self.size), self.size
            )
            surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))


class MovingDie:
    def __init__(self, start_pos, end_pos, value, color, on_finish_callback=None):
        self.x, self.y = start_pos
        self.target_x, self.target_y = end_pos
        self.value = value
        self.color = color
        self.finished = False
        self.callback = on_finish_callback

        self.progress = 0.0
        self.speed = 0.08

    def update(self):
        if self.progress < 1.0:
            self.progress += self.speed
            if self.progress >= 1.0:
                self.progress = 1.0
                self.finished = True
                if self.callback:
                    self.callback()

            t = self.progress
            ease = 1 - pow(1 - t, 3)

            self.x = self.x + (self.target_x - self.x) * ease
            self.y = self.y + (self.target_y - self.y) * ease


class GameUI:
    def __init__(self, ai_depth=2):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Knucklebones - Cult Of The Lamb")
        self.clock = pygame.time.Clock()

        # Fonts
        self.font = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.large_font = pygame.font.SysFont("Segoe UI", 48, bold=True)
        self.small_font = pygame.font.SysFont("Segoe UI", 18)

        self.game = knucklebones_rust.Knucklebones(3, 3, 6)

        # Safe load
        self.tt = load_tt("tt.pkl")

        self.running = True
        self.ai_thinking = False
        self.ai_depth = ai_depth

        self.particles = []
        self.moving_dice = []
        self.hidden_slots = {}

    def spawn_particles(self, x, y, color, count=15):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def draw_rounded_rect(self, surface, rect, color, radius=10, shadow=True):
        """Dessine un rectangle arrondi avec une ombre"""
        if shadow:
            shadow_rect = pygame.Rect(rect.x + 4, rect.y + 4, rect.width, rect.height)
            pygame.draw.rect(
                surface, COLORS["shadow"], shadow_rect, border_radius=radius
            )
        pygame.draw.rect(surface, color, rect, border_radius=radius)

    def draw_dice_face(self, surface, x, y, size, value, color_tint=None):
        """Dessine un dé"""
        rect = pygame.Rect(x, y, size, size)

        # Ombre sous le dé
        shadow_rect = pygame.Rect(x + 3, y + 3, size, size)
        pygame.draw.rect(surface, (20, 20, 20), shadow_rect, border_radius=12)

        # Fond du dé
        base_color = COLORS["dice_bg"]
        if color_tint:
            r = (base_color[0] + color_tint[0] * 0.2) / 1.2
            g = (base_color[1] + color_tint[1] * 0.2) / 1.2
            b = (base_color[2] + color_tint[2] * 0.2) / 1.2
            base_color = (r, g, b)

        pygame.draw.rect(surface, base_color, rect, border_radius=12)
        pygame.draw.rect(surface, (200, 200, 200), rect, 2, border_radius=12)

        # Points
        dot_color = COLORS["dice_dot"]
        c = size // 2
        l = size // 4
        r = size * 3 // 4
        pts = {
            1: [(c, c)],
            2: [(l, l), (r, r)],
            3: [(l, l), (c, c), (r, r)],
            4: [(l, l), (r, l), (l, r), (r, r)],
            5: [(l, l), (r, l), (c, c), (l, r), (r, r)],
            6: [(l, l), (r, l), (l, c), (r, c), (l, r), (r, r)],
        }

        if value in pts:
            for px, py in pts[value]:
                pygame.draw.circle(surface, dot_color, (x + px, y + py), size // 9)

    def draw_board_ui(self):
        """Arrière-plan et éléments fixes"""
        self.screen.fill(COLORS["bg_dark"])

        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        pygame.draw.circle(self.screen, COLORS["bg_light"], center, 500)

    def draw_player_grid(self, board_obj, player_idx, start_y, is_human, is_active):
        grid = board_obj.get_board()
        score = self.game.get_score(player_idx)

        base_color = COLORS["accent"] if is_human else COLORS["enemy"]
        display_color = base_color if is_active else tuple(c // 2 for c in base_color)

        # Affichage du Score
        score_text = "JOUEUR" if is_human else "IA"
        name_surf = self.font.render(score_text, True, display_color)
        score_surf = self.large_font.render(str(score), True, display_color)

        if is_human:
            self.screen.blit(name_surf, (30, start_y - 40))
            self.screen.blit(score_surf, (30, start_y - 10))
        else:
            self.screen.blit(name_surf, (30, start_y + COLUMN_HEIGHT + 10))
            self.screen.blit(score_surf, (30, start_y + COLUMN_HEIGHT + 35))

        # Colonnes
        start_x = (SCREEN_WIDTH - (3 * COLUMN_WIDTH + 2 * MARGIN)) // 2
        mouse_x, mouse_y = pygame.mouse.get_pos()

        for col_idx in range(3):
            col_x = start_x + col_idx * (COLUMN_WIDTH + MARGIN)
            col_rect = pygame.Rect(col_x, start_y, COLUMN_WIDTH, COLUMN_HEIGHT)

            # Hover
            bg_col = COLORS["board_slot"]
            is_hovered = col_rect.collidepoint(mouse_x, mouse_y)

            if (
                is_human
                and is_active
                and is_hovered
                and not self.ai_thinking
                and not self.game.is_game_over()
            ):
                bg_col = tuple(min(255, c + 30) for c in bg_col)
                # Indicateur de sélection
                glow_rect = col_rect.inflate(6, 6)
                pygame.draw.rect(
                    self.screen,
                    COLORS["highlight"],
                    glow_rect,
                    border_radius=14,
                    width=2,
                )

            self.draw_rounded_rect(self.screen, col_rect, bg_col, radius=12)

            dice_size = 60
            padding = (COLUMN_WIDTH - dice_size) // 2

            column_values = grid[col_idx]
            for row_idx, val in enumerate(column_values):
                if val != 0:
                    if (player_idx, col_idx, row_idx) in self.hidden_slots:
                        continue

                    dice_y = start_y + row_idx * (dice_size + 10) + 10
                    self.draw_dice_face(
                        self.screen, col_x + padding, dice_y, dice_size, val, base_color
                    )

    def trigger_move_animation(self, player_idx, col_idx, dice_val):
        """Prépare l'animation visuelle d'un coup"""
        # Calcule de la position de départ
        start_x = SCREEN_WIDTH // 2 - 30
        start_y = SCREEN_HEIGHT // 2 - 30

        # Calcule de la position d'arrivée
        board = self.game.get_boards()[player_idx].get_board()
        col_values = board[col_idx]

        # Index de la dernière valeur non nulle
        target_row = -1
        for r in range(len(col_values) - 1, -1, -1):
            if col_values[r] != 0:
                target_row = r
                break

        if target_row == -1:
            return

        # Calcul coordonnées écran
        grid_start_y = 50 if player_idx == 1 else SCREEN_HEIGHT - 350
        grid_start_x = (SCREEN_WIDTH - (3 * COLUMN_WIDTH + 2 * MARGIN)) // 2

        col_x = grid_start_x + col_idx * (COLUMN_WIDTH + MARGIN)
        dice_size = 60
        padding = (COLUMN_WIDTH - dice_size) // 2
        target_screen_x = col_x + padding
        target_screen_y = grid_start_y + target_row * (dice_size + 10) + 10

        slot_key = (player_idx, col_idx, target_row)
        self.hidden_slots[slot_key] = True

        color = COLORS["accent"] if player_idx == 0 else COLORS["enemy"]

        def on_land():
            if slot_key in self.hidden_slots:
                del self.hidden_slots[slot_key]
            self.spawn_particles(target_screen_x + 30, target_screen_y + 30, color)

        anim = MovingDie(
            (start_x, start_y),
            (target_screen_x, target_screen_y),
            dice_val,
            color,
            on_land,
        )
        self.moving_dice.append(anim)

    def handle_click(self, pos):
        if self.game.is_game_over() or self.ai_thinking or len(self.moving_dice) > 0:
            return

        if self.game.get_current_player() != 0:
            return

        x, y = pos
        human_start_y = SCREEN_HEIGHT - 350
        if y < human_start_y:
            return

        start_x = (SCREEN_WIDTH - (3 * COLUMN_WIDTH + 2 * MARGIN)) // 2
        dice_val_to_play = self.game.get_dice_value()

        for col_idx in range(3):
            col_x = start_x + col_idx * (COLUMN_WIDTH + MARGIN)
            rect = pygame.Rect(col_x, human_start_y, COLUMN_WIDTH, COLUMN_HEIGHT)

            if rect.collidepoint(x, y):
                try:
                    success = self.game.make_move(col_idx)
                    if success:
                        self.trigger_move_animation(0, col_idx, dice_val_to_play)
                    else:
                        print("Colonne pleine")
                except Exception as e:
                    print(f"Erreur: {e}")
                break

    def ai_turn_logic(self):
        """Logique IA dans le thread"""
        if self.ai_depth <= 2:
            time.sleep(1)

        best_move, _ = get_best_move(self.game, self.ai_depth, self.tt)
        dice_val = self.game.get_dice_value()

        self.game.make_move(best_move)
        self.trigger_move_animation(1, best_move, dice_val)

        self.ai_thinking = False

    def draw(self):
        self.draw_board_ui()

        boards = self.game.get_boards()
        current_player = self.game.get_current_player()

        self.draw_player_grid(boards[1], 1, 50, False, current_player == 1)
        self.draw_player_grid(
            boards[0], 0, SCREEN_HEIGHT - 350, True, current_player == 0
        )

        if not self.game.is_game_over() and len(self.moving_dice) == 0:
            center_y = SCREEN_HEIGHT // 2 - 50
            dice_x = SCREEN_WIDTH // 2 - 40

            msg = "À toi de jouer !" if current_player == 0 else "L'IA réfléchit..."
            txt = self.font.render(msg, True, COLORS["text_main"])
            self.screen.blit(
                txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, center_y - 40)
            )

            col = COLORS["accent"] if current_player == 0 else COLORS["enemy"]
            self.draw_dice_face(
                self.screen, dice_x, center_y, 80, self.game.get_dice_value(), col
            )

        for anim in self.moving_dice:
            self.draw_dice_face(self.screen, anim.x, anim.y, 60, anim.value, anim.color)

        for p in self.particles:
            p.draw(self.screen)

        if self.game.is_game_over() and len(self.moving_dice) == 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            s0 = self.game.get_score(0)
            s1 = self.game.get_score(1)

            if s0 > s1:
                msg = "VICTOIRE !"
                col = COLORS["highlight"]
            elif s1 > s0:
                msg = "DÉFAITE..."
                col = COLORS["enemy"]
            else:
                msg = "ÉGALITÉ"
                col = COLORS["text_main"]

            txt = self.large_font.render(msg, True, col)
            self.screen.blit(
                txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, SCREEN_HEIGHT // 2 - 50)
            )

            sub = self.font.render("Appuyez pour recommencer", True, (200, 200, 200))
            self.screen.blit(
                sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, SCREEN_HEIGHT // 2 + 20)
            )

        pygame.display.flip()

    def update(self):
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        for anim in self.moving_dice[:]:
            anim.update()
            if anim.finished:
                self.moving_dice.remove(anim)

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.game.is_game_over():
                        self.reset()
                    elif event.button == 1:
                        self.handle_click(event.pos)

            if not self.game.is_game_over() and len(self.moving_dice) == 0:
                if self.game.get_current_player() == 1 and not self.ai_thinking:
                    self.ai_thinking = True
                    thread = threading.Thread(target=self.ai_turn_logic)
                    thread.start()

            self.update()
            self.draw()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def reset(self):
        self.game = knucklebones_rust.Knucklebones(3, 3, 6)
        self.ai_thinking = False
        self.ai_depth = self.ai_depth
        self.particles = []
        self.moving_dice = []
        self.hidden_slots = {}
