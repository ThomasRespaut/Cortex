import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CheckStep:
    name: str
    command: list[str]
    env: dict[str, str] = field(default_factory=dict)


SECRET_PATTERNS = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    (
        "Private key block",
        re.compile(r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY"),
    ),
    (
        "OAuth token value",
        re.compile(
            r"(?i)\b(?:access_token|refresh_token|client_secret)\b"
            r"\s*[:=]\s*[\"'][A-Za-z0-9._~+/=-]{24,}[\"']"
        ),
    ),
]


def git_output(project_root, *args):
    result = subprocess.run(
        ["git", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def changed_files(project_root):
    paths = set(
        git_output(
            project_root,
            "diff",
            "--name-only",
            "--diff-filter=ACMRTUXB",
            "HEAD",
        )
    )
    paths.update(git_output(project_root, "ls-files", "--others", "--exclude-standard"))
    return sorted(paths)


def secret_findings(project_root, paths):
    root = Path(project_root)
    findings = []
    for relative_path in paths:
        path = root / relative_path
        if not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append((relative_path, line_number, label))
    return findings


def run_secret_scan(project_root):
    findings = secret_findings(project_root, changed_files(project_root))
    if not findings:
        print("Scan secrets OK.")
        return 0

    print("Secrets potentiels détectés dans les fichiers modifiés:")
    for path, line_number, label in findings:
        print(f"- {path}:{line_number} ({label})")
    return 1


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("La valeur doit être un entier") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("La valeur doit être positive")
    return parsed


def touch_rotation(value):
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("La rotation doit être un entier") from error
    if parsed not in (0, 90, 180, 270):
        raise argparse.ArgumentTypeError("La rotation tactile doit être 0, 90, 180 ou 270")
    return parsed


def build_check_steps(
    python_bin,
    dataset_dir,
    screen_size,
    project_root=".",
    step_timeout=300,
    touch_rotation=0,
):
    return [
        CheckStep(
            "Contrôle whitespace Git",
            ["git", "diff", "--check"],
        ),
        CheckStep(
            "Scan secrets fichiers modifiés",
            [
                python_bin,
                "tools/run_local_checks.py",
                "--project-root",
                project_root,
                "--secrets-only",
            ],
        ),
        CheckStep(
            "Compilation Python",
            [
                python_bin,
                "-m",
                "compileall",
                "-q",
                "Screen.py",
                "app",
                "function_calling.py",
                "model_loader.py",
                "tools",
                "tests",
            ],
        ),
        CheckStep(
            "Tests unitaires",
            [python_bin, "-m", "unittest", "discover", "-s", "tests", "-v"],
        ),
        CheckStep(
            "Vérification dépendances",
            [python_bin, "-m", "pip", "check"],
        ),
        CheckStep(
            "Validation dataset fine-tuning",
            [
                python_bin,
                "tools/validate_finetune_dataset.py",
                "--dataset-dir",
                dataset_dir,
            ],
        ),
        CheckStep(
            "Validation Raspberry Pi/Pygame",
            [
                python_bin,
                "tools/validate_raspberry_pi_ui.py",
                "--project-root",
                project_root,
                "--size",
                screen_size,
                "--step-timeout",
                str(step_timeout),
                "--touch-rotation",
                str(touch_rotation),
            ],
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
        description="Exécute la validation locale complète de Cortex."
    )
    parser.add_argument("--project-root", default=".", help="Racine du projet Cortex.")
    parser.add_argument(
        "--dataset-dir",
        default="training/finetune_cortex_v3",
        help="Dossier dataset à valider.",
    )
    parser.add_argument(
        "--screen-size",
        default="480x480",
        help="Taille utilisée par les smokes Raspberry Pi/Pygame.",
    )
    parser.add_argument(
        "--secrets-only",
        action="store_true",
        help="Ne lance que le scan de secrets des fichiers modifiés.",
    )
    parser.add_argument(
        "--step-timeout",
        default=300,
        type=positive_int,
        help="Durée maximale en secondes pour chaque étape de validation.",
    )
    parser.add_argument(
        "--touch-rotation",
        default=0,
        type=touch_rotation,
        help="Rotation tactile Cortex à valider dans les smokes Raspberry Pi.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        print(f"Projet introuvable: {project_root}")
        return 1

    if args.secrets_only:
        return run_secret_scan(project_root)

    steps = build_check_steps(
        sys.executable,
        args.dataset_dir,
        args.screen_size,
        project_root=".",
        step_timeout=args.step_timeout,
        touch_rotation=args.touch_rotation,
    )
    for step in steps:
        returncode = run_step(step, project_root, args.step_timeout)
        if returncode != 0:
            return returncode

    print("\nValidation locale complète OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
