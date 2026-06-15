import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame


def asset_path(*parts):
    return os.path.join("app", "Images", *parts)


def safe_icon_size(size, default=1):
    try:
        if isinstance(size, str):
            normalized = size.strip().lower().replace("*", "x")
            size = normalized.split("x", 1)[0]
        return max(default, int(size))
    except (TypeError, ValueError):
        return default


def safe_surface_size(size, default=1):
    if isinstance(size, str):
        normalized = size.strip().lower().replace("*", "x")
        if "x" in normalized:
            width_text, height_text = normalized.split("x", 1)
            try:
                return (
                    max(default, int(width_text.strip())),
                    max(default, int(height_text.strip())),
                )
            except ValueError:
                return default, default
        safe_size = safe_icon_size(normalized, default=default)
        return safe_size, safe_size

    if isinstance(size, (int, float)):
        safe_size = safe_icon_size(size, default=default)
        return safe_size, safe_size

    try:
        width, height = size
        return max(default, int(width)), max(default, int(height))
    except (TypeError, ValueError):
        return default, default


def make_icon_fallback(label, size=128, accent=(88, 214, 255)):
    size = safe_icon_size(size)
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surface, (10, 17, 35), (size // 2, size // 2), size // 2)
    pygame.draw.circle(surface, accent, (size // 2, size // 2), size // 2 - 4, 4)

    try:
        font = pygame.font.SysFont("Segoe UI", max(26, size // 2), bold=True)
        text = (label.strip()[:1] or "?").upper()
        glyph = font.render(text, True, (242, 245, 255))
        surface.blit(glyph, glyph.get_rect(center=(size // 2, size // 2)))
    except pygame.error:
        pygame.draw.circle(surface, (242, 245, 255), (size // 2, size // 2), size // 9)

    return surface.convert_alpha() if pygame.display.get_init() else surface


def make_background_fallback(label, size, accent=(88, 214, 255)):
    width, height = safe_surface_size(size)
    surface = pygame.Surface((width, height))
    top = (16, 28, 58)
    bottom = (4, 7, 20)
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(
            int(top[channel] * (1 - ratio) + bottom[channel] * ratio)
            for channel in range(3)
        )
        pygame.draw.line(surface, color, (0, y), (width, y))

    radius = min(width, height) // 2
    center = (width // 2, height // 2)
    pygame.draw.circle(surface, accent, center, max(18, int(radius * 0.36)), 3)
    pygame.draw.circle(surface, (240, 245, 255), center, max(8, int(radius * 0.08)))

    try:
        font = pygame.font.SysFont("Segoe UI", max(22, int(radius * 0.12)), bold=True)
        text = (label.strip() or "Cortex")[:18]
        glyph = font.render(text, True, (240, 245, 255))
        surface.blit(glyph, glyph.get_rect(center=(center[0], center[1] + radius * 0.28)))
    except pygame.error:
        pass

    return surface.convert() if pygame.display.get_init() else surface


def load_background_or_fallback(path, label, size, accent=(88, 214, 255)):
    size = safe_surface_size(size)
    try:
        background = pygame.image.load(path)
        return pygame.transform.scale(background, size)
    except (FileNotFoundError, pygame.error, OSError, TypeError) as error:
        print(f"Impossible de charger le fond {path}: {error}")
        return make_background_fallback(label, size, accent=accent)


def load_icon_or_fallback(path, label, size=128, accent=(88, 214, 255)):
    if not path:
        print(f"Icône absente pour {label}: fallback généré.")
        return make_icon_fallback(label, size=size, accent=accent)

    try:
        return pygame.image.load(path).convert_alpha()
    except (FileNotFoundError, pygame.error, OSError, TypeError) as error:
        print(f"Impossible de charger l'icône {path}: {error}")
        return make_icon_fallback(label, size=size, accent=accent)
