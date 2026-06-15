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
os.environ.setdefault("CORTEX_EXIT_AFTER_FRAME", "true")

from tools.smoke_home_touch_interactions import smoke_home_touch_interactions
from tools.smoke_legacy_pygame_screens import parse_size
from tools.smoke_modern_touch_interactions import smoke_modern_touch_interactions


TOUCH_ROTATIONS = (0, 90, 180, 270)


def smoke_touch_rotations(size, rotations=TOUCH_ROTATIONS):
    checked = []
    for rotation in rotations:
        smoke_home_touch_interactions(size, touch_rotation=rotation)
        smoke_modern_touch_interactions(size, touch_rotation=rotation)
        checked.append(rotation)
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
        rotations = smoke_touch_rotations(args.size)
    except Exception as error:
        print(f"Smoke rotations tactiles échoué: {error}")
        return 1

    labels = ", ".join(str(rotation) for rotation in rotations)
    print(f"Smoke rotations tactiles OK: {labels}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
