import argparse
import os
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("CORTEX_EXIT_AFTER_FRAME", "true")

import pygame

from Screen import APP_DEFINITIONS
from app.app_cortex import launch_cortex
from app.feature_shell import launch_feature
from tools.smoke_legacy_pygame_screens import parse_size
from tools.verify_screen_smoke import validate_screen_image


@dataclass(frozen=True)
class ModernScreenSpec:
    name: str
    app_name: str
    icon_path: str | None = None


def screen_slug(value):
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return "_".join(ascii_text.lower().split())


FEATURE_SPECS = [
    ModernScreenSpec(
        name=screen_slug(app_name),
        app_name=app_name,
        icon_path=os.path.join("app", "Images", "app_icons_v2", filename),
    )
    for app_name, filename in APP_DEFINITIONS
    if app_name != "Cortex"
]


class DummyCortex:
    input_mode = "text"
    output_mode = "text"
    first_keyword_detection = False
    local_mode = True

    def keyword_detection(self):
        return None

    def wait_for_response(self):
        return None

    def generate_text(self, prompt):
        return f"Réponse smoke: {prompt}"

    def generate_speech(self, response):
        return None

    def play_audio(self, audio_stream):
        return None


def smoke_cortex(output_dir, size, require_round_mask=False):
    width, height = size
    screen = pygame.display.set_mode(size)
    screen.fill((0, 0, 0))
    pygame.event.clear()
    launch_cortex(screen, DummyCortex(), width, height)
    output_path = output_dir / "cortex.png"
    pygame.image.save(screen, output_path)
    return output_path, validate_screen_image(
        output_path,
        min_width=width,
        min_height=height,
        require_round_mask=require_round_mask,
    )


def smoke_feature(spec, output_dir, size, require_round_mask=False):
    width, height = size
    screen = pygame.display.set_mode(size)
    screen.fill((0, 0, 0))
    pygame.event.clear()
    launch_feature(screen, DummyCortex(), spec.app_name, spec.icon_path)
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
        description="Capture et vérifie les vues Pygame modernes en mode headless."
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/modern-screen-smoke",
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
        help="Vérifie que les captures des vues modernes ont les coins noirs.",
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
        try:
            output_path, stats = smoke_cortex(
                output_dir,
                args.size,
                require_round_mask=args.require_round_mask,
            )
            print(
                f"cortex: {output_path} "
                f"({stats['width']}x{stats['height']}, {stats['unique_colors']} couleurs)"
            )
        except Exception as error:
            failures.append(f"cortex: {error}")

        for spec in FEATURE_SPECS:
            try:
                output_path, stats = smoke_feature(
                    spec,
                    output_dir,
                    args.size,
                    require_round_mask=args.require_round_mask,
                )
                print(
                    f"{spec.name}: {output_path} "
                    f"({stats['width']}x{stats['height']}, {stats['unique_colors']} couleurs)"
                )
            except Exception as error:
                failures.append(f"{spec.name}: {error}")
    finally:
        pygame.quit()

    if failures:
        print("Smoke modern Pygame échoué:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
