# main.py
import pygame
import math
import time
import pandas as pd
from app.app_calendrier import launch_calendar
from app.app_transport import launch_transport
from app.app_jeu import launch_game
from app.app_message import launch_messaging
from app.app_horloge import launch_clock
from app.app_sante import launch_health
from app.app_musique import launch_music
from app.app_cortex import launch_cortex
from app.app_bdd import launch_bdd

import sys
import os

# Ajouter le dossier parent à sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importer cortex.py
from cortex import Cortex



pygame.init()

clock = pygame.time.Clock()
FPS = 60

# Dimensions de l'écran
screen_width = 900
screen_height = 900
screen = pygame.display.set_mode((screen_width, screen_height))
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
infoObject = pygame.display.Info()
screen_width = infoObject.current_w
screen_height = infoObject.current_h
cortex = Cortex(input_mode="voice", output_mode="voice")
pygame.display.set_caption("Cortex")
#bg = pygame.image.load("images/backgrounds/background.png").convert()
#bg = pygame.transform.scale(bg, (screen_width, screen_height))

temps_fonctions = pd.DataFrame()
temps_fonctions[['total','fonctions_de_fin','generate_applications','current_time','boucle_events','handle_dragging','draw_applications','pygame.display.flip()']] = [[0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]]

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 122, 255)

# Variables globales
center_x = screen_width // 2
center_y = screen_height // 2
app_radius = min(screen_width,screen_height)/2  # Rayon maximal pour les applications proches du centre
distance_between_apps = 80  # Distance entre les centres des applications
size_app = 250
apps = []  # Liste pour stocker les positions des applications
dragging = False  # Variable pour vérifier si on fait glisser les applications
drag_start_pos = None
selected_app = None  # Application actuellement sélectionnée
app_launched = False  # Indicateur pour savoir si une application est lancée
current_app = None  # Stocker l'application en cours
mouse_start_pos = None  # Position de départ du clic pour différencier entre un glissement et un clic
mouse_movement_threshold = 30  # Seuil de mouvement de la souris pour considérer un drag
mouse_pos = (0, 0)  # Position initiale de la souris
last_mouse_update_time = 0  # Temps écoulé depuis la dernière mise à jour de la position de la souris
mouse_update_interval = 10  # Intervalle de 100ms (0.1 seconde)
time_limit=0.2

#list_application = [("Horloge", "/images/Horloges.png")]

list_application = [
    ("Cortex", "app/images/app_icons/icone_cortex.png"),
    ("Horloge", "app/images/app_icons/icone_horloge.png"),
    ("Musique", "app/images/app_icons/icone_musique.png"),
    ("Transport", "app/images/app_icons/icone_transport.png"),
    ("Santé", "app/images/app_icons/icone_sante.png"),
    ("Réseaux Sociaux", "app/images/app_icons/icone_reseau_social.png"),
    ("Calendrier", "app/images/app_icons/icone_calendrier.png"),
    ("Messagerie", "app/images/app_icons/icone_message.png"),
    ("Jeux", "app/images/app_icons/icone_jeu.png"),
    ("Actualités", "app/images/app_icons/icone_actualites.png"),
    ("BDD", "app/images/app_icons/icone_bdd.png"),
    ("Divertissement", "app/images/app_icons/icone_divertissement.png"),
    ("Domotique", "app/images/app_icons/icone_domotique.png"),
    ("Finance", "app/images/app_icons/icone_finance.png"),
    ("Mot De Passe", "app/images/app_icons/icone_mot_de_passe.png"),
    ("Réglage", "app/images/app_icons/icone_reglage.png"),
    ("Restauration", "app/images/app_icons/icone_restauration.png"),
    ("Vetement", "app/images/app_icons/icone_vetement.png"),
    ("Eduction", "app/images/app_icons/icone_education.png"),
    ("Météo", "app/images/app_icons/icone_meteo.png"),
    ("Supermarché", "app/images/app_icons/icone_supermarche.png"),
    ("Traduction", "app/images/app_icons/icone_traduction.png"),
]


#icon_app = pygame.image.load("app/Images/Horloge.png")



# Générer les applications en forme de cercle
def generate_applications(num_apps):
    start_time = time.time()  # Temps de début
    for i in range(0,len(list_application)) :
        distance_from_center = 0
        radian_angle = 0
        if(i==0) :
            x = center_x
            y = center_y

        #1er anneau
        elif (i < 8):
            radian_angle = math.radians(i * 360/7)
            distance_from_center = 330

        #2e anneau
        elif (i < 22):
            radian_angle = math.radians(i * 360/14)
            if(i%2==0) :
                distance_from_center = 620
            else :
                distance_from_center = 550
        else :
            distance_from_center = 0
            radian_angle = 0
        x = center_x - math.sin(radian_angle) * distance_from_center
        y = center_y - math.cos(radian_angle) * distance_from_center
        if i != 0 :
            icon_app_resized = pygame.transform.scale(pygame.image.load(list_application[i][1]), (size_app, size_app))
            apps.append([x, y, size_app, icon_app_resized])
        else :
            coef = 1.4
            icon_app_resized = pygame.transform.scale(pygame.image.load(list_application[i][1]), (size_app*coef, size_app*coef))
            apps.append([x - (size_app//2 * coef - size_app//2), y - (size_app//2 * coef - size_app//2), size_app*coef, icon_app_resized])

    end_time = time.time()
    temps_fonctions.loc[0,'generate_applications'] += end_time - start_time


# Fonction pour dessiner les applications

def is_pixel_in_app(x, y, apps):
    for app in apps:
        app_x, app_y = app[0], app[1]
        radius = size_app // 2
        if (x - app_x) ** 2 + (y - app_y) ** 2 <= radius ** 2:
            return True
    return False

def draw_applications():
    start_time = time.time()  # Temps de début

    for i, app in enumerate(apps):
        #pygame.draw.circle(screen, BLUE, (int(app[0]), int(app[1])), size)
        #icon_app = pygame.image.load("Images/Horloge.png")

        screen.blit(app[3], (app[0] - size_app // 2, app[1] - size_app // 2))
    end_time = time.time()
    temps_fonctions.loc[0,'draw_applications'] += end_time - start_time

# Fonction pour gérer le déplacement des applications
def handle_dragging(mouse_pos):
    start_time = time.time()  # Temps de début
    global dragging, drag_start_pos

    if dragging:
        # Calculer le décalage entre la position actuelle et la position de départ du drag
        dx = mouse_pos[0] - drag_start_pos[0]
        dy = mouse_pos[1] - drag_start_pos[1]

        # Déplacer toutes les applications en fonction de ce décalage
        for app in apps:
            app[0] += dx
            app[1] += dy

        # Mettre à jour la position de départ du drag
        drag_start_pos = mouse_pos
    end_time = time.time()
    temps_fonctions.loc[0,'handle_dragging'] += end_time - start_time

def launch_app(app_name):
    global app_launched, current_app
    if app_name == "Calendrier":
        launch_calendar(screen, cortex, screen_width, screen_height)
    elif app_name == "Cortex":
        launch_cortex(screen, cortex, screen_width, screen_height)
    elif app_name == "Horloge":
        launch_clock(screen, cortex, screen_width, screen_height)
    elif app_name == "Musique":
        launch_music(screen, cortex, screen_width, screen_height)
    elif app_name == "Transport":
        launch_transport(screen, cortex, screen_width, screen_height)
    elif app_name == "Santé":
        launch_health(screen, cortex, screen_width, screen_height)
    elif app_name == "Messagerie":
        launch_messaging(screen, cortex, screen_width, screen_height)
    elif app_name == "Jeux":
        launch_game(screen, cortex, screen_width, screen_height)
    elif app_name == "BDD":
        launch_bdd(screen, cortex, screen_width, screen_height)
    else:
        print(f"L'application {app_name} n'est pas encore implémentée.")


def check_app_click(mouse_pos):
    start_time = time.time()
    global selected_app, app_launched, current_app

    for i, app in enumerate(apps):
        distance = math.sqrt((app[0] - mouse_pos[0]) ** 2 + (app[1] - mouse_pos[1]) ** 2)
        if distance < app[2] / 2:
            selected_app = list_application[i][0]
            print(f"App Launched : {list_application[i][0]}")
            if selected_app:
                app_launched = True
                current_app = selected_app
                launch_app(selected_app)
            break
    end_time = time.time()
    #temps_fonctions.loc[0,'check_app_click'] += end_time - start_time # A ne pas mettre
# Fonction principale
def main():
    start_prog = time.time()
    global dragging, drag_start_pos, app_launched, current_app, touch_start_pos, touch_pos

    # Initialize touch-related variables
    touch_start_pos = None
    drag_start_pos = None  # Initialize drag_start_pos
    touch_pos = (0, 0)
    last_touch_update_time = 0
    touch_update_interval = 16  # roughly 60 FPS update interval

    clock = pygame.time.Clock()
    running = True

    # Touch-specific variables
    touch_start_time = 0
    tap_threshold = 0.3  # seconds
    drag_threshold = 10  # pixels

    # Générer les applications
    generate_applications(28)

    while running:
        clock.tick(FPS)

        current_time = pygame.time.get_ticks()

        # Update touch position
        if current_time - last_touch_update_time >= touch_update_interval:
            touch_pos = pygame.mouse.get_pos()
            last_touch_update_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Touch down event (equivalent to mouse button down)
            elif event.type == pygame.FINGERDOWN:
                touch_pos = pygame.mouse.get_pos()
                touch_start_pos = touch_pos
                drag_start_pos = touch_pos  # Set drag_start_pos
                touch_start_time = time.time()
                dragging = False

            # Touch move event
            elif event.type == pygame.FINGERMOTION:
                if touch_start_pos is not None and drag_start_pos is not None:
                    dx = touch_pos[0] - drag_start_pos[0]
                    dy = touch_pos[1] - drag_start_pos[1]

                    # Check if movement exceeds drag threshold
                    if abs(dx) > drag_threshold or abs(dy) > drag_threshold:
                        dragging = True
                        # Move applications
                        for app in apps:
                            app[0] += dx
                            app[1] += dy

                        # Update drag start position
                        drag_start_pos = touch_pos

            # Touch up event (equivalent to mouse button up)
            elif event.type == pygame.FINGERUP:
                touch_end_time = time.time()
                touch_end_pos = touch_pos

                # Determine if it's a tap or drag
                if touch_start_pos is not None:
                    dx = touch_end_pos[0] - touch_start_pos[0]
                    dy = touch_end_pos[1] - touch_start_pos[1]

                    # Check for tap (short duration and small movement)
                    if (not dragging and
                            abs(dx) < drag_threshold and
                            abs(dy) < drag_threshold and
                            (touch_end_time - touch_start_time) < tap_threshold):
                        print("Tap detected")
                        check_app_click(touch_end_pos)
                    elif dragging:
                        print("Drag completed")

                # Reset touch variables
                dragging = False
                touch_start_pos = None
                drag_start_pos = None

        # Handle any ongoing dragging
        if drag_start_pos is not None:
            handle_dragging(touch_pos)

        # Render screen
        screen.fill(WHITE)
        draw_applications()

        pygame.display.update()

    pygame.quit()

    # Performance tracking (unchanged from original)
    end_time = time.time()
    temps_fonctions.loc[0, 'total'] += end_time - start_prog
    for i in temps_fonctions:
        print(f'{i} : {temps_fonctions[i].iloc[0]}')


# Lancer l'application
if __name__ == "__main__":
    main()