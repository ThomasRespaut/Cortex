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
    ".env.example",
    "Screen.py",
    "requirements-raspberry-pi.txt",
    "scripts/launch_raspberry_pi.sh",
    "scripts/setup_raspberry_pi.sh",
    "deploy/raspberry-pi/install_service.sh",
    "deploy/raspberry-pi/cortex.service.example",
    "tools/validate_raspberry_pi_ui.py",
    "tools/smoke_home_touch_interactions.py",
    "tools/smoke_modern_touch_interactions.py",
    "tools/smoke_legacy_pygame_screens.py",
    "tools/smoke_modern_pygame_screens.py",
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

REQUIRED_ENV_EXAMPLE_KEYS = [
    "CORTEX_FULLSCREEN",
    "CORTEX_HIDE_CURSOR",
    "CORTEX_FPS",
    "CORTEX_SCREEN_SIZE",
    "CORTEX_TOUCH_ROTATION",
    "CORTEX_TOUCH_ROUND_CLIP",
    "CORTEX_TOUCH_EDGE_MARGIN",
    "CORTEX_TOUCH_EDGE_CLAMP",
    "CORTEX_ROUND_MASK",
    "CORTEX_TOUCH_HIT_SLOP",
    "CORTEX_TAP_MOVE_LIMIT",
    "CORTEX_EMPTY_DOUBLE_TAP_MS",
    "CORTEX_EMPTY_DOUBLE_TAP_DISTANCE",
]

REQUIRED_RASPBERRY_PI_REQUIREMENTS = [
    "pygame",
    "python-dotenv",
    "requests",
    "PyAudio",
    "sounddevice",
    "soundfile",
    "pvporcupine",
    "vosk",
]

REQUIRED_SERVICE_ENV_SNIPPETS = [
    "Environment=SDL_VIDEODRIVER=kmsdrm",
    "Environment=SDL_TOUCH_MOUSE_EVENTS=0",
    "Environment=SDL_MOUSE_TOUCH_EVENTS=0",
    "Environment=CORTEX_FULLSCREEN=true",
    "Environment=CORTEX_HIDE_CURSOR=true",
    "Environment=CORTEX_FPS=60",
    "Environment=CORTEX_SCREEN_SIZE=480x480",
    "Environment=CORTEX_TOUCH_ROTATION=0",
    "Environment=CORTEX_TOUCH_ROUND_CLIP=true",
    "Environment=CORTEX_TOUCH_EDGE_MARGIN=0",
    "Environment=CORTEX_TOUCH_EDGE_CLAMP=true",
    "Environment=CORTEX_ROUND_MASK=true",
    "Environment=CORTEX_TOUCH_HIT_SLOP=10",
    "Environment=CORTEX_TAP_MOVE_LIMIT=14",
    "Environment=CORTEX_EMPTY_DOUBLE_TAP_MS=500",
    "Environment=CORTEX_EMPTY_DOUBLE_TAP_DISTANCE=36",
]

REQUIRED_TEXT_SNIPPETS = {
    "scripts/launch_raspberry_pi.sh": [
        "SDL_VIDEODRIVER=\"${SDL_VIDEODRIVER:-kmsdrm}\"",
        "SDL_TOUCH_MOUSE_EVENTS=\"${SDL_TOUCH_MOUSE_EVENTS:-0}\"",
        "SDL_MOUSE_TOUCH_EVENTS=\"${SDL_MOUSE_TOUCH_EVENTS:-0}\"",
        "CORTEX_FULLSCREEN=\"${CORTEX_FULLSCREEN:-true}\"",
        "CORTEX_HIDE_CURSOR=\"${CORTEX_HIDE_CURSOR:-true}\"",
        "CORTEX_FPS=\"${CORTEX_FPS:-60}\"",
        "CORTEX_SCREEN_SIZE=\"${CORTEX_SCREEN_SIZE:-480x480}\"",
        "CORTEX_TOUCH_ROTATION=\"${CORTEX_TOUCH_ROTATION:-0}\"",
        "CORTEX_TOUCH_ROUND_CLIP=\"${CORTEX_TOUCH_ROUND_CLIP:-true}\"",
        "CORTEX_TOUCH_EDGE_MARGIN=\"${CORTEX_TOUCH_EDGE_MARGIN:-0}\"",
        "CORTEX_TOUCH_EDGE_CLAMP=\"${CORTEX_TOUCH_EDGE_CLAMP:-true}\"",
        "CORTEX_ROUND_MASK=\"${CORTEX_ROUND_MASK:-true}\"",
        "CORTEX_TOUCH_HIT_SLOP=\"${CORTEX_TOUCH_HIT_SLOP:-10}\"",
        "CORTEX_TAP_MOVE_LIMIT=\"${CORTEX_TAP_MOVE_LIMIT:-14}\"",
        "CORTEX_EMPTY_DOUBLE_TAP_MS=\"${CORTEX_EMPTY_DOUBLE_TAP_MS:-500}\"",
        (
            "CORTEX_EMPTY_DOUBLE_TAP_DISTANCE="
            "\"${CORTEX_EMPTY_DOUBLE_TAP_DISTANCE:-36}\""
        ),
    ],
    "scripts/setup_raspberry_pi.sh": [
        "bash -n scripts/launch_raspberry_pi.sh",
        "bash -n deploy/raspberry-pi/install_service.sh",
        "\"$VENV_DIR/bin/python\" -m pip check",
        "chmod +x scripts/launch_raspberry_pi.sh deploy/raspberry-pi/install_service.sh",
        "tools/validate_raspberry_pi_ui.py",
    ],
    "deploy/raspberry-pi/cortex.service.example": REQUIRED_SERVICE_ENV_SNIPPETS,
    "deploy/raspberry-pi/install_service.sh": REQUIRED_SERVICE_ENV_SNIPPETS,
}


def normalize_requirement_name(name):
    return name.strip().lower().replace("_", "-")


def requirement_names(requirements_text):
    names = set()
    for line in requirements_text.splitlines():
        cleaned = line.split("#", 1)[0].strip()
        if not cleaned or cleaned.startswith("-"):
            continue
        separator_indexes = [
            index
            for index in (
                cleaned.find(separator)
                for separator in ("<", ">", "=", "!", "~", "[", ";", " ")
            )
            if index >= 0
        ]
        name_end = min(separator_indexes) if separator_indexes else len(cleaned)
        names.add(normalize_requirement_name(cleaned[:name_end]))
    return names


def missing_raspberry_pi_requirements(requirements_text):
    names = requirement_names(requirements_text)
    return [
        requirement
        for requirement in REQUIRED_RASPBERRY_PI_REQUIREMENTS
        if normalize_requirement_name(requirement) not in names
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

    env_example = root / ".env.example"
    if env_example.is_file():
        env_content = env_example.read_text(encoding="utf-8")
        for key in REQUIRED_ENV_EXAMPLE_KEYS:
            if f"{key}=" not in env_content:
                errors.append(f"Variable absente de .env.example: {key}")

    requirements = root / "requirements-raspberry-pi.txt"
    if requirements.is_file():
        missing_requirements = missing_raspberry_pi_requirements(
            requirements.read_text(encoding="utf-8")
        )
        for requirement in missing_requirements:
            errors.append(
                "Dépendance Raspberry Pi absente de requirements-raspberry-pi.txt: "
                f"{requirement}"
            )

    for relative_path, snippets in REQUIRED_TEXT_SNIPPETS.items():
        path = root / relative_path
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in content:
                errors.append(f"Configuration absente de {relative_path}: {snippet}")

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
            validate_screen_image(
                screenshot_path,
                min_width=400,
                min_height=400,
                require_round_mask=True,
            )
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
