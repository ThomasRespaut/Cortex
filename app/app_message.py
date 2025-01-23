import pygame
import os

def launch_messaging(screen, cortex, screen_width, screen_height):
    """Fonction principale pour l'application Messagerie."""
    clock = pygame.time.Clock()
    running = True

    background_path = os.path.join("app","images", "backgrounds", "message.png")
    try:
        background = pygame.image.load(background_path)
        background = pygame.transform.scale(background, (screen_width, screen_height))
    except pygame.error as e:
        print(f"Erreur lors du chargement de l'image de fond : {e}")
        running = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.blit(background, (0, 0))

        pygame.display.flip()
        clock.tick(60)
