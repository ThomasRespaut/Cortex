import argparse
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "cortex_runpod_training_bundle.zip"

INCLUDE_PATHS = [
    "assistant/functions.py",
    "assistant/tools.json",
    "function_calling.py",
    "model_loader.py",
    "tools/build_finetune_dataset.py",
    "tools/validate_finetune_dataset.py",
    "tools/train_cortex_lora.py",
    "tools/evaluate_local_model.py",
    "training/finetune_cortex_v3",
    "tinyllama_cortex_finetuned",
    "runpod/train_remote.sh",
]

STORE_SUFFIXES = {".bin", ".pt", ".pth", ".safetensors", ".model", ".zip"}


def iter_files(path):
    if path.is_file():
        yield path
        return

    for child in path.rglob("*"):
        if not child.is_file():
            continue
        if "__pycache__" in child.parts:
            continue
        yield child


def main():
    parser = argparse.ArgumentParser(
        description="Prépare une archive minimale pour entraîner Cortex sur RunPod."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    missing = [item for item in INCLUDE_PATHS if not (ROOT / item).exists()]
    if missing:
        raise SystemExit("Fichiers/dossiers manquants:\n" + "\n".join(missing))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        args.output.unlink()
    with zipfile.ZipFile(args.output, "w") as archive:
        for relative in INCLUDE_PATHS:
            source = ROOT / relative
            for file_path in iter_files(source):
                compression = (
                    zipfile.ZIP_STORED
                    if file_path.suffix.lower() in STORE_SUFFIXES
                    else zipfile.ZIP_DEFLATED
                )
                archive.write(
                    file_path,
                    file_path.relative_to(ROOT).as_posix(),
                    compress_type=compression,
                )

    size_mb = args.output.stat().st_size / (1024 * 1024)
    print(f"Archive prête: {args.output} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
