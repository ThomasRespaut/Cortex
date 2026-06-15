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
os.environ.setdefault("CORTEX_FULLSCREEN", "false")
os.environ.setdefault("CORTEX_SKIP_CORTEX_LOAD", "true")

import pygame

from Screen import CortexHome
from tools.smoke_legacy_pygame_screens import parse_size

TOUCH_ENV_KEYS = (
    "CORTEX_SCREEN_SIZE",
    "CORTEX_TOUCH_ROTATION",
    "CORTEX_TOUCH_FLIP_X",
    "CORTEX_TOUCH_FLIP_Y",
)


def snapshot_touch_environment():
    return {key: os.environ.get(key) for key in TOUCH_ENV_KEYS}


def restore_touch_environment(snapshot):
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def configure_touch_environment(
    touch_rotation=0,
    touch_flip_x=False,
    touch_flip_y=False,
    size=None,
):
    if size is not None:
        os.environ["CORTEX_SCREEN_SIZE"] = f"{size[0]}x{size[1]}"
    os.environ["CORTEX_TOUCH_ROTATION"] = str(touch_rotation)
    os.environ["CORTEX_TOUCH_FLIP_X"] = "true" if touch_flip_x else "false"
    os.environ["CORTEX_TOUCH_FLIP_Y"] = "true" if touch_flip_y else "false"


def render_home_once(home):
    center, radius = home.viewport()
    home.constrain_offset(radius)
    home.draw_background(center, radius)
    home.draw_apps(center, radius)
    home.draw_status(center, radius)
    home.draw_notice(center, radius)
    pygame.display.flip()


def touch_fraction_for_screen_position(
    position,
    size,
    rotation,
    touch_flip_x=None,
    touch_flip_y=None,
):
    rotation %= 360
    screen_x, screen_y = position
    width, height = size
    if rotation == 90:
        x = screen_y / width
        y = (width - screen_x) / height
    elif rotation == 180:
        x = (width - screen_x) / width
        y = (height - screen_y) / height
    elif rotation == 270:
        x = (height - screen_y) / width
        y = screen_x / height
    else:
        x = screen_x / width
        y = screen_y / height
    if touch_flip_x is None:
        touch_flip_x = os.getenv("CORTEX_TOUCH_FLIP_X", "").lower() in (
            "1",
            "true",
            "yes",
            "on",
            "oui",
        )
    if touch_flip_y is None:
        touch_flip_y = os.getenv("CORTEX_TOUCH_FLIP_Y", "").lower() in (
            "1",
            "true",
            "yes",
            "on",
            "oui",
        )
    if touch_flip_x:
        x = 1 - x
    if touch_flip_y:
        y = 1 - y
    return max(0.0, min(1.0, x)), max(0.0, min(1.0, y))


def finger_event(
    event_type,
    position,
    size,
    finger_id=1,
    touch_rotation=0,
    touch_flip_x=None,
    touch_flip_y=None,
):
    x, y = touch_fraction_for_screen_position(
        position,
        size,
        touch_rotation,
        touch_flip_x=touch_flip_x,
        touch_flip_y=touch_flip_y,
    )
    return pygame.event.Event(
        event_type,
        {
            "x": x,
            "y": y,
            "finger_id": finger_id,
        },
    )


def dispatch_quietly(home, event):
    with contextlib.redirect_stdout(io.StringIO()):
        return home.handle_event(event)


def empty_touch_point(home, size):
    candidates = [
        (size[0] // 2, int(size[1] * 0.22)),
        (int(size[0] * 0.28), size[1] // 2),
        (int(size[0] * 0.72), size[1] // 2),
        (size[0] // 2, int(size[1] * 0.78)),
    ]
    for candidate in candidates:
        if home.app_at(candidate) is None:
            return candidate
    raise RuntimeError("Aucune zone vide disponible pour le double-tap.")


def smoke_home_touch_interactions(
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
        size=size,
    )
    try:
        home = CortexHome()
        render_home_once(home)
        if not home.rendered_apps:
            raise RuntimeError("Aucune app rendue sur le menu principal.")

        app, position, _ = home.rendered_apps[-1]
        start = (int(position.x), int(position.y))

        dispatch_quietly(
            home,
            finger_event(pygame.FINGERDOWN, start, size, touch_rotation=touch_rotation),
        )
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERUP, start, size, touch_rotation=touch_rotation),
        )
        if home.notice_text != "Aperçu: Cortex non chargé":
            raise RuntimeError("Le tap tactile sur une app indisponible n'affiche pas de notice.")
        home.notice_text = ""
        dispatch_quietly(
            home,
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {"button": 1, "pos": start, "touch": True},
            ),
        )
        dispatch_quietly(
            home,
            pygame.event.Event(
                pygame.MOUSEBUTTONUP,
                {"button": 1, "pos": start, "touch": True},
            ),
        )
        if home.notice_text:
            raise RuntimeError("Un événement souris synthétique tactile relance une app.")

        home.offset.update(0, 0)
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERDOWN, start, size, touch_rotation=touch_rotation),
        )
        dispatch_quietly(
            home,
            finger_event(
                pygame.FINGERMOTION,
                (1, 1),
                size,
                touch_rotation=touch_rotation,
            ),
        )
        if not home.panning or home.offset.length() <= 0:
            raise RuntimeError("Un drag tactile vers le bord rond ne déplace pas la grille.")
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERUP, start, size, touch_rotation=touch_rotation),
        )

        home.offset.update(0, 0)
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERDOWN, start, size, touch_rotation=touch_rotation),
        )
        dispatch_quietly(
            home,
            finger_event(
                pygame.FINGERMOTION,
                (start[0] + 48, start[1]),
                size,
                touch_rotation=touch_rotation,
            ),
        )
        if not home.panning:
            raise RuntimeError("Le drag tactile du menu principal ne démarre pas le pan.")
        if home.offset.length() <= 0:
            raise RuntimeError("Le drag tactile du menu principal ne déplace pas la grille.")
        if home.selected is not None:
            raise RuntimeError("La sélection d'app reste active pendant un drag.")
        dispatch_quietly(
            home,
            finger_event(
                pygame.FINGERUP,
                (start[0] + 48, start[1]),
                size,
                touch_rotation=touch_rotation,
            ),
        )

        home.offset.update(0, 0)
        home.zoom = 1.0
        center = (size[0] // 2, size[1] // 2)
        left = (center[0] - 45, center[1])
        right = (center[0] + 45, center[1])
        wider = (center[0] + 95, center[1])
        dispatch_quietly(
            home,
            finger_event(
                pygame.FINGERDOWN,
                left,
                size,
                finger_id=1,
                touch_rotation=touch_rotation,
            ),
        )
        dispatch_quietly(
            home,
            finger_event(
                pygame.FINGERDOWN,
                right,
                size,
                finger_id=2,
                touch_rotation=touch_rotation,
            ),
        )
        dispatch_quietly(
            home,
            finger_event(
                pygame.FINGERMOTION,
                wider,
                size,
                finger_id=2,
                touch_rotation=touch_rotation,
            ),
        )
        if home.zoom <= 1.0:
            raise RuntimeError("Le pinch tactile du menu principal ne zoome pas.")
        if home.dragging:
            raise RuntimeError("Le pinch tactile laisse un drag actif.")
        dispatch_quietly(
            home,
            finger_event(
                pygame.FINGERUP,
                wider,
                size,
                finger_id=2,
                touch_rotation=touch_rotation,
            ),
        )
        dispatch_quietly(
            home,
            finger_event(
                pygame.FINGERMOTION,
                (left[0] - 40, left[1]),
                size,
                finger_id=1,
                touch_rotation=touch_rotation,
            ),
        )
        if not home.panning or home.offset.length() <= 0:
            raise RuntimeError("Le pan ne reprend pas après un pinch tactile.")
        dispatch_quietly(
            home,
            finger_event(
                pygame.FINGERUP,
                left,
                size,
                finger_id=1,
                touch_rotation=touch_rotation,
            ),
        )

        render_home_once(home)
        empty = empty_touch_point(home, size)
        home.offset.update(36, -24)
        home.velocity.update(6, 2)
        home.zoom = 1.18
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERDOWN, empty, size, touch_rotation=touch_rotation),
        )
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERUP, empty, size, touch_rotation=touch_rotation),
        )
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERDOWN, empty, size, touch_rotation=touch_rotation),
        )
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERUP, empty, size, touch_rotation=touch_rotation),
        )
        if home.offset.length() > 0 or home.velocity.length() > 0 or home.zoom != 1.0:
            raise RuntimeError("Le double-tap vide ne recentre pas le menu principal.")
    finally:
        pygame.quit()
        restore_touch_environment(previous_env)
    return app.name


def parse_args():
    parser = argparse.ArgumentParser(
        description="Vérifie les interactions tactiles de base du menu Screen.py."
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
        type=int,
        choices=(0, 90, 180, 270),
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
        app_name = smoke_home_touch_interactions(
            args.size,
            args.touch_rotation,
            touch_flip_x=args.touch_flip_x,
            touch_flip_y=args.touch_flip_y,
        )
    except Exception as error:
        print(f"Smoke interactions menu principal échoué: {error}")
        return 1

    print(f"Smoke interactions menu principal OK: {app_name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
