import pygame

from app.screen_assets import asset_path, load_background_or_fallback
from app.screen_config import (
    circular_menu_layout,
    draw_round_mask,
    env_bool,
    env_fps,
    pointer_down_position,
    rect_hit_test,
)

def launch_transport(screen, cortex, screen_width, screen_height):
    """Fonction principale pour l'application Transport."""
    clock = pygame.time.Clock()
    running = True
    screen_width, screen_height = screen.get_size()

    background_path = asset_path("backgrounds", "transport.png")
    background = load_background_or_fallback(
        background_path,
        "Transport",
        (screen_width, screen_height),
        accent=(56, 189, 248),
    )

    screen.blit(background, (0, 0))

    boutton_quitter, menu_buttons = circular_menu_layout(screen_width, screen_height)
    border_color = (0, 200, 0)
    border_width = 3
    pygame.draw.rect(screen, border_color, boutton_quitter, width=border_width)
    for button in menu_buttons:
        pygame.draw.rect(screen, border_color, button, width=border_width)

    center_x = screen_width // 2
    center_y = screen_height // 2
    radius = min(screen_width, screen_height) // 2
    title_font = pygame.font.SysFont("Segoe UI", max(24, radius // 8), bold=True)
    small_font = pygame.font.SysFont("Segoe UI", max(16, radius // 14), bold=True)
    orb_center = (center_x, center_y - radius // 5)
    pygame.draw.circle(screen, (56, 189, 248), orb_center, radius // 5)
    pygame.draw.rect(
        screen,
        (235, 250, 255),
        pygame.Rect(
            center_x - radius // 7,
            center_y - radius // 4,
            radius // 3,
            radius // 11,
        ),
        border_radius=max(4, radius // 30),
    )
    pygame.draw.circle(
        screen,
        (15, 23, 42),
        (center_x - radius // 11, center_y - radius // 7),
        radius // 28,
    )
    pygame.draw.circle(
        screen,
        (15, 23, 42),
        (center_x + radius // 11, center_y - radius // 7),
        radius // 28,
    )
    title = title_font.render("Transport", True, (235, 250, 255))
    screen.blit(title, title.get_rect(center=(center_x, center_y + radius // 12)))
    for index, color in enumerate(
        ((56, 189, 248), (251, 191, 36), (52, 211, 153))
    ):
        x = center_x - radius // 3 + index * radius // 3
        pygame.draw.circle(screen, color, (x, center_y + radius // 4), radius // 16)
    hint = small_font.render("Trajets favoris", True, (240, 245, 255))
    screen.blit(hint, hint.get_rect(center=(center_x, center_y + radius // 2)))

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                pointer = pointer_down_position(event, screen_width, screen_height)
                if pointer and rect_hit_test(boutton_quitter, pointer):
                    running = False

        draw_round_mask(screen)
        pygame.display.flip()
        if env_bool("CORTEX_EXIT_AFTER_FRAME", False):
            running = False
        clock.tick(env_fps())
