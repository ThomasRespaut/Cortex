import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.verify_screen_smoke import validate_screen_image


REQUIRED_FILES = [
    "Screen.py",
    "requirements-raspberry-pi.txt",
    "scripts/launch_raspberry_pi.sh",
    "scripts/setup_raspberry_pi.sh",
    "deploy/raspberry-pi/install_service.sh",
    "deploy/raspberry-pi/cortex.service.example",
]

REQUIRED_ASSETS = [
    "app/Images/backgrounds/calendrier.png",
    "app/Images/backgrounds/horloge.png",
    "app/Images/backgrounds/jeu.png",
    "app/Images/backgrounds/message.png",
    "app/Images/backgrounds/musique.png",
    "app/Images/backgrounds/sante.png",
    "app/Images/backgrounds/transport.png",
    "app/Images/app_icons/icone_reglage.png",
]


def has_lf_line_endings(path):
    content = Path(path).read_bytes()
    return b"\r\n" not in content


def git_mode(project_root, relative_path):
    result = subprocess.run(
        ["git", "ls-files", "--stage", relative_path],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.split(maxsplit=1)[0]


def collect_preflight_errors(
    project_root,
    screenshot=None,
    check_pygame=True,
    require_executable=True,
):
    root = Path(project_root).resolve()
    errors = []

    for relative_path in REQUIRED_FILES:
        path = root / relative_path
        if not path.is_file():
            errors.append(f"Fichier manquant: {relative_path}")

    for relative_path in (
        "scripts/launch_raspberry_pi.sh",
        "scripts/setup_raspberry_pi.sh",
        "deploy/raspberry-pi/install_service.sh",
    ):
        path = root / relative_path
        if path.is_file() and not has_lf_line_endings(path):
            errors.append(f"Script avec fins de ligne CRLF: {relative_path}")
        if require_executable:
            mode = git_mode(root, relative_path)
            if mode is not None and mode != "100755":
                errors.append(f"Script non exécutable dans Git: {relative_path} ({mode})")

    for relative_path in REQUIRED_ASSETS:
        path = root / relative_path
        if not path.is_file():
            errors.append(f"Asset manquant: {relative_path}")
        elif path.stat().st_size == 0:
            errors.append(f"Asset vide: {relative_path}")

    icon_dir = root / "app" / "Images" / "app_icons_v2"
    icons = list(icon_dir.glob("*.png")) if icon_dir.is_dir() else []
    if len(icons) < 22:
        errors.append(f"Icônes app_icons_v2 incomplètes: {len(icons)}/22")

    if check_pygame:
        try:
            import pygame  # noqa: F401
        except ImportError as error:
            errors.append(f"Pygame indisponible: {error}")

    if screenshot:
        screenshot_path = Path(screenshot)
        if not screenshot_path.is_absolute():
            screenshot_path = root / screenshot_path
        try:
            validate_screen_image(screenshot_path, min_width=400, min_height=400)
        except ValueError as error:
            errors.append(str(error))

    return errors


def parse_args():
    parser = argparse.ArgumentParser(
        description="Vérifie qu'un clone Cortex est prêt pour Raspberry Pi/Pygame."
    )
    parser.add_argument("--project-root", default=".", help="Racine du projet Cortex.")
    parser.add_argument("--screenshot", help="Capture smoke test à valider.")
    parser.add_argument(
        "--skip-pygame-import",
        action="store_true",
        help="Ne vérifie pas l'import pygame.",
    )
    parser.add_argument(
        "--skip-executable-check",
        action="store_true",
        help="Ne vérifie pas le mode exécutable Git des scripts .sh.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    errors = collect_preflight_errors(
        args.project_root,
        screenshot=args.screenshot,
        check_pygame=not args.skip_pygame_import,
        require_executable=not args.skip_executable_check,
    )
    if errors:
        print("Préflight Raspberry Pi échoué:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Préflight Raspberry Pi OK.")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    raise SystemExit(main())
