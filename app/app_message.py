import pygame

from app.screen_assets import asset_path
from app.screen_config import circular_menu_layout, env_bool, pointer_down_position

def launch_messaging(screen, cortex, screen_width, screen_height):
    """Fonction principale pour l'application Messagerie."""
    clock = pygame.time.Clock()
    running = True
    screen_width, screen_height = screen.get_size()

    background_path = asset_path("backgrounds", "message.png")
    try:
        background = pygame.image.load(background_path)
        background = pygame.transform.scale(background, (screen_width, screen_height))
    except pygame.error as e:
        print(f"Erreur lors du chargement de l'image de fond : {e}")
        running = False

    screen.blit(background, (0, 0))

    boutton_quitter, menu_buttons = circular_menu_layout(screen_width, screen_height)
    border_color = (0, 200, 0)
    border_width = 3
    pygame.draw.rect(screen, border_color, boutton_quitter, width=border_width)
    for button in menu_buttons:
        pygame.draw.rect(screen, border_color, button, width=border_width)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                pointer = pointer_down_position(event, screen_width, screen_height)
                if pointer and boutton_quitter.collidepoint(pointer):
                    running = False


        pygame.display.flip()
        if env_bool("CORTEX_EXIT_AFTER_FRAME", False):
            running = False
        clock.tick(60)
