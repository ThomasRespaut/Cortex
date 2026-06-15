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
os.environ.setdefault("CORTEX_FULLSCREEN", "false")
os.environ.setdefault("CORTEX_SKIP_CORTEX_LOAD", "true")

import pygame

from Screen import CortexHome
from tools.smoke_legacy_pygame_screens import parse_size


def render_home_once(home):
    center, radius = home.viewport()
    home.constrain_offset(radius)
    home.draw_background(center, radius)
    home.draw_apps(center, radius)
    home.draw_status(center, radius)
    home.draw_notice(center, radius)
    pygame.display.flip()


def finger_event(event_type, position, size, finger_id=1):
    return pygame.event.Event(
        event_type,
        {
            "x": position[0] / size[0],
            "y": position[1] / size[1],
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


def smoke_home_touch_interactions(size):
    os.environ["CORTEX_SCREEN_SIZE"] = f"{size[0]}x{size[1]}"
    home = CortexHome()
    try:
        render_home_once(home)
        if not home.rendered_apps:
            raise RuntimeError("Aucune app rendue sur le menu principal.")

        app, position, _ = home.rendered_apps[-1]
        start = (int(position.x), int(position.y))

        dispatch_quietly(home, finger_event(pygame.FINGERDOWN, start, size))
        dispatch_quietly(home, finger_event(pygame.FINGERUP, start, size))
        if home.notice_text != "Aperçu: Cortex non chargé":
            raise RuntimeError("Le tap tactile sur une app indisponible n'affiche pas de notice.")

        home.offset.update(0, 0)
        dispatch_quietly(home, finger_event(pygame.FINGERDOWN, start, size))
        dispatch_quietly(home, finger_event(pygame.FINGERMOTION, (1, 1), size))
        if home.panning or home.offset.length() > 0:
            raise RuntimeError("Un mouvement tactile hors du cercle déplace la grille.")
        dispatch_quietly(home, finger_event(pygame.FINGERUP, start, size))

        home.offset.update(0, 0)
        dispatch_quietly(home, finger_event(pygame.FINGERDOWN, start, size))
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERMOTION, (start[0] + 48, start[1]), size),
        )
        if not home.panning:
            raise RuntimeError("Le drag tactile du menu principal ne démarre pas le pan.")
        if home.offset.length() <= 0:
            raise RuntimeError("Le drag tactile du menu principal ne déplace pas la grille.")
        if home.selected is not None:
            raise RuntimeError("La sélection d'app reste active pendant un drag.")
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERUP, (start[0] + 48, start[1]), size),
        )

        home.offset.update(0, 0)
        home.zoom = 1.0
        center = (size[0] // 2, size[1] // 2)
        left = (center[0] - 45, center[1])
        right = (center[0] + 45, center[1])
        wider = (center[0] + 95, center[1])
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERDOWN, left, size, finger_id=1),
        )
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERDOWN, right, size, finger_id=2),
        )
        dispatch_quietly(
            home,
            finger_event(pygame.FINGERMOTION, wider, size, finger_id=2),
        )
        if home.zoom <= 1.0:
            raise RuntimeError("Le pinch tactile du menu principal ne zoome pas.")
        if home.dragging:
            raise RuntimeError("Le pinch tactile laisse un drag actif.")
        dispatch_quietly(home, finger_event(pygame.FINGERUP, wider, size, finger_id=2))
        dispatch_quietly(
            home,
            finger_event(
                pygame.FINGERMOTION,
                (left[0] - 40, left[1]),
                size,
                finger_id=1,
            ),
        )
        if not home.panning or home.offset.length() <= 0:
            raise RuntimeError("Le pan ne reprend pas après un pinch tactile.")
        dispatch_quietly(home, finger_event(pygame.FINGERUP, left, size, finger_id=1))

        render_home_once(home)
        empty = empty_touch_point(home, size)
        home.offset.update(36, -24)
        home.velocity.update(6, 2)
        home.zoom = 1.18
        dispatch_quietly(home, finger_event(pygame.FINGERDOWN, empty, size))
        dispatch_quietly(home, finger_event(pygame.FINGERUP, empty, size))
        dispatch_quietly(home, finger_event(pygame.FINGERDOWN, empty, size))
        dispatch_quietly(home, finger_event(pygame.FINGERUP, empty, size))
        if home.offset.length() > 0 or home.velocity.length() > 0 or home.zoom != 1.0:
            raise RuntimeError("Le double-tap vide ne recentre pas le menu principal.")
    finally:
        pygame.quit()
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
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        app_name = smoke_home_touch_interactions(args.size)
    except Exception as error:
        print(f"Smoke interactions menu principal échoué: {error}")
        return 1

    print(f"Smoke interactions menu principal OK: {app_name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
