import math
import os
import threading
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from app.screen_config import (
    env_bool,
    fit_text,
    pointer_down_position,
    round_safe_point,
    wrap_text,
)


BACKGROUND_TOP = (18, 38, 86)
BACKGROUND_BOTTOM = (4, 7, 22)
TEXT = (248, 250, 255)
MUTED = (174, 185, 205)
ACCENT = (74, 196, 255)


SUGGESTIONS = [
    "Résumé du jour",
    "Joue ma musique",
    "Mes prochains RDV",
    "Trajet maison",
]


class CortexView:
    def __init__(self, screen, cortex):
        self.screen = screen
        self.cortex = cortex
        self.clock = pygame.time.Clock()
        self.running = True
        self.status = "ready"
        self.user_text = ""
        self.ai_text = "Touchez l'orbe pour parler à Cortex."
        self.worker = None
        self.error = None
        self.start_time = time.time()
        self.title_font = pygame.font.SysFont("Segoe UI", 34, bold=True)
        self.body_font = pygame.font.SysFont("Segoe UI", 23)
        self.small_font = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.button_font = pygame.font.SysFont("Segoe UI", 18, bold=True)

    def viewport(self):
        width, height = self.screen.get_size()
        radius = min(width, height) / 2
        center = pygame.Vector2(width / 2, height / 2)
        return center, radius

    def draw_background(self, center, radius):
        width, height = self.screen.get_size()
        for y in range(height):
            ratio = y / max(1, height - 1)
            color = tuple(
                int(BACKGROUND_TOP[i] * (1 - ratio) + BACKGROUND_BOTTOM[i] * ratio)
                for i in range(3)
            )
            pygame.draw.line(self.screen, color, (0, y), (width, y))

        glow = pygame.Surface((width, height), pygame.SRCALPHA)
        for step in range(28, 0, -1):
            ratio = step / 28
            alpha = int(42 * (1 - ratio) ** 2)
            pygame.draw.circle(
                glow,
                (78, 140, 255, alpha),
                (center.x - radius * 0.25, center.y - radius * 0.4),
                int(radius * 0.75 * ratio),
            )
            pygame.draw.circle(
                glow,
                (190, 90, 255, int(alpha * 0.65)),
                (center.x + radius * 0.36, center.y - radius * 0.05),
                int(radius * 0.58 * ratio),
            )
            pygame.draw.circle(
                glow,
                (35, 215, 218, int(alpha * 0.48)),
                (center.x, center.y + radius * 0.58),
                int(radius * 0.65 * ratio),
            )
        self.screen.blit(glow, (0, 0))
        pygame.draw.circle(self.screen, (142, 169, 231), center, radius, max(2, int(radius * 0.008)))
        pygame.draw.circle(self.screen, (235, 242, 255), center, radius - 8, 1)

    def draw_back_button(self, center, radius):
        button_radius = max(26, int(radius * 0.07))
        position = round_safe_point(
            center,
            radius,
            -0.72,
            -0.72,
            item_radius=button_radius,
            margin=max(6, int(radius * 0.025)),
        )
        pygame.draw.circle(self.screen, (17, 25, 45), position, button_radius)
        pygame.draw.circle(self.screen, (73, 91, 130), position, button_radius, 1)
        pygame.draw.line(self.screen, TEXT, (position.x + 7, position.y - 11), (position.x - 5, position.y), 3)
        pygame.draw.line(self.screen, TEXT, (position.x - 5, position.y), (position.x + 7, position.y + 11), 3)
        return position, button_radius

    def draw_orb(self, center, radius):
        pulse = (math.sin((time.time() - self.start_time) * 3.2) + 1) / 2
        orb_radius = int(radius * (0.17 + 0.014 * pulse if self.status == "listening" else 0.17))
        orb_center = pygame.Vector2(center.x, center.y - radius * 0.29)

        for step in range(9, 0, -1):
            alpha = int((10 + 9 * pulse) * (1 - step / 10))
            pygame.draw.circle(
                self.screen,
                (78, 205, 255, alpha),
                orb_center,
                int(orb_radius * (1 + step * 0.1)),
            )
        pygame.draw.circle(self.screen, (51, 147, 255), orb_center, orb_radius)
        pygame.draw.circle(self.screen, (128, 91, 255), (orb_center.x, orb_center.y - orb_radius * 0.28), int(orb_radius * 0.83))
        pygame.draw.circle(self.screen, (76, 223, 255), (orb_center.x, orb_center.y + orb_radius * 0.24), int(orb_radius * 0.76))
        pygame.draw.circle(self.screen, (255, 255, 255, 230), orb_center, int(orb_radius * 0.31))

        if self.status == "thinking":
            for index in range(3):
                dot_x = orb_center.x - 22 + index * 22
                dot_y = orb_center.y
                pygame.draw.circle(self.screen, (58, 107, 180), (dot_x, dot_y), 6 + int(3 * pulse))
        else:
            wave_width = int(orb_radius * 0.48)
            for index, height in enumerate((26, 52, 36, 68, 42)):
                x = orb_center.x - wave_width / 2 + index * wave_width / 4
                pygame.draw.line(
                    self.screen,
                    (54, 106, 178),
                    (x, orb_center.y - height / 2),
                    (x, orb_center.y + height / 2),
                    7,
                )

        return orb_center, orb_radius

    def draw_header(self, center, radius):
        title = self.title_font.render("Cortex", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(center.x, center.y - radius * 0.82)))

        if self.status == "listening":
            label = "Écoute en cours"
        elif self.status == "thinking":
            label = "Réflexion..."
        elif self.status == "speaking":
            label = "Réponse prête"
        else:
            label = "Assistant local"
        subtitle = self.small_font.render(label.upper(), True, ACCENT)
        self.screen.blit(subtitle, subtitle.get_rect(center=(center.x, center.y - radius * 0.72)))

    def draw_conversation_card(self, center, radius):
        card_width = radius * 1.32
        card_height = radius * 0.28
        card = pygame.Rect(center.x - card_width / 2, center.y + radius * 0.05, card_width, card_height)
        pygame.draw.rect(self.screen, (12, 20, 39), card, border_radius=int(card_height * 0.18))
        pygame.draw.rect(self.screen, (51, 70, 112), card, 1, border_radius=int(card_height * 0.18))

        label = "Cortex"
        if self.user_text:
            user = self.small_font.render(f"Vous : {fit_text(self.small_font, self.user_text, card_width - 44)}", True, MUTED)
            self.screen.blit(user, (card.x + 24, card.y + 18))
            label_y = card.y + 50
        else:
            label_y = card.y + 22

        speaker = self.small_font.render(label.upper(), True, ACCENT)
        self.screen.blit(speaker, (card.x + 24, label_y))
        lines = wrap_text(self.body_font, self.ai_text, card_width - 48, max_lines=3)
        for index, line in enumerate(lines):
            line_surface = self.body_font.render(line, True, TEXT)
            self.screen.blit(line_surface, (card.x + 24, label_y + 28 + index * 30))

    def draw_suggestions(self, center, radius):
        chip_width = radius * 0.53
        chip_height = radius * 0.105
        start_x = center.x - chip_width - radius * 0.035
        start_y = center.y + radius * 0.42
        rects = []
        for index, suggestion in enumerate(SUGGESTIONS):
            x = start_x + (index % 2) * (chip_width + radius * 0.07)
            y = start_y + (index // 2) * (chip_height + radius * 0.045)
            rect = pygame.Rect(x, y, chip_width, chip_height)
            rects.append((rect, suggestion))
            pygame.draw.rect(self.screen, (21, 31, 55), rect, border_radius=int(chip_height * 0.48))
            pygame.draw.rect(self.screen, (57, 78, 122), rect, 1, border_radius=int(chip_height * 0.48))
            text = self.button_font.render(fit_text(self.button_font, suggestion, chip_width - 24), True, TEXT)
            self.screen.blit(text, text.get_rect(center=rect.center))
        return rects

    def run_query(self, prompt=None):
        if self.worker and self.worker.is_alive():
            return

        def worker():
            try:
                self.status = "listening"
                if prompt is None:
                    if self.cortex.input_mode == "voice":
                        if self.cortex.first_keyword_detection:
                            self.cortex.keyword_detection()
                            self.cortex.first_keyword_detection = False
                        user_response = self.cortex.wait_for_response()
                    else:
                        user_response = prompt
                else:
                    user_response = prompt

                if not user_response:
                    self.status = "ready"
                    self.ai_text = "Je n'ai pas entendu de question. Touchez l'orbe pour réessayer."
                    return

                self.user_text = user_response
                self.status = "thinking"
                response = self.cortex.generate_text(user_response)
                self.ai_text = response or "Je n'ai pas encore de réponse fiable."
                self.status = "speaking"
                if self.cortex.output_mode == "voice" and response:
                    audio_stream = self.cortex.generate_speech(response)
                    if audio_stream and audio_stream != -1:
                        self.cortex.play_audio(audio_stream)
                self.status = "ready"
            except Exception as error:
                self.error = str(error)
                self.ai_text = f"Erreur : {error}"
                self.status = "ready"

        self.worker = threading.Thread(target=worker, name="cortex-query", daemon=True)
        self.worker.start()

    def activate_at(
        self,
        position,
        back_center,
        back_radius,
        orb_center,
        orb_radius,
        suggestion_rects,
    ):
        pos = pygame.Vector2(position)
        if pos.distance_to(back_center) <= back_radius:
            self.running = False
            return
        if pos.distance_to(orb_center) <= orb_radius:
            self.run_query()
            return
        for rect, suggestion in suggestion_rects:
            if rect.collidepoint(position):
                self.run_query(suggestion)
                return

    def run(self):
        while self.running:
            center, radius = self.viewport()
            self.draw_background(center, radius)
            back_center, back_radius = self.draw_back_button(center, radius)
            self.draw_header(center, radius)
            orb_center, orb_radius = self.draw_orb(center, radius)
            self.draw_conversation_card(center, radius)
            suggestion_rects = self.draw_suggestions(center, radius)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    width, height = self.screen.get_size()
                    pointer = pointer_down_position(event, width, height)
                    if pointer:
                        self.activate_at(
                            pointer,
                            back_center,
                            back_radius,
                            orb_center,
                            orb_radius,
                            suggestion_rects,
                        )

            pygame.display.flip()
            if env_bool("CORTEX_EXIT_AFTER_FRAME", False):
                self.running = False
            self.clock.tick(60)


def launch_cortex(screen, cortex, screen_width, screen_height):
    CortexView(screen, cortex).run()
