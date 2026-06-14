import argparse
import json
import os
from pathlib import Path

import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "training" / "finetune_cortex_v3"
DEFAULT_MODEL = ROOT / "tinyllama_cortex_finetuned"
DEFAULT_OUTPUT = ROOT / "tinyllama_cortex_finetuned_v3_lora"


class JsonlTextDataset(Dataset):
    def __init__(self, path, tokenizer, max_length):
        self.rows = []
        with path.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                text = json.loads(line)["text"]
                self.rows.append(
                    tokenizer(
                        text,
                        truncation=True,
                        max_length=max_length,
                        add_special_tokens=True,
                    )
                )

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        return self.rows[index]


def require_peft():
    try:
        from peft import LoraConfig, TaskType, get_peft_model
    except ImportError as error:
        raise SystemExit(
            "Dépendance manquante: peft.\n"
            "Installe d'abord les dépendances fine-tuning avec:\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install peft\n"
            "bitsandbytes n'est pas nécessaire pour ce script."
        ) from error

    return LoraConfig, TaskType, get_peft_model


def build_training_arguments(args, use_cuda):
    kwargs = {
        "output_dir": str(args.output_dir),
        "overwrite_output_dir": True,
        "num_train_epochs": args.epochs,
        "max_steps": args.max_steps,
        "learning_rate": args.learning_rate,
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": 1,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "warmup_ratio": 0.03,
        "weight_decay": 0.0,
        "logging_steps": 10,
        "save_steps": args.save_steps,
        "eval_steps": args.eval_steps,
        "save_total_limit": 2,
        "report_to": [],
        "fp16": use_cuda,
        "dataloader_num_workers": 0,
        "remove_unused_columns": False,
    }

    try:
        return TrainingArguments(eval_strategy="steps", save_strategy="steps", **kwargs)
    except TypeError:
        return TrainingArguments(evaluation_strategy="steps", save_strategy="steps", **kwargs)


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune Cortex avec LoRA sur le dataset v3 nettoyé."
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--eval-steps", type=int, default=50)
    parser.add_argument("--save-steps", type=int, default=50)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument(
        "--allow-cpu",
        action="store_true",
        help="Autorise un entraînement CPU très lent, utile seulement pour un smoke test.",
    )
    args = parser.parse_args()

    os.environ["WANDB_DISABLED"] = "true"
    use_cuda = torch.cuda.is_available()
    if not use_cuda and not args.allow_cpu:
        raise SystemExit(
            "CUDA n'est pas disponible dans cette venv. Pour un vrai fine-tuning "
            "TinyLlama, utilise un environnement GPU.\n"
            "Pour vérifier que la chaîne fonctionne malgré tout, lance un smoke test CPU:\n"
            "  .\\.venv\\Scripts\\python.exe tools\\train_cortex_lora.py --max-steps 1 --allow-cpu"
        )

    LoraConfig, TaskType, get_peft_model = require_peft()

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        local_files_only=True,
        low_cpu_mem_usage=True,
        torch_dtype=torch.float16 if use_cuda else torch.float32,
    )
    model.config.use_cache = False

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    train_dataset = JsonlTextDataset(args.dataset_dir / "train.jsonl", tokenizer, args.max_length)
    eval_dataset = JsonlTextDataset(args.dataset_dir / "eval.jsonl", tokenizer, args.max_length)
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    training_args = build_training_arguments(args, use_cuda)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=collator,
    )

    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Adaptateur LoRA sauvegardé dans {args.output_dir}")


if __name__ == "__main__":
    main()
