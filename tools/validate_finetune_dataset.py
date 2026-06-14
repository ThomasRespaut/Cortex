import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "training" / "finetune_cortex_v3"
TOOL_CALL_RE = re.compile(r"\[\s*([a-zA-Z_][\w]*)")


def load_allowed_tools():
    sys.path.insert(0, str(ROOT))
    import function_calling

    return set(function_calling.get_tools().keys())


def iter_jsonl(path):
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if line.strip():
                yield line_number, json.loads(line)


def response_part(text):
    if "Réponse :" not in text:
        return text
    return text.rsplit("Réponse :", 1)[-1]


def main():
    parser = argparse.ArgumentParser(
        description="Valide que le dataset Cortex v3 n'appelle aucun outil inexistant."
    )
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()

    allowed_tools = load_allowed_tools()
    counts = Counter()
    total = 0
    errors = []

    for split in ("train", "eval"):
        path = args.dataset_dir / f"{split}.jsonl"
        if not path.exists():
            errors.append(f"Fichier manquant: {path}")
            continue
        for line_number, row in iter_jsonl(path):
            total += 1
            text = row.get("text", "")
            if "Question:" not in text or "Réponse :" not in text:
                errors.append(f"{path}:{line_number}: format prompt/réponse incomplet")
            for name in TOOL_CALL_RE.findall(response_part(text)):
                counts[name] += 1
                if name not in allowed_tools:
                    errors.append(f"{path}:{line_number}: outil inconnu {name!r}")

    print(f"Exemples validés: {total}")
    print("Appels d'outils:")
    for name, count in counts.most_common():
        print(f"  {name}: {count}")

    if errors:
        print("\nErreurs:")
        for error in errors[:50]:
            print(f"  - {error}")
        if len(errors) > 50:
            print(f"  ... {len(errors) - 50} erreurs supplémentaires")
        raise SystemExit(1)

    print("Validation OK: aucun outil fantôme détecté.")


if __name__ == "__main__":
    main()
