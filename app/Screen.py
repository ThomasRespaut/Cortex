# main.py
import pygame
import math
import time
from app_calendrier import launch_calendar
from app_transport import launch_transport
from app_jeu import launch_game
from app_message import launch_messaging
from app_horloge import launch_clock
from app_sante import launch_health
from app_musique import launch_music

pygame.init()

# Dimensions de l'écran
screen_width = 600
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))


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
mouse_update_interval = 100  # Intervalle de 100ms (0.1 seconde)
time_limit=0.2

#list_application = [("Horloge", "/images/Horloges.png")]

list_application = [
    ("Horloge", "images/app_icons/icone_horloge.png"),
    ("Musique", "images/app_icons/icone_musique.png"),
    ("Transport", "images/app_icons/icone_transport.png"),
    ("Santé", "images/app_icons/icone_sante.png"),
    ("Réseaux Sociaux", "images/Reseaux Sociaux.png"),
    ("Calendrier", "images/app_icons/icone_calendrier.png"),
    ("Messagerie", "images/app_icons/icone_message.png"),
    ("Jeux", "images/app_icons/icone_jeu.png"),
    ("Routine", "images/Routine.png"),
    ("", "images/Autre.png"),
    ("", "images/Autre.png"),
    ("", "images/Autre.png"),
    ("", "images/Autre.png"),
    ("", "images/Autre.png"),
    ("", "images/Autre.png"),
    ("", "images/Autre.png"),
    ("", "images/Autre.png"),
    ("", "images/Autre.png")
]


icon_app = pygame.image.load("Images/Horloge.png")


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
        elif (i < 7):
            radian_angle = math.radians(i * 360/6)
            distance_from_center = 270

        #2e anneau
        elif (i < 21):
            radian_angle = math.radians(i * 360/12)
            if(i%2==0) :
                distance_from_center = 545
            else :
                distance_from_center = 470
        else :
            distance_from_center = 0
            radian_angle = 0
        x = center_x + math.cos(radian_angle) * distance_from_center
        y = center_y + math.sin(radian_angle) * distance_from_center
        icon_app_resized = pygame.transform.scale(pygame.image.load(list_application[i][1]), (size_app, size_app))
        icon_width, icon_height = icon_app_resized.get_size()
        apps.append([x, y, size_app,icon_app_resized])
    end_time = time.time()
    if((end_time - start_time)>time_limit):
        print(f"generate_applications a pris {end_time - start_time} secondes")


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
    if ((end_time - start_time) > time_limit):
        print(f"draw_applications a pris {end_time - start_time} secondes")

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
    if ((end_time - start_time) > 50):
        print(f"handle_dragging a pris {end_time - start_time} secondes")

def launch_app(app_name):
    global app_launched, current_app
    if app_name == "Calendrier":
        launch_calendar(screen, screen_width, screen_height)
    elif app_name == "Horloge":
        launch_clock(screen, screen_width, screen_height)
    elif app_name == "Musique":
        launch_music(screen, screen_width, screen_height)
    elif app_name == "Transport":
        launch_transport(screen, screen_width, screen_height)
    elif app_name == "Santé":
        launch_health(screen, screen_width, screen_height)
    elif app_name == "Messagerie":
        launch_messaging(screen, screen_width, screen_height)
    elif app_name == "Jeux":
        launch_game(screen, screen_width, screen_height)
    else:
        print(f"L'application {app_name} n'est pas encore implémentée.")


def check_app_click(mouse_pos):
    #start_time = time.time()
    global selected_app, app_launched, current_app

    for i, app in enumerate(apps):
        distance = math.sqrt((app[0] - mouse_pos[0]) ** 2 + (app[1] - mouse_pos[1]) ** 2)
        if distance < app[2] / 2:
            selected_app = list_application[i][0]
            print(f"App Launched : {list_application[i][0]}")
            if selected_app:
                app_launched = True
                current_app = selected_app
                launch_app(selected_app)  # Appelle la fonction pour lancer l'application
            break
    '''
    end_time = time.time()
    if ((end_time - start_time) > time_limit):
        print(f"check_app_click a pris {end_time - start_time} secondes")
    '''
# Fonction principale
def main():
    global dragging, drag_start_pos, app_launched, current_app, mouse_start_pos, mouse_pos, last_mouse_update_time
    clock = pygame.time.Clock()
    running = True


    # Générer les applications
    generate_applications(12)  # Créer 12 applications

    while running:
        start_time = time.time()  # Temps de début
        current_time = pygame.time.get_ticks()
        if current_time - last_mouse_update_time >= mouse_update_interval:
            mouse_pos = pygame.mouse.get_pos()
            last_mouse_update_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Gestion du clic souris pour commencer le glissement
            elif event.type == pygame.MOUSEBUTTONDOWN:
                start_time_drag = time.time()
                mouse_start_pos = mouse_pos
                dragging = True
                drag_start_pos = mouse_pos

            elif event.type == pygame.MOUSEMOTION:
                if dragging is True:
                    current_pos = mouse_pos
                    dx = current_pos[0] - drag_start_pos[0]
                    dy = current_pos[1] - drag_start_pos[1]

                    # Si la souris a bougé au-delà du seuil, on considère que c'est un glissement
                    if abs(dx) > mouse_movement_threshold or abs(dy) > mouse_movement_threshold:
                        dragging = True
                        # Mettre à jour la position des applications si on glisse
                        for app in apps:
                            app[0] += dx
                            app[1] += dy

                        # Mettre à jour la position de départ du drag
                        drag_start_pos = current_pos


            # Relâcher la souris pour arrêter le glissement
            elif event.type == pygame.MOUSEBUTTONUP:
                end_time_drag = time.time()
                dragging = False
                mouse_end_pos = mouse_pos
                # Si la souris n'a presque pas bougé, considérer que c'est un clic
                if mouse_start_pos is not None:
                    dx = mouse_end_pos[0] - mouse_start_pos[0]
                    dy = mouse_end_pos[1] - mouse_start_pos[1]
                    #print(f"Position de départ : {drag_start_pos}")
                    #print(f"Distance parcouru : {abs(dx) + abs(dy)}")
                    if abs(dx) < mouse_movement_threshold and abs(dy) < mouse_movement_threshold and (end_time_drag-start_time_drag) <0.5 :
                        print("click")
                        print(f"time clicked {end_time_drag-start_time_drag}")
                        check_app_click(mouse_end_pos)
                    else :
                        print("drag")

                # Réinitialiser les variables de glissement et de clic
                dragging = False
                #mouse_start_pos = None
        #end_time = time.time()
        #print(f"get_event a pris {end_time - start_time} secondes")

        # Si on fait glisser, déplacer les applications
        handle_dragging(mouse_pos)

        # Remplir l'écran avec une couleur de fond
        screen.fill(WHITE)

        # Dessiner les applications
        draw_applications()

        # Mettre à jour l'affichage
        pygame.display.flip()
        # Limiter à 60 FPS
        clock.tick(60)
        #print(current_app)

        end_time = time.time()
        if((end_time - start_time) >time_limit) :
            print(f"main while {end_time - start_time}")
    pygame.quit()

# Lancer l'application
if __name__ == "__main__":
    main()