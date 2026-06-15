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


def prepare_screenshot_path(path):
    if not path:
        return None
    target = Path(path)
    if target.parent != Path("."):
        target.parent.mkdir(parents=True, exist_ok=True)
    return str(target)
