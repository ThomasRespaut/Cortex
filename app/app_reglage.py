import pygame

from app.screen_assets import asset_path
from app.screen_config import circular_menu_layout, pointer_down_position


def launch_reglage(screen, cortex, screen_width, screen_height):
    """Fonction principale pour l'application Calendrier."""
    clock = pygame.time.Clock()
    running = True
    screen_width, screen_height = screen.get_size()

    # État du mode Cortex
    if cortex.local_mode == True :
        is_online = False
    else : is_online = True

    # Définition des couleurs
    ONLINE_COLOR = (0, 200, 0)  # Vert pour le mode online
    LOCAL_COLOR = (200, 0, 0)  # Rouge pour le mode local
    BUTTON_BG = (230, 230, 230)  # Gris clair pour le fond du bouton
    TEXT_COLOR = (0, 0, 0)  # Noir pour le texte

    # Charger l'image de fond
    background_path = asset_path("app_icons", "icone_reglage.png")
    try:
        background = pygame.image.load(background_path)
        background = pygame.transform.scale(background, (screen_width, screen_height))
    except pygame.error as e:
        print(f"Erreur lors du chargement de l'image de fond : {e}")
        running = False

    # Configuration de la police
    font = pygame.font.Font(None, 36)

    boutton_quitter, menu_buttons = circular_menu_layout(screen_width, screen_height, item_count=1)
    toggle_button = menu_buttons[0]
    border_color = (0, 200, 0)
    border_width = 3

    while running:
        # Rafraîchir l'écran avec l'image de fond
        screen.blit(background, (0, 0))

        # Dessiner le bouton Quitter
        pygame.draw.rect(screen, border_color, boutton_quitter, width=border_width)
        quit_text = font.render("Quitter", True, border_color)
        quit_text_rect = quit_text.get_rect(center=boutton_quitter.center)
        screen.blit(quit_text, quit_text_rect)

        # Dessiner le bouton toggle
        current_color = ONLINE_COLOR if is_online else LOCAL_COLOR
        pygame.draw.rect(screen, BUTTON_BG, toggle_button)
        pygame.draw.rect(screen, current_color, toggle_button, 3)

        # Afficher le texte du mode actuel
        mode_text = "Mode Online" if is_online else "Mode Local"
        text_surface = font.render(mode_text, True, current_color)
        text_rect = text_surface.get_rect(center=toggle_button.center)
        screen.blit(text_surface, text_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                pointer = pointer_down_position(event, screen_width, screen_height)
                if pointer and boutton_quitter.collidepoint(pointer):
                    running = False
                elif pointer and toggle_button.collidepoint(pointer):
                    is_online = not is_online
                    if cortex.local_mode == True :
                        cortex.local_mode = False
                    else :
                        cortex.local_mode = True
                    print(f"Changement de mode : {'Online' if is_online else 'Local'}")

        pygame.display.flip()
        clock.tick(60)

    return is_online  # Retourne l'état final du mode pour pouvoir l'utiliser ailleurs
