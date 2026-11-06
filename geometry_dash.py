"""
Geometry Dash Clone — Single-file Pygame Implementation
========================================================
A side-scrolling obstacle-avoidance game inspired by Geometry Dash.
Features smooth jumping physics, procedural obstacle generation,
score tracking, a dynamic three-variant particle death system,
a flowing RGB keyboard color-shifting background wave,
collectible currency orbs, a main-menu with clickable buttons,
a skin shop with 5 unlockable player skins, and JSON-based
save/load persistence.

Controls:
    SPACE / UP  — Jump
    MOUSE       — Click menu / shop buttons
    ESC         — Back / Quit

Author: Antigravity AI
"""

import pygame
import random
import math
import json
import os

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 900
SCREEN_HEIGHT = 500
FPS = 60

# Colours (R, G, B)
BLACK       = (0, 0, 0)
WHITE       = (255, 255, 255)
GREY        = (60, 60, 60)
DARK_GREY   = (30, 30, 30)
CYAN        = (0, 255, 255)
MAGENTA     = (255, 0, 255)
YELLOW      = (255, 255, 0)
RED         = (255, 60, 60)
ORANGE      = (255, 140, 0)
GREEN       = (80, 255, 80)
BLUE        = (80, 120, 255)
LIGHT_BLUE  = (100, 180, 255)
PINK        = (255, 100, 180)
PURPLE      = (180, 80, 255)
DARK_PURPLE = (40, 10, 50)
GOLD        = (255, 215, 0)
DARK_GOLD   = (180, 150, 0)

# Physics
GRAVITY       = 0.8
JUMP_STRENGTH = -13.5
GROUND_Y      = SCREEN_HEIGHT - 80   # top of the ground strip
PLAYER_SIZE   = 40

# Obstacle settings
OBSTACLE_MIN_GAP = 220
OBSTACLE_MAX_GAP = 360
BASE_SCROLL_SPEED = 6

# Coin spawn settings
COIN_CHANCE      = 0.35               # probability a coin spawns with each obstacle
COIN_RADIUS      = 12
COIN_VALUE       = 1                  # currency awarded per orb

# Save file location (next to the script)
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save_data.json")


# ──────────────────────────────────────────────────────────────
# Skin Definitions
# ──────────────────────────────────────────────────────────────
# Each skin is a dict with an id, display name, description,
# price (0 = free / default), and a draw key used by the Player.
SKINS = [
    {
        "id": "default",
        "name": "Classic Cyan",
        "desc": "The original cube.",
        "price": 0,
    },
    {
        "id": "neon_outline",
        "name": "Neon Outline",
        "desc": "Transparent body with a glowing neon border.",
        "price": 15,
    },
    {
        "id": "checkerboard",
        "name": "Checkerboard",
        "desc": "A retro 4x4 checker pattern.",
        "price": 25,
    },
    {
        "id": "rgb_pulse",
        "name": "RGB Pulse",
        "desc": "Colour-shifting rainbow that pulses over time.",
        "price": 40,
    },
    {
        "id": "fire_core",
        "name": "Fire Core",
        "desc": "A molten orange core with ember particles.",
        "price": 60,
    },
]

# Quick lookup by id
SKIN_MAP = {s["id"]: s for s in SKINS}


# ──────────────────────────────────────────────────────────────
# Save / Load helpers
# ──────────────────────────────────────────────────────────────
def load_save() -> dict:
    """Load persistent player data from disk, or return defaults."""
    defaults = {
        "currency": 0,
        "high_score": 0,
        "unlocked_skins": ["default"],
        "equipped_skin": "default",
    }
    if not os.path.exists(SAVE_FILE):
        return defaults
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return defaults
        # Merge with defaults to handle missing keys in old saves
        for k, v in defaults.items():
            data.setdefault(k, v)
        # Ensure types are valid
        if not isinstance(data.get("unlocked_skins"), list):
            data["unlocked_skins"] = ["default"]
        if "default" not in data["unlocked_skins"]:
            data["unlocked_skins"].insert(0, "default")
        if data.get("equipped_skin") not in SKIN_MAP:
            data["equipped_skin"] = "default"
        if not isinstance(data.get("currency"), (int, float)):
            data["currency"] = 0
        if not isinstance(data.get("high_score"), (int, float)):
            data["high_score"] = 0
        return data
    except Exception:
        return defaults


def write_save(data: dict):
    """Write player data to disk as pretty-printed JSON safely."""
    try:
        tmp_file = SAVE_FILE + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(data, f, indent=2)
        if os.path.exists(tmp_file):
            if os.path.exists(SAVE_FILE):
                os.replace(tmp_file, SAVE_FILE)
            else:
                os.rename(tmp_file, SAVE_FILE)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────
def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between *a* and *b* by factor *t*."""
    return a + (b - a) * t


def random_colour() -> tuple:
    """Return a vivid random colour."""
    return random.choice([CYAN, MAGENTA, YELLOW, RED, ORANGE, GREEN, BLUE, PINK, PURPLE])


def hsv_to_rgb(h: float, s: float, v: float) -> tuple:
    """Convert HSV (h in 0-360, s/v in 0-1) to an (R, G, B) tuple safely clamped to [0, 255]."""
    h = h % 360
    s = max(0.0, min(1.0, float(s)))
    v = max(0.0, min(1.0, float(v)))
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return (
        max(0, min(255, int((r + m) * 255))),
        max(0, min(255, int((g + m) * 255))),
        max(0, min(255, int((b + m) * 255)))
    )


# ──────────────────────────────────────────────────────────────
# UI Button (reusable clickable rectangle)
# ──────────────────────────────────────────────────────────────
class Button:
    """A simple clickable rectangular button with text."""

    def __init__(self, x: int, y: int, w: int, h: int, text: str,
                 font: pygame.font.Font,
                 colour: tuple = CYAN, text_colour: tuple = BLACK,
                 hover_colour: tuple = WHITE):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.colour = colour
        self.text_colour = text_colour
        self.hover_colour = hover_colour
        self.hovered = False
        self.enabled = True              # greyed-out when False

    def update(self, mouse_pos: tuple):
        """Check if the mouse is hovering over this button."""
        self.hovered = self.enabled and self.rect.collidepoint(mouse_pos)

    def draw(self, surface: pygame.Surface):
        """Render the button with hover highlight and optional disabled look."""
        if not self.enabled:
            # Greyed-out appearance
            pygame.draw.rect(surface, DARK_GREY, self.rect, border_radius=8)
            pygame.draw.rect(surface, GREY, self.rect, 2, border_radius=8)
            txt_surf = self.font.render(self.text, True, GREY)
        else:
            fill = self.hover_colour if self.hovered else self.colour
            pygame.draw.rect(surface, fill, self.rect, border_radius=8)
            pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=8)
            txt_surf = self.font.render(self.text, True, self.text_colour)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def clicked(self, mouse_pos: tuple) -> bool:
        """Return True if the button is enabled and was clicked at *mouse_pos*."""
        return self.enabled and self.rect.collidepoint(mouse_pos)


# ──────────────────────────────────────────────────────────────
# Particle  (single point in an explosion / coin-collect effect)
# ──────────────────────────────────────────────────────────────
class Particle:
    """A single visual particle used by the death-explosion and coin-collect systems."""

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 colour: tuple, size: float, lifetime: int,
                 shape: str = "circle", gravity: float = 0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.colour = colour
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = max(1, lifetime)
        self.shape = shape                # "circle" or "square"
        self.gravity = gravity
        self.alive = True

    def update(self):
        """Advance the particle by one frame."""
        self.vy += self.gravity
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        """Render the particle with alpha fade-out."""
        if not self.alive:
            return
        t = max(0.0, min(1.0, self.lifetime / self.max_lifetime))
        r = max(0, min(255, int(self.colour[0] * t)))
        g = max(0, min(255, int(self.colour[1] * t)))
        b = max(0, min(255, int(self.colour[2] * t)))
        col = (r, g, b)
        sz = max(1, int(self.size * t))
        if self.shape == "square":
            pygame.draw.rect(surface, col,
                             (int(self.x) - sz // 2, int(self.y) - sz // 2, sz, sz))
        else:
            pygame.draw.circle(surface, col, (int(self.x), int(self.y)), sz)


# ──────────────────────────────────────────────────────────────
# ParticleSystem
# ──────────────────────────────────────────────────────────────
class ParticleSystem:
    """
    Manages all active particles and exposes three explosion presets
    plus a coin-collect sparkle.

    Explosion presets:
    * **nova_burst**    – particles fly outward in a 360° ring.
    * **pixel_shatter** – square fragments fall with heavy gravity.
    * **spark_shower**  – sparks shoot upward then rain back down.
    """

    def __init__(self):
        self.particles: list[Particle] = []

    # ── Explosion variants ────────────────────────────────────

    def nova_burst(self, cx: float, cy: float):
        """360-degree radial explosion of circular particles."""
        for _ in range(80):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 10)
            self.particles.append(
                Particle(cx, cy,
                         math.cos(angle) * speed, math.sin(angle) * speed,
                         random_colour(), random.uniform(3, 7),
                         random.randint(30, 60), "circle", 0.05))

    def pixel_shatter(self, cx: float, cy: float):
        """Square fragments that break apart and fall with heavy gravity."""
        frag = PLAYER_SIZE // 4
        half = PLAYER_SIZE // 2
        for row in range(4):
            for col in range(4):
                fx = cx - half + col * frag + frag // 2
                fy = cy - half + row * frag + frag // 2
                self.particles.append(
                    Particle(fx, fy,
                             random.uniform(-4, 4), random.uniform(-8, -1),
                             random_colour(), frag,
                             random.randint(45, 90), "square", 0.45))

    def spark_shower(self, cx: float, cy: float):
        """Sparks shoot upward rapidly, then rain down."""
        for _ in range(70):
            self.particles.append(
                Particle(cx, cy,
                         random.uniform(-3, 3), random.uniform(-16, -6),
                         random.choice([YELLOW, ORANGE, WHITE, CYAN]),
                         random.uniform(2, 5), random.randint(50, 90),
                         "circle", 0.35))

    def coin_sparkle(self, cx: float, cy: float):
        """Small golden sparkle burst when a coin is collected."""
        for _ in range(14):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 4)
            self.particles.append(
                Particle(cx, cy,
                         math.cos(angle) * speed, math.sin(angle) * speed,
                         random.choice([GOLD, YELLOW, WHITE]),
                         random.uniform(2, 5), random.randint(15, 30),
                         "circle", 0.08))

    # ── Lifecycle ─────────────────────────────────────────────

    def trigger_random(self, cx: float, cy: float) -> str:
        """Choose a random explosion variant and trigger it. Returns the name."""
        variant = random.choice(["nova_burst", "pixel_shatter", "spark_shower"])
        getattr(self, variant)(cx, cy)
        return variant

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surface: pygame.Surface):
        for p in self.particles:
            p.draw(surface)

    @property
    def active(self) -> bool:
        return len(self.particles) > 0


# ──────────────────────────────────────────────────────────────
# Collectible Coin / Orb
# ──────────────────────────────────────────────────────────────
class Coin:
    """A glowing collectible orb that scrolls with the level."""

    def __init__(self, x: float, y: float, speed: float):
        self.x = x
        self.y = y
        self.y_draw = y                   # Pre-initialized to prevent attribute crashes
        self.speed = speed
        self.radius = COIN_RADIUS
        self.collected = False
        self.bob_offset = random.uniform(0, 2 * math.pi)  # phase for bobbing

    def update(self, frame: int):
        """Scroll left and bob gently up and down."""
        self.x -= self.speed
        # Gentle sine-wave bob (±5 px)
        self.y_draw = self.y + math.sin(frame * 0.07 + self.bob_offset) * 5

    def draw(self, surface: pygame.Surface, frame: int):
        """Draw a glowing golden orb with animated shimmer."""
        if self.collected:
            return
        cx = int(self.x)
        cy = int(self.y_draw)
        # Outer glow
        glow_r = max(1, self.radius + 4 + int(math.sin(frame * 0.1) * 2))
        pygame.draw.circle(surface, (80, 60, 0), (cx, cy), glow_r)
        # Main body
        pygame.draw.circle(surface, GOLD, (cx, cy), self.radius)
        # Highlight
        pygame.draw.circle(surface, YELLOW, (cx - 3, cy - 3), max(1, self.radius // 3))
        # Outline
        pygame.draw.circle(surface, WHITE, (cx, cy), self.radius, 2)

    def is_off_screen(self) -> bool:
        return self.x < -30

    @property
    def rect(self) -> pygame.Rect:
        margin = 2
        return pygame.Rect(int(self.x) - self.radius + margin,
                           int(self.y_draw) - self.radius + margin,
                           (self.radius - margin) * 2,
                           (self.radius - margin) * 2)


# ──────────────────────────────────────────────────────────────
# Player
# ──────────────────────────────────────────────────────────────
class Player:
    """
    The player's geometric avatar — a rotating square that can jump.
    Supports multiple visual skins selected by *skin_id*.
    """

    def __init__(self, skin_id: str = "default"):
        self.size = PLAYER_SIZE
        self.x = 120
        self.y = GROUND_Y - self.size
        self.vy = 0.0
        self.on_ground = True
        self.alive = True
        self.rotation = 0.0
        self.skin_id = skin_id
        self.trail: list[tuple] = []

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_STRENGTH
            self.on_ground = False

    def update(self):
        if not self.alive:
            return
        self.vy += GRAVITY
        self.y += self.vy
        if self.y >= GROUND_Y - self.size:
            self.y = GROUND_Y - self.size
            self.vy = 0
            self.on_ground = True
        if not self.on_ground:
            self.rotation -= 5
        else:
            self.rotation = round(self.rotation / 90) * 90
        cx = self.x + self.size // 2
        cy = int(self.y) + self.size // 2
        self.trail.append((cx, cy))
        if len(self.trail) > 8:
            self.trail.pop(0)

    # ── Rotated-corner helper ─────────────────────────────────

    def _rotated_corners(self, cx, cy, half):
        """Return four corner points of a square rotated around (cx, cy)."""
        a = math.radians(self.rotation)
        cos_a, sin_a = math.cos(a), math.sin(a)
        return [(cx + dx * cos_a - dy * sin_a,
                 cy + dx * sin_a + dy * cos_a)
                for dx, dy in [(-half, -half), (half, -half),
                                (half, half), (-half, half)]]

    # ── Skin drawing routines ─────────────────────────────────

    def _draw_skin_default(self, surface, cx, cy, half):
        """Classic cyan filled square with inner white highlight."""
        corners = self._rotated_corners(cx, cy, half)
        pygame.draw.polygon(surface, CYAN, corners)
        inner = self._rotated_corners(cx, cy, half // 2)
        pygame.draw.polygon(surface, WHITE, inner, 2)

    def _draw_skin_neon_outline(self, surface, cx, cy, half):
        """Transparent body with thick glowing neon-green border and centre dot."""
        corners = self._rotated_corners(cx, cy, half)
        # Draw three layers for a "glow" effect (outer to inner)
        pygame.draw.polygon(surface, (0, 60, 0), corners)          # dark fill
        pygame.draw.polygon(surface, (0, 255, 80), corners, 4)     # bright outline
        pygame.draw.polygon(surface, (180, 255, 180), corners, 2)  # inner white-ish
        # Small centre diamond
        inner = self._rotated_corners(cx, cy, half // 4)
        pygame.draw.polygon(surface, (0, 255, 80), inner)

    def _draw_skin_checkerboard(self, surface, cx, cy, half):
        """4×4 checkerboard pattern inside the rotated square."""
        a = math.radians(self.rotation)
        cos_a, sin_a = math.cos(a), math.sin(a)
        cell = self.size // 4
        for row in range(4):
            for col in range(4):
                # Local coords relative to centre
                lx = -half + col * cell
                ly = -half + row * cell
                # Rotate all four corners of this cell
                cell_corners = []
                for dx, dy in [(lx, ly), (lx + cell, ly),
                                (lx + cell, ly + cell), (lx, ly + cell)]:
                    rx = cx + dx * cos_a - dy * sin_a
                    ry = cy + dx * sin_a + dy * cos_a
                    cell_corners.append((rx, ry))
                colour = WHITE if (row + col) % 2 == 0 else DARK_GREY
                pygame.draw.polygon(surface, colour, cell_corners)
        # Outer border
        corners = self._rotated_corners(cx, cy, half)
        pygame.draw.polygon(surface, MAGENTA, corners, 2)

    def _draw_skin_rgb_pulse(self, surface, cx, cy, half):
        """Colour cycles through the rainbow over time using HSV."""
        ticks = pygame.time.get_ticks()
        hue = (ticks * 0.2) % 360         # full cycle every ~1.8 s
        main_col = hsv_to_rgb(hue, 1.0, 1.0)
        corners = self._rotated_corners(cx, cy, half)
        pygame.draw.polygon(surface, main_col, corners)
        # Inner ring shifts hue by 120°
        inner = self._rotated_corners(cx, cy, half * 0.55)
        pygame.draw.polygon(surface, hsv_to_rgb(hue + 120, 1.0, 1.0), inner, 3)
        # Centre dot shifts another 120°
        pygame.draw.circle(surface, hsv_to_rgb(hue + 240, 1.0, 1.0),
                           (int(cx), int(cy)), 4)

    def _draw_skin_fire_core(self, surface, cx, cy, half):
        """Molten orange core with red-hot edges."""
        corners = self._rotated_corners(cx, cy, half)
        pygame.draw.polygon(surface, (180, 40, 0), corners)       # dark red fill
        pygame.draw.polygon(surface, ORANGE, corners, 3)          # orange border
        # Inner glow
        inner = self._rotated_corners(cx, cy, half * 0.5)
        pygame.draw.polygon(surface, YELLOW, inner)
        # Tiny ember particles around the cube (2-3 dots)
        for _ in range(3):
            ex = cx + random.uniform(-half * 1.3, half * 1.3)
            ey = cy + random.uniform(-half * 1.3, half * 0.5)
            pygame.draw.circle(surface, random.choice([ORANGE, YELLOW, RED]),
                               (int(ex), int(ey)), random.randint(1, 3))

    # ── Unified draw entry point ──────────────────────────────

    def draw(self, surface: pygame.Surface):
        """Draw the player with the currently equipped skin."""
        if not self.alive:
            return

        # ── Trail ──
        for i, (tx, ty) in enumerate(self.trail):
            frac = i / len(self.trail)
            alpha = int(60 * frac)
            sz = int(self.size * 0.5 * frac)
            if sz < 2:
                continue
            pygame.draw.rect(surface, (0, alpha, alpha),
                             (tx - sz // 2, ty - sz // 2, sz, sz))

        cx = self.x + self.size // 2
        cy = int(self.y) + self.size // 2
        half = self.size // 2

        # Dispatch to the correct skin renderer
        renderer = {
            "default":       self._draw_skin_default,
            "neon_outline":  self._draw_skin_neon_outline,
            "checkerboard":  self._draw_skin_checkerboard,
            "rgb_pulse":     self._draw_skin_rgb_pulse,
            "fire_core":     self._draw_skin_fire_core,
        }.get(self.skin_id, self._draw_skin_default)
        renderer(surface, cx, cy, half)

    @staticmethod
    def draw_preview(surface: pygame.Surface, skin_id: str,
                     cx: int, cy: int, size: int = 36,
                     rotation: float = 0.0):
        """
        Draw a static preview of a skin at (cx, cy).
        Used by the shop UI.
        """
        half = size // 2
        a = math.radians(rotation)
        cos_a, sin_a = math.cos(a), math.sin(a)

        def corners(h):
            return [(cx + dx * cos_a - dy * sin_a,
                     cy + dx * sin_a + dy * cos_a)
                    for dx, dy in [(-h, -h), (h, -h), (h, h), (-h, h)]]

        if skin_id == "default":
            c = corners(half)
            pygame.draw.polygon(surface, CYAN, c)
            pygame.draw.polygon(surface, WHITE, corners(half // 2), 2)

        elif skin_id == "neon_outline":
            c = corners(half)
            pygame.draw.polygon(surface, (0, 60, 0), c)
            pygame.draw.polygon(surface, (0, 255, 80), c, 3)
            pygame.draw.polygon(surface, (180, 255, 180), c, 1)

        elif skin_id == "checkerboard":
            cell = size // 4
            for row in range(4):
                for col in range(4):
                    lx = -half + col * cell
                    ly = -half + row * cell
                    cc = []
                    for dx, dy in [(lx, ly), (lx + cell, ly),
                                    (lx + cell, ly + cell), (lx, ly + cell)]:
                        cc.append((cx + dx * cos_a - dy * sin_a,
                                   cy + dx * sin_a + dy * cos_a))
                    colour = WHITE if (row + col) % 2 == 0 else DARK_GREY
                    pygame.draw.polygon(surface, colour, cc)
            pygame.draw.polygon(surface, MAGENTA, corners(half), 2)

        elif skin_id == "rgb_pulse":
            hue = (pygame.time.get_ticks() * 0.2) % 360
            pygame.draw.polygon(surface, hsv_to_rgb(hue, 1, 1), corners(half))
            pygame.draw.polygon(surface, hsv_to_rgb(hue + 120, 1, 1),
                                corners(int(half * 0.55)), 2)

        elif skin_id == "fire_core":
            c = corners(half)
            pygame.draw.polygon(surface, (180, 40, 0), c)
            pygame.draw.polygon(surface, ORANGE, c, 3)
            pygame.draw.polygon(surface, YELLOW, corners(int(half * 0.5)))

        else:
            # Fallback
            pygame.draw.polygon(surface, CYAN, corners(half))

    @property
    def rect(self) -> pygame.Rect:
        margin = 6
        return pygame.Rect(self.x + margin, int(self.y) + margin,
                           self.size - margin * 2, self.size - margin * 2)


# ──────────────────────────────────────────────────────────────
# Obstacles
# ──────────────────────────────────────────────────────────────
class Obstacle:
    """Base class for scrolling obstacles."""

    def __init__(self, x: float, speed: float):
        self.x = x
        self.speed = speed
        self.passed = False

    def update(self):
        self.x -= self.speed

    def is_off_screen(self) -> bool:
        return self.x < -80

    def draw(self, surface: pygame.Surface):
        raise NotImplementedError

    @property
    def rect(self) -> pygame.Rect:
        raise NotImplementedError


class SpikeObstacle(Obstacle):
    """A triangular spike sitting on the ground."""

    def __init__(self, x: float, speed: float):
        super().__init__(x, speed)
        self.width = 36
        self.height = 44

    def draw(self, surface: pygame.Surface):
        bx = int(self.x)
        by = GROUND_Y
        tip   = (bx + self.width // 2, by - self.height)
        left  = (bx, by)
        right = (bx + self.width, by)
        pygame.draw.polygon(surface, RED, [tip, left, right])
        pygame.draw.polygon(surface, WHITE, [tip, left, right], 2)

    @property
    def rect(self) -> pygame.Rect:
        mx, mt = 8, 10
        return pygame.Rect(int(self.x) + mx, GROUND_Y - self.height + mt,
                           self.width - mx * 2, self.height - mt)


class BlockObstacle(Obstacle):
    """A solid rectangular block on the ground."""

    def __init__(self, x: float, speed: float):
        super().__init__(x, speed)
        self.width = 40
        self.height = random.choice([40, 60, 80])

    def draw(self, surface: pygame.Surface):
        bx = int(self.x)
        by = GROUND_Y - self.height
        pygame.draw.rect(surface, MAGENTA, (bx, by, self.width, self.height))
        pygame.draw.rect(surface, WHITE, (bx, by, self.width, self.height), 2)
        pygame.draw.line(surface, WHITE, (bx, by),
                         (bx + self.width, by + self.height), 1)
        pygame.draw.line(surface, WHITE, (bx + self.width, by),
                         (bx, by + self.height), 1)

    @property
    def rect(self) -> pygame.Rect:
        m = 4
        return pygame.Rect(int(self.x) + m, GROUND_Y - self.height + m,
                           self.width - m * 2, self.height - m * 2)


class DoubleSpikeObstacle(Obstacle):
    """Two spikes side by side for added difficulty."""

    def __init__(self, x: float, speed: float):
        super().__init__(x, speed)
        self.width = 60
        self.spike_w = 30
        self.height = 44

    def draw(self, surface: pygame.Surface):
        for i in range(2):
            bx = int(self.x) + i * self.spike_w
            by = GROUND_Y
            tip   = (bx + self.spike_w // 2, by - self.height)
            left  = (bx, by)
            right = (bx + self.spike_w, by)
            pygame.draw.polygon(surface, ORANGE, [tip, left, right])
            pygame.draw.polygon(surface, WHITE, [tip, left, right], 2)

    @property
    def rect(self) -> pygame.Rect:
        mx, mt = 6, 10
        return pygame.Rect(int(self.x) + mx, GROUND_Y - self.height + mt,
                           self.width - mx * 2, self.height - mt)


# ──────────────────────────────────────────────────────────────
# Background decoration
# ──────────────────────────────────────────────────────────────
class BackgroundStar:
    """A tiny dot that scrolls slowly for a parallax star-field effect."""

    def __init__(self):
        self.reset(random.randint(0, SCREEN_WIDTH))

    def reset(self, x=None):
        self.x = x if x is not None else SCREEN_WIDTH + random.randint(0, 100)
        self.y = random.randint(10, GROUND_Y - 20)
        self.speed = random.uniform(0.3, 1.5)
        self.size = random.randint(1, 3)
        brightness = random.randint(40, 120)
        self.colour = (brightness, brightness, brightness + 40)

    def update(self):
        self.x -= self.speed
        if self.x < -5:
            self.reset()

    def draw(self, surface: pygame.Surface):
        pygame.draw.circle(surface, self.colour, (int(self.x), self.y), self.size)


# ──────────────────────────────────────────────────────────────
# Game  (main controller)
# ──────────────────────────────────────────────────────────────
class Game:
    """
    Top-level game manager.

    States:
        "menu"      – main menu (Play / Shop)
        "shop"      – skin shop UI
        "playing"   – active gameplay
        "dying"     – death particle animation
        "gameover"  – game-over overlay
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Geometry Dash — Pygame Clone")
        self.clock = pygame.time.Clock()
        self.font_big   = pygame.font.SysFont("consolas", 52, bold=True)
        self.font_med   = pygame.font.SysFont("consolas", 28)
        self.font_sm    = pygame.font.SysFont("consolas", 20)
        self.font_xs    = pygame.font.SysFont("consolas", 16)
        self.frame = 0                     # global frame counter

        # Persistent background stars
        self.stars = [BackgroundStar() for _ in range(60)]

        # ── Load persistent save data ─────────────────────────
        self.save_data = load_save()
        self.currency   = self.save_data["currency"]
        self.high_score = self.save_data["high_score"]
        self.unlocked   = list(self.save_data["unlocked_skins"])
        self.equipped   = self.save_data["equipped_skin"]

        # Build menu / shop buttons (created once, updated each frame)
        self._build_menu_buttons()
        self._build_shop_buttons()

        self._reset_gameplay()

    # ── Persistent data ───────────────────────────────────────

    def _persist(self):
        """Write current state to the JSON save file."""
        self.save_data.update({
            "currency": self.currency,
            "high_score": self.high_score,
            "unlocked_skins": self.unlocked,
            "equipped_skin": self.equipped,
        })
        write_save(self.save_data)

    # ── Button builders ───────────────────────────────────────

    def _build_menu_buttons(self):
        """Create the main-menu Play and Shop buttons, and game-over buttons."""
        bw, bh = 200, 50
        cx = SCREEN_WIDTH // 2 - bw // 2
        self.btn_play = Button(cx, 250, bw, bh, "PLAY",
                               self.font_med, CYAN, BLACK)
        self.btn_shop = Button(cx, 320, bw, bh, "SHOP",
                               self.font_med, MAGENTA, BLACK)
        self.menu_buttons = [self.btn_play, self.btn_shop]

        # Game-over buttons
        go_bw, go_bh = 160, 44
        go_cx = SCREEN_WIDTH // 2
        self.btn_go_retry = Button(go_cx - go_bw - 10, 340, go_bw, go_bh,
                                   "RETRY", self.font_med, CYAN, BLACK)
        self.btn_go_menu  = Button(go_cx + 10, 340, go_bw, go_bh,
                                   "MENU", self.font_med, MAGENTA, BLACK)

    def _build_shop_buttons(self):
        """
        Create shop item rows.  Each row has a Buy / Equip button and
        is associated with a skin entry.
        """
        self.shop_items: list[dict] = []
        start_y = 80
        row_h = 64
        for i, skin in enumerate(SKINS):
            y = start_y + i * row_h
            owned = skin["id"] in self.unlocked
            is_equipped = skin["id"] == self.equipped

            if skin["price"] == 0 or owned:
                label = "EQUIPPED" if is_equipped else "EQUIP"
                btn = Button(720, y + 10, 130, 36, label,
                             self.font_sm, GREEN if is_equipped else LIGHT_BLUE,
                             BLACK)
                btn.enabled = not is_equipped
            else:
                btn = Button(720, y + 10, 130, 36, f"BUY  {skin['price']}",
                             self.font_sm, GOLD, BLACK)
                btn.enabled = self.currency >= skin["price"]

            self.shop_items.append({
                "skin": skin,
                "y": y,
                "button": btn,
            })

        # Back button
        self.btn_shop_back = Button(20, 15, 100, 36, "< BACK",
                                    self.font_sm, WHITE, BLACK)

    # ── Gameplay reset ────────────────────────────────────────

    def _reset_gameplay(self):
        """Reset gameplay-specific state (not menu / shop)."""
        self.state = "menu"
        self.player = Player(skin_id=self.equipped)
        self.obstacles: list[Obstacle] = []
        self.coins: list[Coin] = []
        self.particles = ParticleSystem()
        self.score = 0
        self.coins_this_run = 0
        self.scroll_speed = BASE_SCROLL_SPEED
        self.distance = 0.0
        self.next_obstacle_dist = 300.0
        self.death_variant = ""
        self.ground_offset = 0.0
        self.flash_timer = 0

    # ── Main loop ─────────────────────────────────────────────

    def run(self):
        """Entry point — runs until the player quits."""
        running = True
        while running:
            self.clock.tick(FPS)
            self.frame += 1
            mouse_pos = pygame.mouse.get_pos()

            # ── Event handling ─────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # ESC backs out of sub-screens, or quits from menu
                        if self.state in ("shop", "gameover"):
                            self._go_to_menu()
                        elif self.state == "playing":
                            self._go_to_menu()
                        else:
                            running = False

                    elif event.key in (pygame.K_SPACE, pygame.K_UP):
                        if self.state == "playing":
                            self.player.jump()
                        elif self.state == "gameover":
                            self._start_game()

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(mouse_pos)

            # ── Update ─────────────────────────────────────
            if self.state == "playing":
                self._update_playing()
            elif self.state == "dying":
                self._update_dying()

            # Update button hover states
            if self.state == "menu":
                for b in self.menu_buttons:
                    b.update(mouse_pos)
            elif self.state == "shop":
                self.btn_shop_back.update(mouse_pos)
                for item in self.shop_items:
                    item["button"].update(mouse_pos)
            elif self.state == "gameover":
                self.btn_go_retry.update(mouse_pos)
                self.btn_go_menu.update(mouse_pos)

            for s in self.stars:
                s.update()

            # ── Draw ───────────────────────────────────────
            self._draw()
            pygame.display.flip()

        # Save on exit
        self._persist()
        pygame.quit()

    # ── Navigation helpers ────────────────────────────────────

    def _go_to_menu(self):
        """Return to the main menu and save progress."""
        self._persist()
        self._build_shop_buttons()        # refresh affordability
        self._reset_gameplay()

    def _start_game(self):
        """Begin a new gameplay run."""
        self.state = "playing"
        self.player = Player(skin_id=self.equipped)
        self.obstacles.clear()
        self.coins.clear()
        self.particles = ParticleSystem()
        self.score = 0
        self.coins_this_run = 0
        self.scroll_speed = BASE_SCROLL_SPEED
        self.distance = 0.0
        self.next_obstacle_dist = 300.0
        self.ground_offset = 0.0

    # ── Click handling ────────────────────────────────────────

    def _handle_click(self, mouse_pos: tuple):
        """Dispatch mouse clicks based on current state."""
        if self.state == "menu":
            if self.btn_play.clicked(mouse_pos):
                self._start_game()
            elif self.btn_shop.clicked(mouse_pos):
                self._build_shop_buttons()  # refresh before entering
                self.state = "shop"

        elif self.state == "shop":
            if self.btn_shop_back.clicked(mouse_pos):
                self._go_to_menu()
            else:
                for item in self.shop_items:
                    btn = item["button"]
                    skin = item["skin"]
                    if btn.clicked(mouse_pos):
                        if skin["id"] in self.unlocked:
                            # Equip this skin
                            self.equipped = skin["id"]
                        else:
                            # Buy this skin
                            if self.currency >= skin["price"]:
                                self.currency -= skin["price"]
                                self.unlocked.append(skin["id"])
                                self.equipped = skin["id"]
                        self._persist()
                        self._build_shop_buttons()  # refresh UI
                        break

        elif self.state == "gameover":
            # "Menu" and "Retry" buttons drawn on game-over
            if self.btn_go_menu.clicked(mouse_pos):
                self._go_to_menu()
            elif self.btn_go_retry.clicked(mouse_pos):
                self._start_game()

    # ── Update routines ───────────────────────────────────────

    def _update_playing(self):
        """Advance gameplay by one frame."""
        self.player.update()
        self.scroll_speed = BASE_SCROLL_SPEED + self.score * 0.03
        self.ground_offset = (self.ground_offset + self.scroll_speed) % 40

        # Distance scoring
        self.distance += self.scroll_speed
        new_score = int(self.distance / 80)
        if new_score > self.score:
            self.score = new_score

        # Spawn obstacles (and maybe coins)
        self.next_obstacle_dist -= self.scroll_speed
        if self.next_obstacle_dist <= 0:
            self._spawn_obstacle()
            gap = random.randint(OBSTACLE_MIN_GAP, OBSTACLE_MAX_GAP)
            gap = max(160, gap - self.score)
            self.next_obstacle_dist = gap

        # Update obstacles & check collisions
        for obs in self.obstacles:
            obs.speed = self.scroll_speed
            obs.update()
            if not obs.passed and obs.x + 60 < self.player.x:
                obs.passed = True
            if self.player.rect.colliderect(obs.rect):
                self._kill_player()
                return
        self.obstacles = [o for o in self.obstacles if not o.is_off_screen()]

        # Update coins & check collection
        for coin in self.coins:
            coin.speed = self.scroll_speed
            coin.update(self.frame)
            if not coin.collected and self.player.rect.colliderect(coin.rect):
                coin.collected = True
                self.coins_this_run += COIN_VALUE
                self.currency += COIN_VALUE
                # Sparkle!
                self.particles.coin_sparkle(coin.x, coin.y_draw)
        self.coins = [c for c in self.coins
                      if not c.is_off_screen() and not c.collected]

        # Update any active particles (coin sparkles during play)
        self.particles.update()

    def _update_dying(self):
        """Play the death particle animation, then switch to game-over."""
        self.particles.update()
        self.flash_timer = max(self.flash_timer - 1, 0)
        self.ground_offset = (self.ground_offset + 2) % 40
        if not self.particles.active:
            self.state = "gameover"
            # Build game-over buttons
            bw, bh = 160, 44
            cx = SCREEN_WIDTH // 2
            self.btn_go_retry = Button(cx - bw - 10, 340, bw, bh,
                                       "RETRY", self.font_med, CYAN, BLACK)
            self.btn_go_menu  = Button(cx + 10, 340, bw, bh,
                                       "MENU", self.font_med, MAGENTA, BLACK)

    def _kill_player(self):
        """Handle player death."""
        self.player.alive = False
        cx = self.player.x + self.player.size // 2
        cy = int(self.player.y) + self.player.size // 2
        self.death_variant = self.particles.trigger_random(cx, cy)
        self.state = "dying"
        self.flash_timer = 8
        if self.score > self.high_score:
            self.high_score = self.score
        self._persist()

    def _spawn_obstacle(self):
        """Add a randomly chosen obstacle (and optionally a coin) at the right edge."""
        x = SCREEN_WIDTH + random.randint(0, 40)
        kind = random.choices(
            [SpikeObstacle, BlockObstacle, DoubleSpikeObstacle],
            weights=[45, 30, 25], k=1)[0]
        obs = kind(x, self.scroll_speed)
        self.obstacles.append(obs)

        # Maybe spawn a coin near this obstacle
        if random.random() < COIN_CHANCE:
            # Place the coin above the obstacle, slightly offset
            coin_x = x + random.randint(-20, 50)
            coin_y = GROUND_Y - random.randint(70, 140)
            self.coins.append(Coin(coin_x, coin_y, self.scroll_speed))

    # ── Drawing ───────────────────────────────────────────────

    def _draw(self):
        """Master draw dispatcher."""
        self._draw_background()
        for s in self.stars:
            s.draw(self.screen)

        if self.state == "menu":
            self._draw_menu()
        elif self.state == "shop":
            self._draw_shop()
        elif self.state in ("playing", "dying"):
            self._draw_game()
        elif self.state == "gameover":
            self._draw_game()
            self._draw_gameover_overlay()

    def _draw_background(self):
        """
        Dynamic RGB color wave background that smoothly shifts through the spectrum.
        Uses elapsed time and HSV-to-RGB conversion with sine wave modulation
        to mimic the slow, flowing chromatic wave of an RGB keyboard across both
        the main menu and active gameplay.
        """
        ticks = pygame.time.get_ticks()

        # Continuous, flowing hue progression through the 360-degree color spectrum
        # At 0.02 deg/ms, a full chromatic cycle takes ~18 seconds
        base_hue = (ticks * 0.02) % 360

        # Draw smooth vertical gradient bands with wave displacement
        band_h = 2  # 2-pixel vertical bands provide a continuous gradient at 60 FPS
        for y in range(0, SCREEN_HEIGHT, band_h):
            t = y / SCREEN_HEIGHT

            # Flowing sine wave modulation creates an undulating chromatic wave
            wave = math.sin(ticks * 0.0018 + t * 2.8) * 18.0
            hue = (base_hue + t * 50.0 + wave) % 360

            # Value (brightness) fades from a rich glow at top (0.32) down to deep dark
            # near the ground (0.08) so foreground obstacles, player, and HUD stay legible
            v = lerp(0.32, 0.08, t)
            s = 0.85
            col = hsv_to_rgb(hue, s, v)
            pygame.draw.rect(self.screen, col, (0, y, SCREEN_WIDTH, band_h))

    def _draw_ground(self):
        """Draw the scrolling ground strip with grid lines."""
        pygame.draw.rect(self.screen, GREY,
                         (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
        pygame.draw.line(self.screen, WHITE,
                         (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 2)
        step = 40
        offset = int(self.ground_offset)
        for gx in range(-step + offset, SCREEN_WIDTH + step, step):
            x = SCREEN_WIDTH - gx
            pygame.draw.line(self.screen, DARK_GREY,
                             (x, GROUND_Y + 1), (x, SCREEN_HEIGHT), 1)

    def _draw_currency_badge(self, x: int, y: int):
        """Draw a small currency indicator (coin icon + amount)."""
        # Coin icon
        pygame.draw.circle(self.screen, GOLD, (x + 10, y + 10), 10)
        pygame.draw.circle(self.screen, YELLOW, (x + 8, y + 8), 4)
        pygame.draw.circle(self.screen, WHITE, (x + 10, y + 10), 10, 2)
        # Amount text
        txt = self.font_sm.render(f"{self.currency}", True, GOLD)
        self.screen.blit(txt, (x + 26, y))

    # ── Menu ──────────────────────────────────────────────────

    def _draw_menu(self):
        """Render the main menu with Play and Shop buttons."""
        self._draw_ground()

        # Title
        title = self.font_big.render("GEOMETRY  DASH", True, CYAN)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 100)))

        # Decorative line
        pygame.draw.line(self.screen, MAGENTA,
                         (SCREEN_WIDTH // 2 - 180, 140),
                         (SCREEN_WIDTH // 2 + 180, 140), 3)

        # Subtitle
        sub = self.font_sm.render("Choose an option", True, LIGHT_BLUE)
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 170)))

        # High score
        if self.high_score > 0:
            hs = self.font_sm.render(f"High Score: {self.high_score}", True, YELLOW)
            self.screen.blit(hs, hs.get_rect(center=(SCREEN_WIDTH // 2, 210)))

        # Buttons
        for b in self.menu_buttons:
            b.draw(self.screen)

        # Currency badge (top-right)
        self._draw_currency_badge(SCREEN_WIDTH - 140, 15)

        # Spinning demo player with equipped skin
        rot = (pygame.time.get_ticks() * 0.1) % 360
        Player.draw_preview(self.screen, self.equipped,
                            SCREEN_WIDTH // 2, 405, 26, rot)

        # Controls hint
        ctrl = self.font_xs.render(
            "SPACE/UP = Jump  |  Mouse = Menu  |  ESC = Quit", True, GREY)
        self.screen.blit(ctrl, ctrl.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20)))

    # ── Shop ──────────────────────────────────────────────────

    def _draw_shop(self):
        """Render the skin shop UI."""
        self._draw_ground()

        # Header
        title = self.font_big.render("SKIN  SHOP", True, MAGENTA)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 55)))

        # Currency badge
        self._draw_currency_badge(SCREEN_WIDTH - 140, 15)

        # Back button
        self.btn_shop_back.draw(self.screen)

        # ── Item rows ─────────────────────────────────────
        for item in self.shop_items:
            skin = item["skin"]
            y = item["y"]
            btn = item["button"]
            owned = skin["id"] in self.unlocked
            is_eq = skin["id"] == self.equipped

            # Row background
            row_rect = pygame.Rect(30, y, SCREEN_WIDTH - 60, 52)
            bg_col = (30, 35, 50) if not is_eq else (20, 50, 30)
            pygame.draw.rect(self.screen, bg_col, row_rect, border_radius=6)
            pygame.draw.rect(self.screen, GREY, row_rect, 1, border_radius=6)

            # Skin preview (small rotating cube)
            preview_rot = (pygame.time.get_ticks() * 0.08) % 360
            Player.draw_preview(self.screen, skin["id"],
                                70, y + 26, 20, preview_rot)

            # Name
            name_col = WHITE if owned else LIGHT_BLUE
            name_surf = self.font_med.render(skin["name"], True, name_col)
            self.screen.blit(name_surf, (100, y + 4))

            # Description
            desc_surf = self.font_xs.render(skin["desc"], True, GREY)
            self.screen.blit(desc_surf, (100, y + 31))

            # Price tag (for locked skins)
            if not owned and skin["price"] > 0:
                price_col = GOLD if self.currency >= skin["price"] else RED
                price_surf = self.font_sm.render(
                    f"Cost: {skin['price']}", True, price_col)
                self.screen.blit(price_surf, (560, y + 16))

            # Equipped indicator
            if is_eq:
                eq_surf = self.font_xs.render("[ACTIVE]", True, GREEN)
                self.screen.blit(eq_surf, (560, y + 16) if owned else (460, y + 16))

            # Action button
            btn.draw(self.screen)

    # ── Gameplay ──────────────────────────────────────────────

    def _draw_game(self):
        """Render the active play area."""
        self._draw_ground()

        for obs in self.obstacles:
            obs.draw(self.screen)

        for coin in self.coins:
            coin.draw(self.screen, self.frame)

        self.player.draw(self.screen)
        self.particles.draw(self.screen)

        # White flash on death
        if self.flash_timer > 0:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash_surf.fill(WHITE)
            flash_surf.set_alpha(int(200 * (self.flash_timer / 8)))
            self.screen.blit(flash_surf, (0, 0))

        # HUD — top-left: score & speed
        self.screen.blit(
            self.font_med.render(f"Score: {self.score}", True, WHITE), (20, 15))
        self.screen.blit(
            self.font_sm.render(f"Speed: {self.scroll_speed:.1f}", True, LIGHT_BLUE),
            (20, 50))

        # HUD — top-right: coins collected this run + total currency
        self._draw_currency_badge(SCREEN_WIDTH - 140, 15)
        run_txt = self.font_xs.render(
            f"+{self.coins_this_run} this run", True, YELLOW)
        self.screen.blit(run_txt, (SCREEN_WIDTH - 140, 42))

    # ── Game Over ─────────────────────────────────────────────

    def _draw_gameover_overlay(self):
        """Semi-transparent overlay with score, buttons, and death-style label."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(160)
        self.screen.blit(overlay, (0, 0))

        cx = SCREEN_WIDTH // 2

        # "GAME OVER"
        go = self.font_big.render("GAME OVER", True, RED)
        self.screen.blit(go, go.get_rect(center=(cx, 120)))

        # Score
        self.screen.blit(
            self.font_med.render(f"Score: {self.score}", True, WHITE),
            self.font_med.render(f"Score: {self.score}", True, WHITE)
                .get_rect(center=(cx, 190)))

        # High score
        self.screen.blit(
            self.font_med.render(f"High Score: {self.high_score}", True, YELLOW),
            self.font_med.render(f"High Score: {self.high_score}", True, YELLOW)
                .get_rect(center=(cx, 225)))

        # Coins earned
        self.screen.blit(
            self.font_sm.render(
                f"Coins earned: +{self.coins_this_run}  (Total: {self.currency})",
                True, GOLD),
            self.font_sm.render(
                f"Coins earned: +{self.coins_this_run}  (Total: {self.currency})",
                True, GOLD).get_rect(center=(cx, 265)))

        # Death variant
        variant_nice = (self.death_variant or "Unknown").replace("_", " ").title()
        dv = self.font_sm.render(f'Death Style: "{variant_nice}"', True, ORANGE)
        self.screen.blit(dv, dv.get_rect(center=(cx, 300)))

        # Retry / Menu buttons
        self.btn_go_retry.draw(self.screen)
        self.btn_go_menu.draw(self.screen)

        # Hint
        hint = self.font_xs.render("SPACE to retry  |  ESC for menu", True, GREY)
        self.screen.blit(hint, hint.get_rect(center=(cx, 400)))


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    game = Game()
    game.run()
