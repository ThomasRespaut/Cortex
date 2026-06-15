import argparse
import os
import sys
from dataclasses import dataclass
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

from app.app_bdd import launch_bdd
from app.app_calendrier import launch_calendar
from app.app_horloge import launch_clock
from app.app_jeu import launch_game
from app.app_message import launch_messaging
from app.app_musique import launch_music
from app.app_reglage import launch_reglage
from app.app_sante import launch_health
from app.app_transport import launch_transport
from tools.verify_screen_smoke import format_screen_stats, validate_screen_image


@dataclass(frozen=True)
class ScreenSpec:
    name: str
    launcher: object


class EdgeMap(dict):
    def __iter__(self):
        return iter(self.keys())


class SmokeGraph:
    def __init__(self):
        self.nodes = {
            0: {"label": "Thomas Respaut"},
            1: {"label": "Cortex"},
            2: {"label": "Raspberry Pi"},
            3: {"label": "Ecran tactile"},
        }
        self.edges = EdgeMap(
            {
                (0, 1): {"label": "utilise"},
                (0, 2): {"label": "installe"},
                (1, 3): {"label": "affiche"},
            }
        )

    def neighbors(self, node_id):
        return [target for source, target in self.edges if source == node_id]


class SmokeDatabase:
    def _initialiser_graphe(self):
        graph = SmokeGraph()
        noeuds = {}
        node_id_map = {}
        noeud_principal_id = 0
        positions = {
            0: (0, 0),
            1: (140, -80),
            2: (-120, 110),
            3: (70, 145),
        }
        return graph, noeuds, node_id_map, noeud_principal_id, positions


SCREEN_SPECS = [
    ScreenSpec("bdd", launch_bdd),
    ScreenSpec("calendrier", launch_calendar),
    ScreenSpec("horloge", launch_clock),
    ScreenSpec("jeu", launch_game),
    ScreenSpec("message", launch_messaging),
    ScreenSpec("musique", launch_music),
    ScreenSpec("reglage", launch_reglage),
    ScreenSpec("sante", launch_health),
    ScreenSpec("transport", launch_transport),
]


class DummyCortex:
    local_mode = True
    db = SmokeDatabase()


def parse_size(value):
    normalized = value.lower().replace("*", "x")
    if "x" not in normalized:
        raise argparse.ArgumentTypeError("Format attendu: largeurxhauteur")
    width_text, height_text = normalized.split("x", 1)
    try:
        width = int(width_text)
        height = int(height_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("La taille doit contenir deux entiers") from error
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("La taille doit être positive")
    return width, height


def smoke_screen(spec, output_dir, size, require_round_mask=False):
    width, height = size
    screen = pygame.display.set_mode(size)
    screen.fill((0, 0, 0))
    pygame.event.clear()
    spec.launcher(screen, DummyCortex(), width, height)
    output_path = output_dir / f"{spec.name}.png"
    pygame.image.save(screen, output_path)
    return output_path, validate_screen_image(
        output_path,
        min_width=width,
        min_height=height,
        require_round_mask=require_round_mask,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Capture et vérifie les anciens sous-écrans Pygame en mode headless."
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/legacy-screen-smoke",
        help="Dossier de sortie des captures PNG.",
    )
    parser.add_argument(
        "--size",
        default="480x480",
        type=parse_size,
        help="Taille de surface Pygame à tester, par exemple 480x480.",
    )
    parser.add_argument(
        "--require-round-mask",
        action="store_true",
        help="Vérifie que les captures des anciens écrans ont les coins noirs.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    failures = []
    pygame.init()
    try:
        for spec in SCREEN_SPECS:
            try:
                output_path, stats = smoke_screen(
                    spec,
                    output_dir,
                    args.size,
                    require_round_mask=args.require_round_mask,
                )
                print(
                    f"{spec.name}: {output_path} "
                    f"({format_screen_stats(stats)})"
                )
            except Exception as error:
                failures.append(f"{spec.name}: {error}")
    finally:
        pygame.quit()
    if failures:
        print("Smoke legacy Pygame échoué:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
