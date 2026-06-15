import pygame
from app.legacy_widgets import draw_legacy_status_panel
from app.screen_assets import asset_path, load_background_or_fallback
from app.screen_config import (
    circular_menu_layout,
    draw_round_mask,
    env_bool,
    env_fps,
    pointer_down_position,
    rect_hit_test,
)
#from Screen import main

def launch_calendar(screen, cortex, screen_width, screen_height):
    """Fonction principale pour l'application Calendrier."""
    clock = pygame.time.Clock()
    running = True
    screen_width, screen_height = screen.get_size()
    # Charger l'image de fond
    background_path = asset_path("backgrounds", "calendrier.png")
    background = load_background_or_fallback(
        background_path,
        "Calendrier",
        (screen_width, screen_height),
        accent=(249, 115, 22),
    )

    screen.blit(background, (0, 0))

    boutton_quitter, menu_buttons = circular_menu_layout(screen_width, screen_height)
    border_color = (0, 200, 0)
    border_width = 3
    pygame.draw.rect(screen, border_color, boutton_quitter, width=border_width)
    for button in menu_buttons:
        pygame.draw.rect(screen, border_color, button, width=border_width)
    draw_legacy_status_panel(
        screen,
        "Calendrier",
        "Planning du jour",
        (249, 115, 22),
        ("RDV", "Taches", "Alertes"),
    )

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
