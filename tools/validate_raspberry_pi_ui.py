import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.screen_size import parse_screen_size
from tools.touch_config import parse_touch_rotation


@dataclass(frozen=True)
class ValidationStep:
    name: str
    command: list[str]
    env: dict[str, str] = field(default_factory=dict)


parse_size = parse_screen_size


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("La valeur doit être un entier") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("La valeur doit être positive")
    return parsed


touch_rotation = parse_touch_rotation


def relative_or_absolute(path):
    return str(path) if Path(path).is_absolute() else path


def pygame_headless_env(screen_size, **extra):
    env = {
        "SDL_VIDEODRIVER": "dummy",
        "SDL_TOUCH_MOUSE_EVENTS": "0",
        "SDL_MOUSE_TOUCH_EVENTS": "0",
        "CORTEX_FULLSCREEN": "false",
        "CORTEX_SCREEN_SIZE": screen_size,
        "CORTEX_SKIP_CORTEX_LOAD": "true",
    }
    env.update(extra)
    return env


def build_validation_steps(
    python_bin,
    project_root,
    size,
    screenshot,
    legacy_output_dir,
    modern_output_dir,
    touch_rotation=0,
    touch_flip_x=False,
    touch_flip_y=False,
):
    width, height = size
    screen_size = f"{width}x{height}"
    min_width = str(min(width, 400))
    min_height = str(min(height, 400))
    touch_env = {
        "CORTEX_TOUCH_ROTATION": str(touch_rotation),
        "CORTEX_TOUCH_FLIP_X": "true" if touch_flip_x else "false",
        "CORTEX_TOUCH_FLIP_Y": "true" if touch_flip_y else "false",
    }

    def touch_command(script):
        command = [
            python_bin,
            script,
            "--size",
            screen_size,
            "--touch-rotation",
            str(touch_rotation),
        ]
        if touch_flip_x:
            command.append("--touch-flip-x")
        if touch_flip_y:
            command.append("--touch-flip-y")
        return command

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
            env=pygame_headless_env(
                screen_size,
                **touch_env,
                CORTEX_SCREENSHOT_PATH=relative_or_absolute(screenshot),
                CORTEX_EXIT_AFTER_SCREENSHOT="true",
            ),
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
            touch_command("tools/smoke_home_touch_interactions.py"),
            env=pygame_headless_env(screen_size, **touch_env),
        ),
        ValidationStep(
            "Interactions tactiles écrans modernes",
            touch_command("tools/smoke_modern_touch_interactions.py"),
            env=pygame_headless_env(screen_size, **touch_env),
        ),
        ValidationStep(
            "Interactions tactiles anciens écrans",
            touch_command("tools/smoke_legacy_touch_interactions.py"),
            env=pygame_headless_env(screen_size, **touch_env),
        ),
        ValidationStep(
            "Interactions tactiles toutes rotations",
            [
                python_bin,
                "tools/smoke_touch_rotations.py",
                "--size",
                screen_size,
            ],
            env=pygame_headless_env(screen_size),
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
            env=pygame_headless_env(screen_size, **touch_env),
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
            env=pygame_headless_env(screen_size, **touch_env),
        ),
    ]


def run_step(step, project_root, timeout_seconds):
    print(f"\n==> {step.name}", flush=True)
    print(" ".join(step.command), flush=True)
    env = os.environ.copy()
    env.update(step.env)
    try:
        result = subprocess.run(
            step.command,
            cwd=project_root,
            env=env,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        print(
            f"Étape expirée après {timeout_seconds}s: {step.name}",
            flush=True,
        )
        return 124
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
    parser.add_argument(
        "--step-timeout",
        default=120,
        type=positive_int,
        help="Durée maximale en secondes pour chaque étape de validation.",
    )
    parser.add_argument(
        "--touch-rotation",
        default=0,
        type=touch_rotation,
        help="Rotation tactile Cortex à valider: 0, 90, 180 ou 270.",
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
        touch_rotation=args.touch_rotation,
        touch_flip_x=args.touch_flip_x,
        touch_flip_y=args.touch_flip_y,
    )
    for step in steps:
        returncode = run_step(step, project_root, args.step_timeout)
        if returncode != 0:
            return returncode

    print("\nValidation Raspberry Pi/Pygame OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
