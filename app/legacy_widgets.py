import pygame

from app.screen_config import fit_text


def draw_legacy_status_panel(screen, title, subtitle, accent, chips=()):
    width, height = screen.get_size()
    radius = min(width, height) // 2
    center_x = width // 2
    center_y = height // 2
    title_font = pygame.font.SysFont("Segoe UI", max(24, radius // 8), bold=True)
    small_font = pygame.font.SysFont("Segoe UI", max(15, radius // 15), bold=True)

    orb_center = (center_x, center_y - radius // 5)
    pygame.draw.circle(screen, accent, orb_center, radius // 5)
    pygame.draw.circle(screen, (245, 248, 255), orb_center, radius // 12)
    pygame.draw.circle(screen, (12, 18, 32), orb_center, radius // 18)

    title_surface = title_font.render(
        fit_text(title_font, title, radius * 1.22),
        True,
        (245, 248, 255),
    )
    screen.blit(
        title_surface,
        title_surface.get_rect(center=(center_x, center_y + radius // 12)),
    )

    subtitle_surface = small_font.render(
        fit_text(small_font, subtitle, radius * 1.24),
        True,
        (225, 232, 246),
    )
    screen.blit(
        subtitle_surface,
        subtitle_surface.get_rect(center=(center_x, center_y + radius // 4)),
    )

    chip_y = center_y + radius // 2
    chip_radius = max(10, radius // 18)
    colors = (accent, (88, 214, 255), (52, 211, 153))
    visible_chips = chips[:3]
    chip_count = max(1, len(visible_chips))
    for index, chip in enumerate(visible_chips):
        x = center_x + int((index - (chip_count - 1) / 2) * radius * 0.42)
        pygame.draw.circle(
            screen,
            colors[index % len(colors)],
            (x, chip_y),
            chip_radius,
        )
        label = small_font.render(
            fit_text(small_font, chip, radius * 0.32),
            True,
            (245, 248, 255),
        )
        screen.blit(label, label.get_rect(center=(x, chip_y + chip_radius * 2)))
