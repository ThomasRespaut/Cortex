import pygame
import sys
import os


# Ajouter le dossier parent à sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



running = True


def conversation(cortex, screen, background, boutton_1, screen_width, screen_height, boutton_quitter):
    global running
    running_conversation = True
    screen.blit(background, (0, 0))
    screen.blit(boutton_1[0], boutton_1[1])
    pygame.display.flip()
    display_text_letter_by_letter(screen, "Ok Cortex pour démarrer...", screen_width, screen_height, (screen_width / 2, screen_height / 6), boutton_quitter, delay=10, text_size=40)

    while running_conversation:
        user_response = None

        if cortex.input_mode == "voice":
            if cortex.first_keyword_detection:
                if not cortex.keyword_detection():
                    continue
                screen.blit(background, (0, 0))
                screen.blit(boutton_1[0], boutton_1[1])
                display_text_letter_by_letter(screen, "Ok Cortex pour démarrer...", screen_width, screen_height,
                                              (screen_width / 2, screen_height / 6), boutton_quitter, delay=10,text_size=40)
                pygame.display.flip()
                cortex.first_keyword_detection = False

            # Efface la zone où "Voix détectée" sera affiché
            clear_rect = pygame.Rect(0, screen_height / 6 * 2 - 50, screen_width, 100)  # Rect pour effacer
            screen.blit(background, clear_rect, clear_rect)

            display_text_letter_by_letter(screen, "Voix détectée", screen_width, screen_height,
                                          (screen_width / 2, screen_height / 6 + 50), boutton_quitter, delay=10, text_size=40)

            user_response = cortex.wait_for_response()
            #Interrompre d'urgence
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if boutton_quitter.collidepoint(event.pos):
                        running = False
                        running_conversation = False
                        break
            if(running==False or running_conversation == False):
                break
            if user_response:
                # Efface la zone où "Votre question" sera affichée
                clear_rect = pygame.Rect(0, screen_height / 6 * 3 - 50, screen_width, 100)  # Rect pour effacer
                #screen.blit(background, clear_rect, clear_rect)

                display_text_letter_by_letter(screen, f"Votre question : {user_response}", screen_width, screen_height,
                                              (screen_width / 2, screen_height / 6 * 2), boutton_quitter, delay=10, text_size=40)

                print(f"Utilisateur : {user_response}")
            else:
                cortex.first_keyword_detection = True
                continue

        if cortex.input_mode == "text":
            user_response = input("Utilisateur : ")

            if user_response.lower() in ["quit", "stop", "exit"]:
                print("Conversation terminée.")
                break

        if not user_response:
            continue

        ai_response = cortex.generate_text(user_response)

        if ai_response:
            # Efface la zone où "Réponse" sera affichée
            clear_rect = pygame.Rect(0, screen_height / 6 * 2 - 50, screen_width, 1000)  # Rect pour effacer
            screen.blit(background, clear_rect, clear_rect)

            display_text_letter_by_letter(screen, f"Réponse : {ai_response}", screen_width, screen_height,
                                          (screen_width / 2, screen_height / 6 * 3), boutton_quitter, delay=10, text_size = 40)
            print(f"Cortex : {ai_response}")

            if cortex.output_mode == "voice":
                if isinstance(ai_response, str) and ai_response.strip():
                    audio_stream = cortex.generate_speech(ai_response)
                    if audio_stream:
                        cortex.play_audio(audio_stream)
                    else:
                        print("Impossible de générer l'audio.")
            running_conversation=False

        print("-" * 100)

def discussion(screen, text, cortex, background, boutton_1, screen_width, screen_height, pos, boutton_quitter) :
    conversation(cortex, screen, background, (boutton_1[0], boutton_1[1], boutton_1[2]), screen_width, screen_height, boutton_quitter)
    #display_text_letter_by_letter(screen, text, screen_width, screen_height, pos,  boutton_quitter, delay = 50)


def display_text_letter_by_letter(screen, text, screen_width, screen_height, pos, boutton_quitter, delay=250, clock=None, text_size= 50):
    """
    Affiche un texte lettre par lettre au centre de l'écran, avec gestion automatique des retours à la ligne.

    :param screen: Surface sur laquelle dessiner
    :param text: Texte à afficher
    :param font: Police à utiliser pour le texte
    :param color: Couleur du texte
    :param screen_width: Largeur de l'écran
    :param screen_height: Hauteur de l'écran
    :param delay: Temps en millisecondes entre chaque lettre
    :param clock: Instance de pygame.time.Clock pour limiter la vitesse
    """

    global running

    font = pygame.font.Font(None, text_size)  # Police par défaut, taille 50
    color = (255, 255, 255)


    words = text.split(' ')  # Découpe le texte en mots
    line_height = font.size('Tg')[1]  # Hauteur d'une ligne
    max_width = screen_width * 0.8  # Limite la largeur du texte à 80% de la largeur de l'écran

    lines = []
    current_line = ""

    # Construire les lignes en fonction de la largeur maximale
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] > max_width:
            lines.append(current_line.strip())
            current_line = word + " "
        else:
            current_line = test_line
    lines.append(current_line.strip())  # Ajouter la dernière ligne

    total_height = len(lines) * line_height  # Hauteur totale du texte
    start_x = pos[0]
    start_y = pos[1] - total_height// 2  # Calculer le centre vertical pour la position finale

    rendered_text = ""

    # Animation lettre par lettre
    for line_index, line in enumerate(lines):
        for letter in line:
            rendered_text += letter
            text_surface = font.render(rendered_text, True, color)

            # Position temporaire (non centrée finalisée)
            text_x = start_x - font.size(line)[0] // 2
            text_y = start_y + line_index * line_height

            # Dessiner les lignes précédentes
            for i, prev_line in enumerate(lines[:line_index]):
                prev_surface = font.render(prev_line, True, color)
                prev_x = start_x  - prev_surface.get_width() // 2
                prev_y = start_y + i * line_height
                screen.blit(prev_surface, (prev_x, prev_y))
            # Dessiner la ligne en cours
            screen.blit(text_surface, (text_x, text_y))
            pygame.display.flip()

            if clock:
                clock.tick(60)
            pygame.time.delay(delay)

            #Interrompre d'urgence
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if boutton_quitter.collidepoint(event.pos):
                        screen.blit(font.render("TOTO", True, color), (0, 0))
                        running = False
                        break
            if(running==False) :
                break

        rendered_text = ""  # Réinitialiser pour la prochaine ligne
        if (running == False):
            break
    pygame.display.flip()



def launch_cortex(screen, cortex, screen_width, screen_height):
    """Fonction principale pour l'application Calendrier."""
    clock = pygame.time.Clock()
    global running
    running = True
    # Charger l'image de fond
    background_path = os.path.join("app","images", "backgrounds", "cortex.png")
    try:
        infoObject = pygame.display.Info()
        background = pygame.image.load(background_path)
        background = pygame.transform.scale(background, (infoObject.current_w, infoObject.current_h))
        screen_width = infoObject.current_w
        screen_height = infoObject.current_h
    except pygame.error as e:
        print(f"Erreur lors du chargement de l'image de fond : {e}")
        running = False

    screen.blit(background, (0, 0))

    # Bouton Quitter
    boutton_quitter = pygame.Rect(screen_width / 2 - 75, 0, 150, 50)
    border_color = (0, 200, 0)
    border_width = 3
    #pygame.draw.rect(screen, border_color, boutton_quitter, width=border_width)

    # Bouton 1
    boutton_1_centre = (screen_width / 2, screen_height / 5 * 4)
    boutton_1_diam = 100
    border_color = (0, 200, 0)
    border_width = 3
    boutton_1 = pygame.Rect(boutton_1_centre[0]-boutton_1_diam, boutton_1_centre[1]-boutton_1_diam, boutton_1_diam*2, boutton_1_diam*2)
    #pygame.draw.rect(screen, border_color, boutton_1, width=border_width)
    #pygame.draw.circle(screen, border_color, boutton_1_centre, boutton_1_diam, width=border_width)
    sprite_1 = pygame.image.load("app/images/cortex_sprite/sprite1.png")
    sprite_1 = pygame.transform.scale(sprite_1, (boutton_1_diam * 2, boutton_1_diam * 2))
    boutton_1_centre = (boutton_1_centre[0] - boutton_1_diam, boutton_1_centre[1] - boutton_1_diam)
    screen.blit(sprite_1, boutton_1_centre)


    # Afficher le texte "Comment puis-je vous aider" au centre de l'écran
    font = pygame.font.Font(None, 50)  # Police par défaut, taille 50
    text_color = (255, 255, 255)
    text_center = (screen_width // 2, screen_height // 2)
    text = "Comment puis-je vous aider, Que Puis-je faire pour vous ? "

    # Utiliser une variable pour savoir si on doit continuer l'animation du texte
    initialization = True


    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if boutton_quitter.collidepoint(event.pos):
                    running = False
                if boutton_1.collidepoint(event.pos):
                    screen.blit(background, (0, 0))
                    discussion(screen, "", cortex, background, (sprite_1,boutton_1_centre,boutton_1), screen_width, screen_height, (screen_width // 2, screen_height // 2), boutton_quitter)
                    initialization = False
        if initialization == False :
            background_path = os.path.join("app", "images", "backgrounds", "cortex.png")
            try:
                infoObject = pygame.display.Info()
                background = pygame.image.load(background_path)
                background = pygame.transform.scale(background, (infoObject.current_w, infoObject.current_h))
                screen_width = infoObject.current_w
                screen_height = infoObject.current_h
            except pygame.error as e:
                print(f"Erreur lors du chargement de l'image de fond : {e}")
                running = False

            screen.blit(background, (0, 0))

            # Bouton Quitter
            boutton_quitter = pygame.Rect(screen_width / 2 - 75, 0, 150, 50)
            border_color = (0, 200, 0)
            border_width = 3
            # pygame.draw.rect(screen, border_color, boutton_quitter, width=border_width)

            # Bouton 1
            boutton_1_centre = (screen_width / 2, screen_height / 5 * 4)
            boutton_1_diam = 100
            border_color = (0, 200, 0)
            border_width = 3
            boutton_1 = pygame.Rect(boutton_1_centre[0] - boutton_1_diam, boutton_1_centre[1] - boutton_1_diam,
                                    boutton_1_diam * 2, boutton_1_diam * 2)
            # pygame.draw.rect(screen, border_color, boutton_1, width=border_width)
            # pygame.draw.circle(screen, border_color, boutton_1_centre, boutton_1_diam, width=border_width)
            sprite_1 = pygame.image.load("app/images/cortex_sprite/sprite1.png")
            sprite_1 = pygame.transform.scale(sprite_1, (boutton_1_diam * 2, boutton_1_diam * 2))
            boutton_1_centre = (boutton_1_centre[0] - boutton_1_diam, boutton_1_centre[1] - boutton_1_diam)
            screen.blit(sprite_1, boutton_1_centre)
            initialization = True
        pygame.display.flip()
        clock.tick(60)
