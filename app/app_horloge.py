import pygame
import os

def launch_clock(screen, cortex, screen_width, screen_height):
    """Fonction principale pour l'application Horloge."""
    clock = pygame.time.Clock()
    running = True

    background_path = os.path.join("app","images", "backgrounds", "horloge.png")
    try:
        background = pygame.image.load(background_path)
        background = pygame.transform.scale(background, (screen_width, screen_height))
    except pygame.error as e:
        print(f"Erreur lors du chargement de l'image de fond : {e}")
        running = False

    screen.blit(background, (0, 0))

    #Bouton Quitter
    boutton_quitter = pygame.Rect(screen_width/2-75, 0, 150, 50)
    border_color = (0, 200, 0)
    border_width = 3
    pygame.draw.rect(screen, border_color, boutton_quitter, width=border_width)

    #Bouton 1
    boutton_1 = pygame.Rect(screen_width/2-200, 200, 400, 75)
    border_color = (0, 200, 0)
    border_width = 3
    pygame.draw.rect(screen, border_color, boutton_1, width=border_width)

    #Bouton 2
    boutton_2 = pygame.Rect(screen_width/2-200, 300, 400, 75)
    border_color = (0, 200, 0)
    border_width = 3
    pygame.draw.rect(screen, border_color, boutton_2, width=border_width)

    #Bouton 3
    boutton_3 = pygame.Rect(screen_width/2-200, 400, 400, 75)
    border_color = (0, 200, 0)
    border_width = 3
    pygame.draw.rect(screen, border_color, boutton_3, width=border_width)

    #Bouton 4
    boutton_4 = pygame.Rect(screen_width/2-200, 500, 400, 75)
    border_color = (0, 200, 0)
    border_width = 3
    pygame.draw.rect(screen, border_color, boutton_4, width=border_width)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if boutton_quitter.collidepoint(event.pos):
                    running = False


        pygame.display.flip()
        clock.tick(60)
