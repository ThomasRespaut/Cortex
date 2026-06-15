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
os.environ.setdefault("CORTEX_FULLSCREEN", "false")
os.environ.setdefault("CORTEX_SKIP_CORTEX_LOAD", "true")
os.environ.setdefault("CORTEX_EXIT_AFTER_FRAME", "true")

from tools.smoke_home_touch_interactions import smoke_home_touch_interactions
from tools.smoke_legacy_pygame_screens import parse_size
from tools.smoke_legacy_touch_interactions import smoke_legacy_touch_interactions
from tools.smoke_modern_touch_interactions import smoke_modern_touch_interactions


TOUCH_ROTATIONS = (0, 90, 180, 270)
TOUCH_FLIP_CASES = (
    (False, False),
    (True, False),
    (False, True),
    (True, True),
)


def smoke_touch_rotations(size, rotations=TOUCH_ROTATIONS, flip_cases=TOUCH_FLIP_CASES):
    checked = []
    for rotation in rotations:
        for flip_x, flip_y in flip_cases:
            smoke_home_touch_interactions(
                size,
                touch_rotation=rotation,
                touch_flip_x=flip_x,
                touch_flip_y=flip_y,
            )
            smoke_modern_touch_interactions(
                size,
                touch_rotation=rotation,
                touch_flip_x=flip_x,
                touch_flip_y=flip_y,
            )
            smoke_legacy_touch_interactions(
                size,
                touch_rotation=rotation,
                touch_flip_x=flip_x,
                touch_flip_y=flip_y,
            )
            checked.append((rotation, flip_x, flip_y))
    return checked


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Vérifie les interactions tactiles Pygame sur toutes les rotations "
            "utiles d'un écran circulaire Raspberry Pi."
        )
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
        cases = smoke_touch_rotations(args.size)
    except Exception as error:
        print(f"Smoke rotations tactiles échoué: {error}")
        return 1

    labels = ", ".join(
        f"{rotation}/flipX={str(flip_x).lower()}/flipY={str(flip_y).lower()}"
        for rotation, flip_x, flip_y in cases
    )
    print(f"Smoke rotations tactiles OK: {labels}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
