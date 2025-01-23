import pygame
import os

def launch_music(screen, cortex, screen_width, screen_height):
    """Fonction principale pour l'application Musique."""
    clock = pygame.time.Clock()
    running = True

    # Charger l'image de fond
    background_path = os.path.join("app","images", "backgrounds", "musique.png")
    try:
        background = pygame.image.load(background_path)
        background = pygame.transform.scale(background, (screen_width, screen_height))
    except pygame.error as e:
        print(f"Erreur lors du chargement de l'image de fond : {e}")
        running = False  # Quitter l'application si l'image ne peut pas être chargée

    # Boucle principale de l'application Musique
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:  # Retour à l'application principale
                    running = False

        # Afficher l'image de fond
        screen.blit(background, (0, 0))

        # Rafraîchir l'écran
        pygame.display.flip()
        clock.tick(60)
