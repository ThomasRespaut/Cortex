import math
import os
import sys
import threading
from dataclasses import dataclass

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

from app.app_cortex import launch_cortex
from app.feature_shell import launch_feature
from app.screen_assets import load_icon_or_fallback
from app.screen_config import (
    circle_hit_test,
    draw_round_mask as apply_round_mask,
    display_flags,
    env_bool,
    env_int,
    env_screen_size,
    circle_fits_round_viewport,
    fit_text,
    pointer_down_position,
    pointer_move_position,
    pointer_up_position,
    prepare_screenshot_path,
)

load_dotenv()


FPS = 60
BACKGROUND = (8, 15, 35)
RING = (76, 98, 145)
TEXT = (242, 245, 255)
MUTED = (148, 157, 184)
ACCENT = (88, 214, 255)
TAP_MOVE_LIMIT = 14
ZOOM_MIN = 0.72
ZOOM_MAX = 1.28
PINCH_ZOOM_FACTOR = 0.003
EMPTY_DOUBLE_TAP_MS = 500
EMPTY_DOUBLE_TAP_DISTANCE = 36


@dataclass
class AppItem:
    name: str
    icon_path: str
    grid_x: float
    grid_y: float
    enabled: bool = True


APP_DEFINITIONS = [
    ("Cortex", "icone_cortex.png"),
    ("Horloge", "icone_horloge.png"),
    ("Musique", "icone_musique.png"),
    ("Transport", "icone_transport.png"),
    ("Santé", "icone_sante.png"),
    ("Réseaux", "icone_reseau_social.png"),
    ("Calendrier", "icone_calendrier.png"),
    ("Messages", "icone_message.png"),
    ("Jeux", "icone_jeu.png"),
    ("Actualités", "icone_actualites.png"),
    ("Données", "icone_bdd.png"),
    ("Divertissement", "icone_divertissement.png"),
    ("Maison", "icone_domotique.png"),
    ("Finance", "icone_finance.png"),
    ("Mots de passe", "icone_mot_de_passe.png"),
    ("Réglages", "icone_reglage.png"),
    ("Restaurants", "icone_restauration.png"),
    ("Vêtements", "icone_vetement.png"),
    ("Éducation", "icone_education.png"),
    ("Météo", "icone_meteo.png"),
    ("Courses", "icone_supermarche.png"),
    ("Traduction", "icone_traduction.png"),
]


def build_honeycomb(items):
    positions = [(0, 0)]
    radius = 1
    while len(positions) < len(items):
        q, r = -radius, radius
        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
        for dq, dr in directions:
            for _ in range(radius):
                if len(positions) >= len(items):
                    break
                positions.append((q, r))
                q += dq
                r += dr
        radius += 1

    result = []
    for (name, filename), (q, r) in zip(items, positions):
        x = math.sqrt(3) * (q + r / 2)
        y = 1.5 * r
        result.append(
            AppItem(
                name=name,
                icon_path=os.path.join("app", "Images", "app_icons_v2", filename),
                grid_x=x,
                grid_y=y,
            )
        )
    return result


def circular_icon(source, size):
    scaled = pygame.transform.smoothscale(source, (size, size))
    result = pygame.Surface((size, size), pygame.SRCALPHA)
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
    scaled.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    result.blit(scaled, (0, 0))
    return result


class CortexHome:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Cortex")

        fullscreen = env_bool("CORTEX_FULLSCREEN", True)
        pygame.mouse.set_visible(not env_bool("CORTEX_HIDE_CURSOR", fullscreen))
        if fullscreen:
            self.screen = pygame.display.set_mode((0, 0), display_flags(fullscreen))
        else:
            preview_size = env_int("CORTEX_PREVIEW_SIZE", 900)
            screen_size = env_screen_size(
                "CORTEX_SCREEN_SIZE",
                (preview_size, preview_size),
            )
            self.screen = pygame.display.set_mode(
                screen_size,
                display_flags(fullscreen),
            )

        self.clock = pygame.time.Clock()
        self.cortex = None
        self.loading_error = None
        self.skip_cortex_load = env_bool("CORTEX_SKIP_CORTEX_LOAD", False)
        self.loading_thread = None
        if not self.skip_cortex_load:
            self.loading_thread = threading.Thread(
                target=self.load_cortex,
                name="cortex-loader",
                daemon=True,
            )
            self.loading_thread.start()
        self.apps = build_honeycomb(APP_DEFINITIONS)
        self.icons = {
            app.name: load_icon_or_fallback(app.icon_path, app.name)
            for app in self.apps
        }
        self.icon_cache = {}
        self.offset = pygame.Vector2()
        self.velocity = pygame.Vector2()
        self.zoom = 1.0
        self.dragging = False
        self.panning = False
        self.drag_origin = pygame.Vector2()
        self.last_pointer = pygame.Vector2()
        self.press_position = pygame.Vector2()
        self.selected = None
        self.active_fingers = {}
        self.pinch_last_distance = None
        self.last_empty_tap_at = None
        self.last_empty_tap_position = None
        self.suppress_next_empty_tap = False
        self.rendered_apps = []
        self.screenshot_saved = False
        self.notice_text = ""
        self.notice_until = 0
        self.title_font = pygame.font.SysFont("Segoe UI", 30, bold=True)
        self.label_font = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.small_font = pygame.font.SysFont("Segoe UI", 16)

    def load_cortex(self):
        try:
            from cortex import Cortex

            self.cortex = Cortex(
                input_mode=os.getenv("CORTEX_INPUT_MODE", "voice"),
                output_mode=os.getenv("CORTEX_OUTPUT_MODE", "voice"),
                local_mode=env_bool("CORTEX_LOCAL_MODE", True),
            )
        except Exception as error:
            self.loading_error = str(error)
            print(f"Impossible d'initialiser Cortex : {error}")

    def viewport(self):
        width, height = self.screen.get_size()
        diameter = min(width, height)
        center = pygame.Vector2(width / 2, height / 2)
        return center, diameter / 2

    def icon_for(self, app, size):
        cache_key = (app.name, size)
        if cache_key not in self.icon_cache:
            self.icon_cache[cache_key] = circular_icon(self.icons[app.name], size)
        return self.icon_cache[cache_key]

    def app_position(self, app, center, spacing):
        return center + self.offset + pygame.Vector2(
            app.grid_x * spacing,
            app.grid_y * spacing,
        )

    def draw_background(self, center, radius):
        width, height = self.screen.get_size()
        background = pygame.Surface((width, height))
        top = (22, 43, 88)
        bottom = (6, 10, 28)
        for y in range(height):
            ratio = y / max(1, height - 1)
            color = tuple(
                int(top[channel] * (1 - ratio) + bottom[channel] * ratio)
                for channel in range(3)
            )
            pygame.draw.line(background, color, (0, y), (width, y))
        self.screen.blit(background, (0, 0))

        glow = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)

        def radial_glow(position, glow_radius, color, max_alpha):
            steps = 24
            for step in range(steps, 0, -1):
                ratio = step / steps
                alpha = int(max_alpha * (1 - ratio) ** 2)
                pygame.draw.circle(
                    glow,
                    (*color, alpha),
                    position,
                    int(glow_radius * ratio),
                )

        radial_glow(
            (center.x - radius * 0.4, center.y - radius * 0.42),
            radius * 0.72,
            (77, 116, 255),
            34,
        )
        radial_glow(
            (center.x + radius * 0.48, center.y - radius * 0.22),
            radius * 0.62,
            (190, 78, 255),
            22,
        )
        radial_glow(
            (center.x + radius * 0.08, center.y + radius * 0.62),
            radius * 0.68,
            (22, 206, 204),
            20,
        )
        self.screen.blit(glow, (0, 0))

        inner = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(inner, (3, 7, 20, 60), center, radius * 0.98)
        self.screen.blit(inner, (0, 0))

        pygame.draw.circle(self.screen, RING, center, radius, max(2, int(radius * 0.009)))
        pygame.draw.circle(
            self.screen,
            (151, 174, 225),
            center,
            radius - max(4, int(radius * 0.018)),
            max(1, int(radius * 0.003)),
        )

    def draw_status(self, center, radius):
        if self.skip_cortex_load:
            mode = "APERÇU"
            mode_color = ACCENT
        elif self.loading_error:
            mode = "ERREUR"
            mode_color = (255, 105, 125)
        elif self.cortex is None:
            mode = "INITIALISATION"
            mode_color = (255, 194, 92)
        else:
            mode = "LOCAL" if self.cortex.local_mode else "EN LIGNE"
            mode_color = ACCENT
        mode_surface = self.small_font.render(mode, True, mode_color)
        mode_rect = mode_surface.get_rect(center=(center.x, center.y - radius * 0.9))
        pill = mode_rect.inflate(24, 10)
        pygame.draw.rect(self.screen, (12, 31, 44), pill, border_radius=pill.height // 2)
        pygame.draw.rect(self.screen, (28, 103, 128), pill, 1, border_radius=pill.height // 2)
        self.screen.blit(mode_surface, mode_rect)

    def show_notice(self, text, duration_ms=1800):
        self.notice_text = text
        self.notice_until = pygame.time.get_ticks() + duration_ms

    def draw_notice(self, center, radius):
        if not self.notice_text or pygame.time.get_ticks() > self.notice_until:
            return
        text = fit_text(self.small_font, self.notice_text, radius * 1.25)
        notice_surface = self.small_font.render(text, True, TEXT)
        notice_rect = notice_surface.get_rect(center=(center.x, center.y + radius * 0.78))
        notice_bg = notice_rect.inflate(26, 12)
        pygame.draw.rect(
            self.screen,
            (10, 20, 38),
            notice_bg,
            border_radius=notice_bg.height // 2,
        )
        pygame.draw.rect(
            self.screen,
            (55, 75, 116),
            notice_bg,
            1,
            border_radius=notice_bg.height // 2,
        )
        self.screen.blit(notice_surface, notice_rect)

    def draw_round_mask(self, center, radius):
        apply_round_mask(self.screen, center, radius)

    def draw_apps(self, center, radius):
        width, height = self.screen.get_size()
        spacing = radius * 0.245 * self.zoom
        base_size = radius * 0.285 * self.zoom
        safe_margin = max(6, int(radius * 0.025))
        self.rendered_apps = []

        visible = []
        for app in self.apps:
            position = self.app_position(app, center, spacing)
            distance = position.distance_to(center)
            if distance > radius * 1.05:
                continue

            focus = max(0.0, 1.0 - distance / (radius * 0.92))
            edge_fade = max(0.15, min(1.0, (radius - distance) / (radius * 0.24)))
            size = int(base_size * (0.72 + 0.56 * focus))
            size = max(62, min(size, int(radius * 0.37)))
            if not circle_fits_round_viewport(
                position,
                width,
                height,
                size / 2,
                margin=safe_margin,
            ):
                continue
            visible.append((distance, app, position, size, edge_fade, focus))

        for distance, app, position, size, edge_fade, focus in sorted(
            visible,
            key=lambda entry: entry[0],
            reverse=True,
        ):
            shadow = pygame.Surface((size + 24, size + 24), pygame.SRCALPHA)
            pygame.draw.circle(
                shadow,
                (0, 0, 0, int(90 * edge_fade)),
                (shadow.get_width() // 2, shadow.get_height() // 2 + 5),
                size // 2 + 5,
            )
            self.screen.blit(shadow, shadow.get_rect(center=position))

            icon = self.icon_for(app, size).copy()
            icon.set_alpha(int(255 * edge_fade))
            self.screen.blit(icon, icon.get_rect(center=position))
            if app == self.selected:
                pygame.draw.circle(
                    self.screen,
                    ACCENT,
                    position,
                    size // 2 + max(4, int(radius * 0.015)),
                    max(2, int(radius * 0.01)),
                )

            self.rendered_apps.append((app, position, size))

        focused = min(visible, default=None, key=lambda entry: entry[0])
        if focused and focused[0] < radius * 0.25:
            _, app, position, size, _, _ = focused
            label_text = fit_text(self.label_font, app.name, radius * 1.2)
            label = self.label_font.render(label_text, True, TEXT)
            label_rect = label.get_rect(center=(center.x, center.y + radius * 0.56))
            label_bg = label_rect.inflate(30, 14)
            pygame.draw.rect(
                self.screen,
                (8, 11, 21),
                label_bg,
                border_radius=label_bg.height // 2,
            )
            self.screen.blit(label, label_rect)

    def constrain_offset(self, radius):
        limit = radius * 1.4
        if self.offset.length() > limit:
            self.offset.scale_to_length(limit)

    def app_at(self, position):
        for app, center, size in reversed(self.rendered_apps):
            if circle_hit_test(position, center, size / 2):
                return app
        return None

    def center_app(self, app):
        center, radius = self.viewport()
        spacing = radius * 0.245 * self.zoom
        target = pygame.Vector2(app.grid_x * spacing, app.grid_y * spacing)
        self.offset = -target
        self.velocity.update(0, 0)

    def reset_view(self):
        self.offset.update(0, 0)
        self.velocity.update(0, 0)
        self.zoom = 1.0
        self.selected = None
        self.show_notice("Vue recentrée")

    def clamp_zoom(self, value):
        return max(ZOOM_MIN, min(ZOOM_MAX, value))

    def set_zoom(self, value, focus=None):
        previous_zoom = self.zoom
        next_zoom = self.clamp_zoom(value)
        if focus is not None and previous_zoom > 0 and next_zoom != previous_zoom:
            center, _ = self.viewport()
            focus = pygame.Vector2(focus)
            relative_focus = focus - center - self.offset
            self.offset = focus - center - relative_focus * (next_zoom / previous_zoom)
        self.zoom = next_zoom

    def active_touch_distance(self):
        fingers = list(self.active_fingers.values())
        if len(fingers) < 2:
            return None
        return fingers[0].distance_to(fingers[1])

    def active_touch_center(self):
        fingers = list(self.active_fingers.values())
        if not fingers:
            return None
        center = pygame.Vector2()
        for finger in fingers:
            center += finger
        return center / len(fingers)

    def launch_app(self, name):
        if self.cortex is None:
            if self.loading_error:
                message = "Cortex indisponible"
            elif self.skip_cortex_load:
                message = "Aperçu: Cortex non chargé"
            else:
                message = "Initialisation de Cortex..."
            self.show_notice(message)
            print(message)
            return
        width, height = self.screen.get_size()
        if name == "Cortex":
            launch_cortex(self.screen, self.cortex, width, height)
        else:
            app = next(item for item in self.apps if item.name == name)
            launch_feature(self.screen, self.cortex, name, app.icon_path)

    def handle_pointer_down(self, position):
        self.dragging = True
        self.press_position = pygame.Vector2(position)
        self.last_pointer = pygame.Vector2(position)
        self.velocity.update(0, 0)
        self.selected = self.app_at(position)
        self.panning = False

    def handle_pointer_move(self, position):
        if not self.dragging:
            return
        pointer = pygame.Vector2(position)
        tap_move_limit = max(1, env_int("CORTEX_TAP_MOVE_LIMIT", TAP_MOVE_LIMIT))
        if pointer.distance_to(self.press_position) < tap_move_limit:
            return
        delta = pointer - self.last_pointer
        self.panning = True
        self.offset += delta
        self.velocity = delta * 0.75
        self.last_pointer = pointer
        self.selected = None

    def handle_pointer_up(self, position):
        if not self.dragging:
            return
        release = pygame.Vector2(position)
        moved = release.distance_to(self.press_position)
        tap_move_limit = max(1, env_int("CORTEX_TAP_MOVE_LIMIT", TAP_MOVE_LIMIT))
        tapped = self.app_at(position)
        selected = self.selected
        suppress_empty_tap = self.suppress_next_empty_tap
        self.suppress_next_empty_tap = False
        self.dragging = False
        self.panning = False
        self.selected = None
        if moved < tap_move_limit and tapped and tapped == selected:
            self.launch_app(tapped.name)
        elif (
            moved < tap_move_limit
            and tapped is None
            and selected is None
            and not suppress_empty_tap
        ):
            self.handle_empty_tap(release)

    def handle_empty_tap(self, position):
        now = pygame.time.get_ticks()
        position = pygame.Vector2(position)
        double_tap_ms = max(
            1,
            env_int("CORTEX_EMPTY_DOUBLE_TAP_MS", EMPTY_DOUBLE_TAP_MS),
        )
        double_tap_distance = max(
            1,
            env_int("CORTEX_EMPTY_DOUBLE_TAP_DISTANCE", EMPTY_DOUBLE_TAP_DISTANCE),
        )
        if (
            self.last_empty_tap_at is not None
            and now - self.last_empty_tap_at <= double_tap_ms
            and self.last_empty_tap_position is not None
            and position.distance_to(self.last_empty_tap_position)
            <= double_tap_distance
        ):
            self.reset_view()
            self.last_empty_tap_at = None
            self.last_empty_tap_position = None
            return

        self.last_empty_tap_at = now
        self.last_empty_tap_position = position

    def handle_touch_event(self, event, width, height):
        if event.type == pygame.FINGERDOWN:
            pointer = pointer_down_position(event, width, height)
            if pointer is None:
                return True
            self.active_fingers[event.finger_id] = pygame.Vector2(pointer)
            if len(self.active_fingers) == 1:
                self.handle_pointer_down(pointer)
            elif len(self.active_fingers) == 2:
                self.dragging = False
                self.panning = False
                self.selected = None
                self.velocity.update(0, 0)
                self.pinch_last_distance = self.active_touch_distance()
            return True

        if event.type == pygame.FINGERMOTION:
            if event.finger_id not in self.active_fingers:
                return True
            pointer = pointer_move_position(event, width, height)
            if pointer is None:
                return True
            self.active_fingers[event.finger_id] = pygame.Vector2(pointer)
            if len(self.active_fingers) >= 2:
                distance = self.active_touch_distance()
                if distance is not None and self.pinch_last_distance is not None:
                    delta = (distance - self.pinch_last_distance) * PINCH_ZOOM_FACTOR
                    self.set_zoom(self.zoom + delta, focus=self.active_touch_center())
                self.pinch_last_distance = distance
                self.dragging = False
                self.panning = False
                self.selected = None
                self.velocity.update(0, 0)
            else:
                self.handle_pointer_move(pointer)
            return True

        if event.type == pygame.FINGERUP:
            pointer = pointer_up_position(event, width, height)
            was_pinching = (
                self.pinch_last_distance is not None
                or len(self.active_fingers) > 1
            )
            self.active_fingers.pop(event.finger_id, None)
            if was_pinching:
                self.pinch_last_distance = self.active_touch_distance()
                self.dragging = False
                self.panning = False
                self.selected = None
                self.velocity.update(0, 0)
                if len(self.active_fingers) == 1:
                    remaining = next(iter(self.active_fingers.values()))
                    self.dragging = True
                    self.press_position = remaining.copy()
                    self.last_pointer = remaining.copy()
                    self.suppress_next_empty_tap = True
                return True
            if pointer is not None:
                self.handle_pointer_up(pointer)
            return True

        return False

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                return False
            if event.key == pygame.K_HOME:
                self.offset.update(0, 0)
                self.velocity.update(0, 0)
        width, height = self.screen.get_size()
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            return self.handle_touch_event(event, width, height)
        if event.type == pygame.MOUSEWHEEL:
            self.set_zoom(self.zoom + event.y * 0.07)
        pointer_down = pointer_down_position(event, width, height)
        if pointer_down is not None:
            self.handle_pointer_down(pointer_down)
        pointer_move = pointer_move_position(event, width, height)
        if pointer_move is not None:
            self.handle_pointer_move(pointer_move)
        pointer_up = pointer_up_position(event, width, height)
        if pointer_up is not None:
            self.handle_pointer_up(pointer_up)
        return True

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                running = self.handle_event(event)
                if not running:
                    break

            if not self.dragging:
                self.offset += self.velocity
                self.velocity *= 0.9
                if self.velocity.length_squared() < 0.02:
                    self.velocity.update(0, 0)

            center, radius = self.viewport()
            self.constrain_offset(radius)
            self.draw_background(center, radius)
            self.draw_apps(center, radius)
            self.draw_status(center, radius)
            self.draw_notice(center, radius)
            self.draw_round_mask(center, radius)
            pygame.display.flip()
            screenshot_path = os.getenv("CORTEX_SCREENSHOT_PATH")
            if screenshot_path and not self.screenshot_saved:
                pygame.image.save(self.screen, prepare_screenshot_path(screenshot_path))
                self.screenshot_saved = True
                if env_bool("CORTEX_EXIT_AFTER_SCREENSHOT", False):
                    running = False
            self.clock.tick(FPS)

        pygame.quit()


def main():
    CortexHome().run()


if __name__ == "__main__":
    main()
