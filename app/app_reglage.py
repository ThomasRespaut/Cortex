import pygame

from app.screen_assets import asset_path, load_icon_or_fallback
from app.screen_config import (
    circular_menu_layout,
    draw_round_mask,
    env_bool,
    pointer_down_position,
    rect_hit_test,
)


def launch_reglage(screen, cortex, screen_width, screen_height):
    """Fonction principale pour l'application Calendrier."""
    clock = pygame.time.Clock()
    running = True
    screen_width, screen_height = screen.get_size()

    # État du mode Cortex
    if cortex.local_mode == True :
        is_online = False
    else : is_online = True

    ONLINE_COLOR = (34, 197, 94)
    LOCAL_COLOR = (248, 113, 113)
    BUTTON_BG = (17, 24, 39)
    TEXT_COLOR = (245, 247, 255)

    # Charger l'image de fond
    background_path = asset_path("app_icons", "icone_reglage.png")
    background = load_icon_or_fallback(
        background_path,
        "Réglages",
        size=max(screen_width, screen_height),
        accent=(148, 163, 184),
    )
    background = pygame.transform.scale(background, (screen_width, screen_height))

    font = pygame.font.Font(None, 36)
    title_font = pygame.font.Font(None, 42)
    small_font = pygame.font.Font(None, 24)
    icon_size = max(74, int(min(screen_width, screen_height) * 0.2))
    icon = pygame.transform.smoothscale(background, (icon_size, icon_size))

    boutton_quitter, menu_buttons = circular_menu_layout(screen_width, screen_height, item_count=1)
    toggle_button = menu_buttons[0]
    border_color = (0, 200, 0)
    border_width = 3

    while running:
        diameter = min(screen_width, screen_height)
        radius = diameter / 2
        center = (screen_width / 2, screen_height / 2)

        screen.fill((5, 8, 22))
        pygame.draw.circle(screen, (30, 41, 75), center, radius, max(2, int(radius * 0.01)))
        pygame.draw.circle(screen, (82, 107, 155), center, radius - 8, 1)
        for index, color in enumerate(((36, 75, 120), (20, 120, 128), (71, 85, 145))):
            pygame.draw.circle(
                screen,
                color,
                (int(center[0]), int(center[1])),
                max(12, int(radius * (0.22 + index * 0.16))),
                1,
            )

        icon_rect = icon.get_rect(center=(center[0], center[1] - radius * 0.45))
        pygame.draw.circle(screen, (24, 33, 58), icon_rect.center, int(icon_size * 0.68))
        screen.blit(icon, icon_rect)
        title = title_font.render("Réglages", True, TEXT_COLOR)
        screen.blit(title, title.get_rect(center=(center[0], center[1] - radius * 0.24)))

        pygame.draw.rect(screen, border_color, boutton_quitter, width=border_width)
        quit_text = font.render("Quitter", True, border_color)
        quit_text_rect = quit_text.get_rect(center=boutton_quitter.center)
        screen.blit(quit_text, quit_text_rect)

        current_color = ONLINE_COLOR if is_online else LOCAL_COLOR
        pygame.draw.rect(screen, BUTTON_BG, toggle_button, border_radius=toggle_button.height // 3)
        pygame.draw.rect(screen, current_color, toggle_button, 3, border_radius=toggle_button.height // 3)

        mode_text = "Mode Online" if is_online else "Mode Local"
        text_surface = font.render(mode_text, True, current_color)
        text_rect = text_surface.get_rect(center=toggle_button.center)
        screen.blit(text_surface, text_rect)
        hint = small_font.render("Touchez pour basculer", True, (174, 185, 205))
        screen.blit(hint, hint.get_rect(center=(center[0], toggle_button.bottom + radius * 0.09)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                pointer = pointer_down_position(event, screen_width, screen_height)
                if pointer and rect_hit_test(boutton_quitter, pointer):
                    running = False
                elif pointer and rect_hit_test(toggle_button, pointer):
                    is_online = not is_online
                    if cortex.local_mode == True :
                        cortex.local_mode = False
                    else :
                        cortex.local_mode = True
                    print(f"Changement de mode : {'Online' if is_online else 'Local'}")
        draw_round_mask(screen, center, radius)
        pygame.display.flip()
        if env_bool("CORTEX_EXIT_AFTER_FRAME", False):
            running = False
        clock.tick(60)

    return is_online  # Retourne l'état final du mode pour pouvoir l'utiliser ailleurs
