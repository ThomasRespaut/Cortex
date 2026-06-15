import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


TRUTHY = {"1", "true", "yes", "on", "oui"}
FALSY = {"0", "false", "no", "off", "non"}


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in TRUTHY:
        return True
    if normalized in FALSY:
        return False
    return default


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_screen_size(name, default):
    value = os.getenv(name)
    if not value:
        return default
    normalized = value.strip().lower().replace("*", "x")
    if "x" not in normalized:
        return default
    width_text, height_text = normalized.split("x", 1)
    try:
        width = int(width_text.strip())
        height = int(height_text.strip())
    except ValueError:
        return default
    if width <= 0 or height <= 0:
        return default
    return width, height


def display_flags(fullscreen):
    import pygame

    if fullscreen:
        return pygame.FULLSCREEN
    if env_bool("CORTEX_FRAMELESS", False):
        return pygame.NOFRAME
    return pygame.RESIZABLE


def rotated_touch_position(x, y, width, height, rotation=None):
    rotation = env_int("CORTEX_TOUCH_ROTATION", 0) if rotation is None else rotation
    rotation %= 360
    px = x * width
    py = y * height
    if rotation == 90:
        return width - py, px
    if rotation == 180:
        return width - px, height - py
    if rotation == 270:
        return py, height - px
    return px, py


def circular_menu_layout(width, height, item_count=4):
    import pygame

    diameter = min(width, height)
    radius = diameter / 2
    center_x = width / 2
    center_y = height / 2

    quit_width = max(96, min(180, int(diameter * 0.32)))
    quit_height = max(34, min(54, int(diameter * 0.085)))
    quit_rect = pygame.Rect(
        int(center_x - quit_width / 2),
        max(0, int(center_y - radius + radius * 0.1)),
        quit_width,
        quit_height,
    )

    item_width = max(220, int(diameter * 0.7))
    item_width = min(item_width, int(width * 0.86))
    item_height = max(42, int(diameter * 0.095))
    item_gap = max(12, int(diameter * 0.035))
    total_height = item_count * item_height + max(0, item_count - 1) * item_gap
    start_y = int(center_y - total_height / 2 + radius * 0.08)

    item_rects = [
        pygame.Rect(
            int(center_x - item_width / 2),
            start_y + index * (item_height + item_gap),
            item_width,
            item_height,
        )
        for index in range(item_count)
    ]
    return quit_rect, item_rects


def pointer_down_position(event, width, height):
    import pygame

    if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
        return event.pos
    if event.type == pygame.FINGERDOWN:
        return rotated_touch_position(event.x, event.y, width, height)
    return None


def pointer_move_position(event, width, height):
    import pygame

    if event.type == pygame.MOUSEMOTION:
        return event.pos
    if event.type == pygame.FINGERMOTION:
        return rotated_touch_position(event.x, event.y, width, height)
    return None


def pointer_up_position(event, width, height):
    import pygame

    if event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", 1) == 1:
        return event.pos
    if event.type == pygame.FINGERUP:
        return rotated_touch_position(event.x, event.y, width, height)
    return None


def prepare_screenshot_path(path):
    if not path:
        return None
    target = Path(path)
    if target.parent != Path("."):
        target.parent.mkdir(parents=True, exist_ok=True)
    return str(target)
