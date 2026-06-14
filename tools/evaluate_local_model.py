import argparse
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from model_loader import build_local_prompt, load_local_cortex_model


DEFAULT_QUESTIONS = [
    "Bonjour, qui es-tu ?",
    "Quelle heure est-il ?",
    "Peux-tu jouer de la musique ?",
    "Ajoute acheter du lait à ma liste de tâches.",
    "Quelle est la météo aujourd'hui ?",
    "Raconte-moi une blague courte.",
    "Explique ce que tu peux faire en une phrase.",
]


def extract_answer(decoded):
    if "Réponse :" in decoded:
        return decoded.split("Réponse :", 1)[-1].strip()
    return decoded.strip()


def main():
    parser = argparse.ArgumentParser(description="Évalue rapidement le modèle local Cortex.")
    parser.add_argument("--model", default="tinyllama_cortex_finetuned")
    parser.add_argument("--adapter", default="tinyllama_cortex_finetuned_v3_lora")
    parser.add_argument("--no-adapter", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=80)
    args = parser.parse_args()

    adapter = None if args.no_adapter else args.adapter
    tokenizer, model, active_model, device = load_local_cortex_model(
        base_model=args.model,
        adapter=adapter,
    )
    print(f"Modèle actif: {active_model}")
    print(f"Device: {device}")

    questions = DEFAULT_QUESTIONS[: args.limit] if args.limit else DEFAULT_QUESTIONS
    for question in questions:
        prompt = build_local_prompt(question)
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        inputs = {key: value.to(device) for key, value in inputs.items()}
        start = time.time()
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                repetition_penalty=1.08,
                pad_token_id=tokenizer.eos_token_id,
            )
        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        print("\n---")
        print(f"Question : {question}")
        print(f"Temps : {time.time() - start:.2f}s")
        print(f"Réponse : {extract_answer(decoded)}")


if __name__ == "__main__":
    main()
