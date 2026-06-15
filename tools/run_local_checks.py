import argparse
import os
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


def build_check_steps(
    python_bin,
    dataset_dir,
    screen_size,
    project_root=".",
):
    return [
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
    return parser.parse_args()


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        print(f"Projet introuvable: {project_root}")
        return 1

    steps = build_check_steps(
        sys.executable,
        args.dataset_dir,
        args.screen_size,
        project_root=".",
    )
    for step in steps:
        returncode = run_step(step, project_root)
        if returncode != 0:
            return returncode

    print("\nValidation locale complète OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
