import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ValidationStep:
    name: str
    command: list[str]
    env: dict[str, str] = field(default_factory=dict)


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


def relative_or_absolute(path):
    return str(path) if Path(path).is_absolute() else path


def build_validation_steps(
    python_bin,
    project_root,
    size,
    screenshot,
    legacy_output_dir,
    modern_output_dir,
):
    width, height = size
    screen_size = f"{width}x{height}"
    min_width = str(min(width, 400))
    min_height = str(min(height, 400))

    return [
        ValidationStep(
            "Préflight Raspberry Pi",
            [
                python_bin,
                "tools/raspberry_pi_preflight.py",
                "--project-root",
                project_root,
            ],
        ),
        ValidationStep(
            "Capture Screen.py headless",
            [python_bin, "Screen.py"],
            env={
                "SDL_VIDEODRIVER": "dummy",
                "CORTEX_FULLSCREEN": "false",
                "CORTEX_SCREEN_SIZE": screen_size,
                "CORTEX_SKIP_CORTEX_LOAD": "true",
                "CORTEX_SCREENSHOT_PATH": relative_or_absolute(screenshot),
                "CORTEX_EXIT_AFTER_SCREENSHOT": "true",
            },
        ),
        ValidationStep(
            "Validation capture Screen.py",
            [
                python_bin,
                "tools/verify_screen_smoke.py",
                relative_or_absolute(screenshot),
                "--min-width",
                min_width,
                "--min-height",
                min_height,
                "--require-round-mask",
            ],
        ),
        ValidationStep(
            "Préflight avec capture",
            [
                python_bin,
                "tools/raspberry_pi_preflight.py",
                "--project-root",
                project_root,
                "--screenshot",
                relative_or_absolute(screenshot),
            ],
        ),
        ValidationStep(
            "Interactions tactiles menu principal",
            [
                python_bin,
                "tools/smoke_home_touch_interactions.py",
                "--size",
                screen_size,
            ],
        ),
        ValidationStep(
            "Interactions tactiles écrans modernes",
            [
                python_bin,
                "tools/smoke_modern_touch_interactions.py",
                "--size",
                screen_size,
            ],
        ),
        ValidationStep(
            "Smokes anciens écrans Pygame",
            [
                python_bin,
                "tools/smoke_legacy_pygame_screens.py",
                "--size",
                screen_size,
                "--output-dir",
                relative_or_absolute(legacy_output_dir),
                "--require-round-mask",
            ],
        ),
        ValidationStep(
            "Smokes écrans Pygame modernes",
            [
                python_bin,
                "tools/smoke_modern_pygame_screens.py",
                "--size",
                screen_size,
                "--output-dir",
                relative_or_absolute(modern_output_dir),
                "--require-round-mask",
            ],
        ),
    ]


def run_step(step, project_root):
    print(f"\n==> {step.name}", flush=True)
    print(" ".join(step.command), flush=True)
    env = os.environ.copy()
    env.update(step.env)
    result = subprocess.run(step.command, cwd=project_root, env=env, check=False)
    if result.returncode != 0:
        print(f"Étape échouée: {step.name} ({result.returncode})")
    return result.returncode


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Exécute la validation headless Raspberry Pi/Pygame complète "
            "pour l'écran circulaire tactile."
        )
    )
    parser.add_argument("--project-root", default=".", help="Racine du projet Cortex.")
    parser.add_argument(
        "--size",
        default="480x480",
        type=parse_size,
        help="Taille cible de l'écran tactile, par exemple 480x480.",
    )
    parser.add_argument(
        "--screenshot",
        default="artifacts/screen-smoke.png",
        help="Capture Screen.py générée puis validée.",
    )
    parser.add_argument(
        "--legacy-output-dir",
        default="artifacts/legacy-screen-smoke",
        help="Dossier des captures des anciens écrans Pygame.",
    )
    parser.add_argument(
        "--modern-output-dir",
        default="artifacts/modern-screen-smoke",
        help="Dossier des captures des écrans Pygame modernes.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        print(f"Projet introuvable: {project_root}")
        return 1

    steps = build_validation_steps(
        sys.executable,
        ".",
        args.size,
        args.screenshot,
        args.legacy_output_dir,
        args.modern_output_dir,
    )
    for step in steps:
        returncode = run_step(step, project_root)
        if returncode != 0:
            return returncode

    print("\nValidation Raspberry Pi/Pygame OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
