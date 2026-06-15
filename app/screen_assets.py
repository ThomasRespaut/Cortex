import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame


def asset_path(*parts):
    return os.path.join("app", "Images", *parts)


def make_icon_fallback(label, size=128, accent=(88, 214, 255)):
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


def load_icon_or_fallback(path, label, size=128, accent=(88, 214, 255)):
    if not path:
        print(f"Icône absente pour {label}: fallback généré.")
        return make_icon_fallback(label, size=size, accent=accent)

    try:
        return pygame.image.load(path).convert_alpha()
    except (FileNotFoundError, pygame.error, OSError, TypeError) as error:
        print(f"Impossible de charger l'icône {path}: {error}")
        return make_icon_fallback(label, size=size, accent=accent)
