import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


TRUTHY = {"1", "true", "yes", "on", "oui"}
FALSY = {"0", "false", "no", "off", "non"}
TOUCH_ROTATIONS = {0, 90, 180, 270}
_ROUND_MASK_CACHE_KEY = None
_ROUND_MASK_CACHE_SURFACE = None


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


def env_positive_int(name, default):
    return max(1, env_int(name, default))


def env_non_negative_int(name, default):
    return max(0, env_int(name, default))


def env_touch_hit_slop(default=10):
    return env_non_negative_int("CORTEX_TOUCH_HIT_SLOP", default)


def env_touch_edge_margin(default=0):
    return env_non_negative_int("CORTEX_TOUCH_EDGE_MARGIN", default)


def env_fps(default=60):
    return env_positive_int("CORTEX_FPS", default)


def env_touch_rotation(default=0):
    rotation = env_int("CORTEX_TOUCH_ROTATION", default)
    fallback = default if default in TOUCH_ROTATIONS else 0
    return rotation if rotation in TOUCH_ROTATIONS else fallback


def env_screen_size(name, default):
    value = os.getenv(name)
    if not value:
        return default
    normalized = value.strip().lower().replace("*", "x").replace("×", "x")
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


def fit_text(font, text, max_width, ellipsis="..."):
    if max_width <= 0:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    trimmed = text
    while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
        trimmed = trimmed[:-1]
    if trimmed:
        return trimmed + ellipsis
    while ellipsis and font.size(ellipsis)[0] > max_width:
        ellipsis = ellipsis[:-1]
    return ellipsis


def wrap_text(font, text, max_width, max_lines=3, ellipsis="..."):
    if max_lines <= 0:
        return []

    words = text.split()
    if not words:
        return []

    lines = []
    current = ""
    for word in words:
        fitted_word = fit_text(font, word, max_width, ellipsis=ellipsis)
        candidate = f"{current} {fitted_word}".strip()
        if current and font.size(candidate)[0] > max_width:
            lines.append(current)
            current = fitted_word
        else:
            current = candidate
        if len(lines) >= max_lines:
            break

    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and " ".join(lines) != text:
        lines[-1] = fit_text(font, lines[-1], max_width, ellipsis=ellipsis)
    return lines


def display_flags(fullscreen):
    import pygame

    if fullscreen:
        return pygame.FULLSCREEN
    if env_bool("CORTEX_FRAMELESS", False):
        return pygame.NOFRAME
    return pygame.RESIZABLE


def is_synthetic_touch_mouse_event(event):
    return bool(getattr(event, "touch", False))


def rotated_touch_position(x, y, width, height, rotation=None):
    rotation = env_touch_rotation() if rotation is None else rotation
    if env_bool("CORTEX_TOUCH_FLIP_X", False):
        x = 1 - x
    if env_bool("CORTEX_TOUCH_FLIP_Y", False):
        y = 1 - y
    px = x * width
    py = y * height
    if rotation == 90:
        return width - py, px
    if rotation == 180:
        return width - px, height - py
    if rotation == 270:
        return py, height - px
    return px, py


def is_inside_round_viewport(position, width, height, edge_margin=0):
    diameter = min(width, height)
    radius = max(0, diameter / 2 - edge_margin)
    center_x = width / 2
    center_y = height / 2
    px, py = position
    return (px - center_x) ** 2 + (py - center_y) ** 2 <= radius**2


def clamp_to_round_viewport(position, width, height, edge_margin=0):
    import pygame

    diameter = min(width, height)
    radius = max(0, diameter / 2 - edge_margin)
    center = pygame.Vector2(width / 2, height / 2)
    pointer = pygame.Vector2(position)
    offset = pointer - center
    if radius <= 0:
        return tuple(center)
    if offset.length_squared() == 0 or offset.length() <= radius:
        return tuple(pointer)
    offset.scale_to_length(radius)
    return tuple(center + offset)


def circle_fits_round_viewport(position, width, height, item_radius, margin=0):
    import pygame

    diameter = min(width, height)
    radius = max(0, diameter / 2 - margin)
    center = pygame.Vector2(width / 2, height / 2)
    return pygame.Vector2(position).distance_to(center) + item_radius <= radius


def rect_fits_round_viewport(rect, center, radius, margin=0):
    import pygame

    viewport_center = pygame.Vector2(center)
    usable_radius = max(0, radius - margin)
    return all(
        pygame.Vector2(corner).distance_to(viewport_center) <= usable_radius
        for corner in (
            rect.topleft,
            rect.topright,
            rect.bottomleft,
            rect.bottomright,
        )
    )


def round_safe_rect_center(center, radius, dx_ratio, dy_ratio, rect_size, margin=0):
    import pygame

    origin = pygame.Vector2(center)
    vector = pygame.Vector2(dx_ratio, dy_ratio)
    if vector.length_squared() == 0:
        return origin

    def fitted_at(position):
        rect = pygame.Rect((0, 0), rect_size)
        rect.center = position
        return rect_fits_round_viewport(rect, origin, radius, margin=margin)

    target = origin + vector * radius
    if fitted_at(target):
        return target
    if not fitted_at(origin):
        return origin

    low = 0.0
    high = 1.0
    for _ in range(24):
        middle = (low + high) / 2
        candidate = origin + vector * radius * middle
        if fitted_at(candidate):
            low = middle
        else:
            high = middle
    return origin + vector * radius * low


def circle_hit_test(position, center, radius, padding=None):
    import pygame

    if padding is None:
        padding = env_touch_hit_slop()
    return pygame.Vector2(position).distance_to(center) <= radius + max(0, padding)


def rect_hit_test(rect, position, padding=None):
    if padding is None:
        padding = env_touch_hit_slop()
    padding = max(0, int(padding))
    return rect.inflate(padding * 2, padding * 2).collidepoint(position)


def round_safe_point(center, radius, dx_ratio, dy_ratio, item_radius=0, margin=0):
    import pygame

    origin = pygame.Vector2(center)
    vector = pygame.Vector2(dx_ratio, dy_ratio)
    if vector.length_squared() == 0:
        return origin

    target_distance = radius * vector.length()
    max_distance = max(0, radius - item_radius - margin)
    vector.scale_to_length(min(target_distance, max_distance))
    return origin + vector


def draw_round_mask(surface, center=None, radius=None, enabled=None):
    import pygame
    global _ROUND_MASK_CACHE_KEY, _ROUND_MASK_CACHE_SURFACE

    if enabled is None:
        enabled = env_bool("CORTEX_ROUND_MASK", True)
    if not enabled:
        return False

    width, height = surface.get_size()
    if center is None:
        center = pygame.Vector2(width / 2, height / 2)
    else:
        center = pygame.Vector2(center)
    if radius is None:
        radius = min(width, height) / 2

    cache_key = (
        width,
        height,
        round(center.x, 2),
        round(center.y, 2),
        round(radius, 2),
    )
    if _ROUND_MASK_CACHE_KEY != cache_key or _ROUND_MASK_CACHE_SURFACE is None:
        mask = pygame.Surface((width, height), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 255))
        pygame.draw.circle(mask, (0, 0, 0, 0), center, max(0, radius - 1))
        _ROUND_MASK_CACHE_KEY = cache_key
        _ROUND_MASK_CACHE_SURFACE = mask

    surface.blit(_ROUND_MASK_CACHE_SURFACE, (0, 0))
    return True


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

    position = None
    if is_synthetic_touch_mouse_event(event):
        return None
    if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
        position = event.pos
    elif event.type == pygame.FINGERDOWN:
        position = rotated_touch_position(event.x, event.y, width, height)

    if position is None:
        return None
    if env_bool("CORTEX_TOUCH_ROUND_CLIP", True) and not is_inside_round_viewport(
        position,
        width,
        height,
        env_touch_edge_margin(),
    ):
        return None
    return position


def pointer_move_position(event, width, height):
    import pygame

    position = None
    if is_synthetic_touch_mouse_event(event):
        return None
    if event.type == pygame.MOUSEMOTION:
        position = event.pos
    elif event.type == pygame.FINGERMOTION:
        position = rotated_touch_position(event.x, event.y, width, height)

    if position is None:
        return None
    edge_margin = env_touch_edge_margin()
    if env_bool("CORTEX_TOUCH_ROUND_CLIP", True) and not is_inside_round_viewport(
        position,
        width,
        height,
        edge_margin,
    ):
        if env_bool("CORTEX_TOUCH_EDGE_CLAMP", True):
            return clamp_to_round_viewport(position, width, height, edge_margin)
        return None
    return position


def pointer_up_position(event, width, height):
    import pygame

    position = None
    if is_synthetic_touch_mouse_event(event):
        return None
    if event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", 1) == 1:
        position = event.pos
    elif event.type == pygame.FINGERUP:
        position = rotated_touch_position(event.x, event.y, width, height)

    if position is None:
        return None
    edge_margin = env_touch_edge_margin()
    if env_bool("CORTEX_TOUCH_ROUND_CLIP", True) and not is_inside_round_viewport(
        position,
        width,
        height,
        edge_margin,
    ):
        return clamp_to_round_viewport(position, width, height, edge_margin)
    return position


def prepare_screenshot_path(path):
    if not path:
        return None
    target = Path(path).expanduser()
    if target.parent != Path("."):
        target.parent.mkdir(parents=True, exist_ok=True)
    return str(target)
