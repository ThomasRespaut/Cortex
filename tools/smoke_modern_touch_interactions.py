import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_TOUCH_MOUSE_EVENTS", "0")
os.environ.setdefault("SDL_MOUSE_TOUCH_EVENTS", "0")
os.environ.setdefault("CORTEX_EXIT_AFTER_FRAME", "true")

import pygame

from app.app_cortex import CortexView
from app.feature_shell import launch_feature
from app.screen_config import pointer_down_position
from tools.smoke_home_touch_interactions import (
    configure_touch_environment,
    restore_touch_environment,
    snapshot_touch_environment,
    touch_fraction_for_screen_position,
)
from tools.screen_size import parse_square_screen_size as parse_size
from tools.touch_config import parse_touch_rotation


class DummyCortex:
    input_mode = "text"
    output_mode = "text"
    first_keyword_detection = False
    local_mode = True

    def generate_text(self, prompt):
        return f"Réponse smoke: {prompt}"

    def generate_speech(self, response):
        return None

    def play_audio(self, audio_stream):
        return None


def finger_down(position, size, touch_rotation=0, touch_flip_x=False, touch_flip_y=False):
    x, y = touch_fraction_for_screen_position(
        position,
        size,
        touch_rotation,
        touch_flip_x=touch_flip_x,
        touch_flip_y=touch_flip_y,
    )
    return pygame.event.Event(
        pygame.FINGERDOWN,
        {
            "x": x,
            "y": y,
            "finger_id": 1,
        },
    )


def pointer_from_finger(
    position,
    size,
    touch_rotation=0,
    touch_flip_x=False,
    touch_flip_y=False,
):
    event = finger_down(
        position,
        size,
        touch_rotation,
        touch_flip_x=touch_flip_x,
        touch_flip_y=touch_flip_y,
    )
    pointer = pointer_down_position(event, size[0], size[1])
    if pointer is None:
        raise RuntimeError(f"Position tactile rejetée: {position}")
    return pointer


def smoke_cortex_touch(
    screen,
    size,
    touch_rotation=0,
    touch_flip_x=False,
    touch_flip_y=False,
):
    view = CortexView(screen, DummyCortex())
    prompts = []
    view.run_query = lambda prompt=None: prompts.append(prompt)

    center, radius = view.viewport()
    view.draw_background(center, radius)
    back_center, back_radius = view.draw_back_button(center, radius)
    view.draw_header(center, radius)
    orb_center, orb_radius = view.draw_orb(center, radius)
    view.draw_conversation_card(center, radius)
    suggestion_rects = view.draw_suggestions(center, radius)

    suggestion_position = suggestion_rects[0][0].center
    view.activate_at(
        pointer_from_finger(
            suggestion_position,
            size,
            touch_rotation,
            touch_flip_x=touch_flip_x,
            touch_flip_y=touch_flip_y,
        ),
        back_center,
        back_radius,
        orb_center,
        orb_radius,
        suggestion_rects,
    )
    if prompts != [suggestion_rects[0][1]]:
        raise RuntimeError("Le tap tactile sur une suggestion Cortex ne lance pas la requête.")

    view.activate_at(
        pointer_from_finger(
            back_center,
            size,
            touch_rotation,
            touch_flip_x=touch_flip_x,
            touch_flip_y=touch_flip_y,
        ),
        back_center,
        back_radius,
        orb_center,
        orb_radius,
        suggestion_rects,
    )
    if view.running:
        raise RuntimeError("Le tap tactile sur retour Cortex ne ferme pas la vue.")


def smoke_feature_touch(
    screen,
    size,
    touch_rotation=0,
    touch_flip_x=False,
    touch_flip_y=False,
):
    cortex = DummyCortex()
    width, height = size
    radius = min(width, height) / 2
    center = pygame.Vector2(width / 2, height / 2)
    card_height = radius * 0.19
    first_card_center = (center.x, center.y - radius * 0.08 + card_height / 2)

    pygame.event.clear()
    pygame.event.post(
        finger_down(
            first_card_center,
            size,
            touch_rotation,
            touch_flip_x=touch_flip_x,
            touch_flip_y=touch_flip_y,
        )
    )
    launch_feature(
        screen,
        cortex,
        "Réglages",
        os.path.join("app", "Images", "app_icons_v2", "icone_reglage.png"),
    )
    if cortex.local_mode:
        raise RuntimeError("Le tap tactile sur Réglages ne bascule pas le mode local.")


def smoke_modern_touch_interactions(
    size,
    touch_rotation=0,
    touch_flip_x=False,
    touch_flip_y=False,
):
    previous_env = snapshot_touch_environment()
    configure_touch_environment(
        touch_rotation,
        touch_flip_x=touch_flip_x,
        touch_flip_y=touch_flip_y,
    )
    pygame.init()
    try:
        screen = pygame.display.set_mode(size)
        smoke_cortex_touch(
            screen,
            size,
            touch_rotation,
            touch_flip_x=touch_flip_x,
            touch_flip_y=touch_flip_y,
        )
        smoke_feature_touch(
            screen,
            size,
            touch_rotation,
            touch_flip_x=touch_flip_x,
            touch_flip_y=touch_flip_y,
        )
    finally:
        pygame.quit()
        restore_touch_environment(previous_env)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Vérifie les interactions tactiles des écrans Pygame modernes."
    )
    parser.add_argument(
        "--size",
        default="480x480",
        type=parse_size,
        help="Taille de surface Pygame à tester, par exemple 480x480.",
    )
    parser.add_argument(
        "--touch-rotation",
        default=0,
        type=parse_touch_rotation,
        help="Rotation tactile Cortex à valider.",
    )
    parser.add_argument(
        "--touch-flip-x",
        action="store_true",
        help="Valide le tactile avec l'axe X brut inversé.",
    )
    parser.add_argument(
        "--touch-flip-y",
        action="store_true",
        help="Valide le tactile avec l'axe Y brut inversé.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        smoke_modern_touch_interactions(
            args.size,
            args.touch_rotation,
            touch_flip_x=args.touch_flip_x,
            touch_flip_y=args.touch_flip_y,
        )
    except Exception as error:
        print(f"Smoke interactions modernes échoué: {error}")
        return 1

    print("Smoke interactions modernes OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
