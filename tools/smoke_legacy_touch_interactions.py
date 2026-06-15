import argparse
import contextlib
import io
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

from app.app_reglage import launch_reglage
from app.screen_config import circular_menu_layout
from tools.smoke_home_touch_interactions import (
    configure_touch_environment,
    restore_touch_environment,
    snapshot_touch_environment,
    touch_fraction_for_screen_position,
)
from tools.screen_size import parse_square_screen_size as parse_size
from tools.screen_size import require_square_screen_size
from tools.touch_config import parse_touch_rotation


class DummyCortex:
    def __init__(self, local_mode=True):
        self.local_mode = local_mode


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


def run_settings_with_event(screen, size, event, local_mode=True):
    cortex = DummyCortex(local_mode=local_mode)
    pygame.event.clear()
    pygame.event.post(event)
    with contextlib.redirect_stdout(io.StringIO()):
        is_online = launch_reglage(screen, cortex, size[0], size[1])
    return cortex.local_mode, is_online


def smoke_legacy_touch_interactions(
    size,
    touch_rotation=0,
    touch_flip_x=False,
    touch_flip_y=False,
):
    size = require_square_screen_size(size)
    previous_env = snapshot_touch_environment()
    configure_touch_environment(
        touch_rotation,
        touch_flip_x=touch_flip_x,
        touch_flip_y=touch_flip_y,
    )

    _, menu_buttons = circular_menu_layout(size[0], size[1], item_count=1)
    toggle_position = menu_buttons[0].center

    pygame.init()
    try:
        screen = pygame.display.set_mode(size)
        local_mode, is_online = run_settings_with_event(
            screen,
            size,
            finger_down(
                toggle_position,
                size,
                touch_rotation=touch_rotation,
                touch_flip_x=touch_flip_x,
                touch_flip_y=touch_flip_y,
            ),
            local_mode=True,
        )
        if local_mode or not is_online:
            raise RuntimeError("Le tap tactile Réglages ne bascule pas le mode local.")

        local_mode, is_online = run_settings_with_event(
            screen,
            size,
            finger_down(
                toggle_position,
                size,
                touch_rotation=touch_rotation,
                touch_flip_x=touch_flip_x,
                touch_flip_y=touch_flip_y,
            ),
            local_mode=False,
        )
        if not local_mode or is_online:
            raise RuntimeError("Le tap tactile Réglages ne rebascule pas en mode local.")

        local_mode, is_online = run_settings_with_event(
            screen,
            size,
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {
                    "button": 1,
                    "pos": toggle_position,
                    "touch": True,
                },
            ),
            local_mode=True,
        )
        if not local_mode or is_online:
            raise RuntimeError(
                "Un événement souris synthétique tactile bascule les Réglages."
            )
    finally:
        pygame.quit()
        restore_touch_environment(previous_env)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Vérifie les interactions tactiles des anciens écrans Pygame."
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
        smoke_legacy_touch_interactions(
            args.size,
            args.touch_rotation,
            touch_flip_x=args.touch_flip_x,
            touch_flip_y=args.touch_flip_y,
        )
    except Exception as error:
        print(f"Smoke interactions anciens écrans échoué: {error}")
        return 1

    print("Smoke interactions anciens écrans OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
