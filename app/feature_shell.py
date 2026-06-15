import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from app.screen_assets import load_icon_or_fallback
from app.screen_config import (
    circle_hit_test,
    draw_round_mask,
    env_bool,
    env_fps,
    fit_text,
    pointer_down_position,
    rect_hit_test,
    round_safe_point,
)


FEATURE_CONTENT = {
    "Horloge": ("Aujourd'hui", ["16:45", "Aucune alarme", "Minuteur"]),
    "Musique": ("À l'écoute", ["Lecture locale", "Playlists", "Recommandations"]),
    "Transport": ("Mes trajets", ["Maison → Travail", "État du trafic", "Favoris"]),
    "Santé": ("Bien-être", ["Activité du jour", "Sommeil", "Tendances"]),
    "Réseaux": ("Réseaux sociaux", ["Notifications", "Messages récents", "Temps d'écran"]),
    "Calendrier": ("Planning", ["Prochain événement", "Vue du jour", "Ajouter"]),
    "Messages": ("Messagerie", ["Messages non lus", "Nouveau message", "Contacts"]),
    "Jeux": ("Jeux", ["Jeu rapide", "Scores", "Défis"]),
    "Actualités": ("À la une", ["Résumé du jour", "Technologie", "Favoris"]),
    "Données": ("Jumeau numérique", ["Explorer le graphe", "Relations", "Confidentialité"]),
    "Divertissement": ("Pour vous", ["Films et séries", "Podcasts", "Découvrir"]),
    "Maison": ("Maison", ["Pièces", "Scènes", "Appareils"]),
    "Finance": ("Finances", ["Vue d'ensemble", "Budget", "Alertes"]),
    "Mots de passe": ("Coffre-fort", ["Identifiants", "Sécurité", "Générateur"]),
    "Réglages": ("Réglages", ["Mode de calcul", "Voix et micro", "Connexions"]),
    "Restaurants": ("Restaurants", ["À proximité", "Favoris", "Réserver"]),
    "Vêtements": ("Tenues", ["Suggestions", "Météo", "Garde-robe"]),
    "Éducation": ("Apprendre", ["Continuer", "Révisions", "Découvrir"]),
    "Météo": ("Météo", ["Conditions actuelles", "Prévisions", "Alertes"]),
    "Courses": ("Liste de courses", ["À acheter", "Ajouter un article", "Historique"]),
    "Traduction": ("Traduction", ["Traduire une phrase", "Conversation", "Langues"]),
}

FEATURE_ACCENTS = {
    "Horloge": (167, 139, 250),
    "Musique": (244, 114, 182),
    "Transport": (56, 189, 248),
    "Santé": (251, 113, 133),
    "Réseaux": (192, 132, 252),
    "Calendrier": (249, 115, 22),
    "Messages": (52, 211, 153),
    "Jeux": (239, 68, 68),
    "Actualités": (96, 165, 250),
    "Données": (45, 212, 191),
    "Divertissement": (232, 121, 249),
    "Maison": (129, 140, 248),
    "Finance": (251, 191, 36),
    "Mots de passe": (251, 146, 60),
    "Réglages": (148, 163, 184),
    "Restaurants": (250, 204, 21),
    "Vêtements": (59, 130, 246),
    "Éducation": (132, 204, 22),
    "Météo": (34, 211, 238),
    "Courses": (74, 222, 128),
    "Traduction": (240, 171, 252),
}


def activate_feature_at(cortex, app_name, position, back_center, back_radius, card_rects, cards):
    if circle_hit_test(position, back_center, back_radius):
        return False
    if app_name == "Réglages" and card_rects and rect_hit_test(card_rects[0], position):
        cortex.local_mode = not cortex.local_mode
        cards[0] = "Mode local" if cortex.local_mode else "Mode en ligne"
    return True


def feature_background_cache_key(width, height, center, radius, accent):
    return (
        width,
        height,
        round(center.x, 2),
        round(center.y, 2),
        round(radius, 2),
        tuple(accent),
    )


def make_feature_background_surface(size, center, radius, accent):
    background = pygame.Surface(size)
    background.fill((3, 5, 12))
    pygame.draw.circle(background, (28, 34, 51), center, radius, max(2, int(radius * 0.008)))
    pygame.draw.circle(background, accent, center, radius - 6, 2)
    return background


def launch_feature(screen, cortex, app_name, icon_path):
    clock = pygame.time.Clock()
    title, cards = FEATURE_CONTENT.get(
        app_name,
        (app_name, ["Fonctionnalité en préparation", "Personnaliser", "En savoir plus"]),
    )
    accent = FEATURE_ACCENTS.get(app_name, (88, 214, 255))
    icon = load_icon_or_fallback(icon_path, app_name, accent=accent)
    title_font = pygame.font.SysFont("Segoe UI", 34, bold=True)
    card_font = pygame.font.SysFont("Segoe UI", 22, bold=True)
    small_font = pygame.font.SysFont("Segoe UI", 16)
    running = True
    background_cache_key = None
    background_cache_surface = None

    while running:
        width, height = screen.get_size()
        diameter = min(width, height)
        radius = diameter / 2
        center = pygame.Vector2(width / 2, height / 2)
        next_background_cache_key = feature_background_cache_key(
            width,
            height,
            center,
            radius,
            accent,
        )
        if (
            background_cache_key != next_background_cache_key
            or background_cache_surface is None
        ):
            background_cache_surface = make_feature_background_surface(
                (width, height),
                center,
                radius,
                accent,
            )
            background_cache_key = next_background_cache_key
        screen.blit(background_cache_surface, (0, 0))

        back_radius = max(25, int(radius * 0.075))
        back_center = round_safe_point(
            center,
            radius,
            -0.68,
            -0.68,
            item_radius=back_radius,
            margin=max(6, int(radius * 0.025)),
        )
        pygame.draw.circle(screen, (18, 23, 38), back_center, back_radius)
        pygame.draw.line(
            screen,
            (230, 235, 248),
            (back_center[0] + 6, back_center[1] - 10),
            (back_center[0] - 5, back_center[1]),
            3,
        )
        pygame.draw.line(
            screen,
            (230, 235, 248),
            (back_center[0] - 5, back_center[1]),
            (back_center[0] + 6, back_center[1] + 10),
            3,
        )

        icon_size = int(radius * 0.22)
        icon_scaled = pygame.transform.smoothscale(icon, (icon_size, icon_size))
        icon_rect = icon_scaled.get_rect(center=(center.x, center.y - radius * 0.56))
        pygame.draw.circle(
            screen,
            (*accent, 36),
            icon_rect.center,
            int(icon_size * 0.7),
        )
        screen.blit(icon_scaled, icon_rect)

        heading = title_font.render(
            fit_text(title_font, title, radius * 1.15, ellipsis="…"),
            True,
            (245, 247, 255),
        )
        screen.blit(heading, heading.get_rect(center=(center.x, center.y - radius * 0.34)))

        card_width = radius * 1.28
        card_height = radius * 0.19
        gap = radius * 0.045
        start_y = center.y - radius * 0.08
        card_rects = []
        for index, label in enumerate(cards):
            rect = pygame.Rect(
                center.x - card_width / 2,
                start_y + index * (card_height + gap),
                card_width,
                card_height,
            )
            card_rects.append(rect)
            if index == 0:
                card_fill = accent
                border = accent
                text_color = (255, 255, 255)
                number_color = (255, 255, 255)
            else:
                card_fill = (18, 23, 36)
                border = (43, 51, 71)
                text_color = (236, 239, 248)
                number_color = accent
            pygame.draw.rect(screen, card_fill, rect, border_radius=int(card_height * 0.28))
            pygame.draw.rect(screen, border, rect, 1, border_radius=int(card_height * 0.28))
            number = small_font.render(f"0{index + 1}", True, number_color)
            screen.blit(number, (rect.x + 20, rect.centery - number.get_height() / 2))
            card_label = card_font.render(
                fit_text(card_font, label, card_width - 100, ellipsis="…"),
                True,
                text_color,
            )
            screen.blit(
                card_label,
                (rect.x + 64, rect.centery - card_label.get_height() / 2),
            )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                position = pointer_down_position(event, width, height)
                if position:
                    running = activate_feature_at(
                        cortex,
                        app_name,
                        position,
                        back_center,
                        back_radius,
                        card_rects,
                        cards,
                    )

        mode = "LOCAL" if cortex.local_mode else "EN LIGNE"
        mode_surface = small_font.render(mode, True, accent)
        screen.blit(
            mode_surface,
            mode_surface.get_rect(center=(center.x, center.y + radius * 0.82)),
        )
        draw_round_mask(screen, center, radius)
        pygame.display.flip()
        if env_bool("CORTEX_EXIT_AFTER_FRAME", False):
            running = False
        clock.tick(env_fps())
