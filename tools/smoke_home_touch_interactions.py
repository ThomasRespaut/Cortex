import argparse
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


def smoke_home_touch_interactions(size):
    os.environ["CORTEX_SCREEN_SIZE"] = f"{size[0]}x{size[1]}"
    home = CortexHome()
    try:
        render_home_once(home)
        if not home.rendered_apps:
            raise RuntimeError("Aucune app rendue sur le menu principal.")

        app, position, _ = home.rendered_apps[-1]
        start = (int(position.x), int(position.y))

        home.handle_pointer_down(start)
        home.handle_pointer_up(start)
        if home.notice_text != "Aperçu: Cortex non chargé":
            raise RuntimeError("Le tap sur une app indisponible n'affiche pas de notice.")

        home.handle_pointer_down(start)
        home.handle_pointer_move((start[0] + 48, start[1]))
        if not home.panning:
            raise RuntimeError("Le drag du menu principal ne démarre pas le pan.")
        if home.offset.length() <= 0:
            raise RuntimeError("Le drag du menu principal ne déplace pas la grille.")
        if home.selected is not None:
            raise RuntimeError("La sélection d'app reste active pendant un drag.")
        home.handle_pointer_up((start[0] + 48, start[1]))
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
