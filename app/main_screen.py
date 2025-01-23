import pygame
from Screen3 import main_page
from app_calendrier import calendar_page

pygame.init()

# Dimensions de la fenêtre
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Application Modulaire")

# Boucle principale
current_page = "main"  # La page actuelle : "main" ou "calendar"
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Gestion de la navigation entre les pages
        if current_page == "main":
            current_page = main_page(screen, event)  # Retourne "calendar" si le bouton est cliqué
        elif current_page == "calendar":
            current_page = calendar_page(screen, event)  # Retourne "main" si on veut revenir

    pygame.display.flip()

pygame.quit()
