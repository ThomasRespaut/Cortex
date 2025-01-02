import json
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    TrainerCallback
)
from datasets import Dataset
from sklearn.model_selection import train_test_split
from torch.nn import CrossEntropyLoss
import torch
import json
import os
import numpy as np


# ----------------------------------------------------------------------
# 1. Désactiver W&B si vous ne souhaitez pas de logs Weights & Biases
# ----------------------------------------------------------------------
os.environ["WANDB_DISABLED"] = "true"

# ----------------------------------------------------------------------
# 2. Lecture du fichier JSON 'rag_personality_training.json'
# ----------------------------------------------------------------------
def load_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Taille du dataset : {len(data)}")
        return data
    except FileNotFoundError:
        print(f"Erreur : fichier {file_path} introuvable.")
        return []

data = load_data('rag/rag_training.json')

# ----------------------------------------------------------------------
# 3. Préparation des données
# ----------------------------------------------------------------------
def prepare_examples(data):
    examples = []
    for item in data:
        if 'question' in item and 'response' in item:
            examples.append({
                "text": #f"[Prompt] : {item.get('prompt', 'Aucun prompt spécifié')}\n"
                        f"[Contexte] : {item.get('database', 'Aucun contexte fourni')}\n"
                        f"[Question] : {item.get('question', 'Aucune question spécifiée')}\n"
                        f"[Réponse] : {item.get('response', 'Aucune réponse spécifiée')}\n"
                        f"\n-----------------------------\n"
            })
        else:
            print("Donnée invalide détectée, ignorée.")

    print(examples)
    return examples

examples = prepare_examples(data)

# Division en données d'entraînement et d'évaluation
train_data, eval_data = train_test_split(examples, test_size=0.33, random_state=42)
train_dataset = Dataset.from_list(train_data)
eval_dataset = Dataset.from_list(eval_data)

# ----------------------------------------------------------------------
# 4. Chargement du modèle et du tokenizer
# ----------------------------------------------------------------------
finetuned_model_path = "../../tinyllama_cortex_finetuned/"
tokenizer = AutoTokenizer.from_pretrained(finetuned_model_path)
model = AutoModelForCausalLM.from_pretrained(finetuned_model_path)
print("Modèle fine-tuné chargé avec succès.")

# Prétraitement : tokenisation et création des labels
def preprocess_function(examples):
    inputs = tokenizer(
        examples["text"],
        padding="max_length",
        truncation=True,
        max_length=64
    )
    inputs["labels"] = inputs["input_ids"].copy()
    return inputs

tokenized_train_dataset = train_dataset.map(preprocess_function, batched=True)
tokenized_eval_dataset = eval_dataset.map(preprocess_function, batched=True)

# ----------------------------------------------------------------------
# 5. Trainer personnalisé et visualisation à chaque époque
# ----------------------------------------------------------------------
class CustomTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()

        loss_fct = CrossEntropyLoss()
        loss = loss_fct(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1)
        )
        return (loss, outputs) if return_outputs else loss

    def evaluate(self, eval_dataset=None, ignore_keys=None, metric_key_prefix="eval"):
        eval_results = super().evaluate(eval_dataset, ignore_keys, metric_key_prefix)
        print("\n--- Visualisation des réponses à chaque époque ---")
        for example in eval_data[:5]:
            print(f"\nQuestion: {example['text']}")
            response = generate_response(example['text'], model, tokenizer)
            print(f"Réponse générée: {response}")
        return eval_results

# ----------------------------------------------------------------------
# 6. Arguments d'entraînement
# ----------------------------------------------------------------------
training_args = TrainingArguments(
    output_dir="./tinyllama_cortex_finetune",
    evaluation_strategy="epoch",
    learning_rate=5e-5,
    per_device_train_batch_size=50,
    gradient_accumulation_steps=4,
    num_train_epochs=10,
    save_total_limit=2,
    logging_steps=10,
    eval_steps=10,
    save_strategy="epoch",
    logging_dir="../../logs",
    report_to=["tensorboard"],
    fp16=torch.cuda.is_available(),
)

# ----------------------------------------------------------------------
# 7. Fine-tuning du modèle
# ----------------------------------------------------------------------
def generate_response(prompt, model, tokenizer):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=128)
    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            inputs["input_ids"],
            max_length=150,
            do_sample=True,
            top_k=30,
            top_p=0.85,
            temperature=1.0,
            num_return_sequences=1,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

trainer = CustomTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train_dataset,
    eval_dataset=tokenized_eval_dataset
)

trainer.train()

# Sauvegarde du modèle fine-tuné
trainer.save_model("./tinyllama_cortex_finetuned_v2")
tokenizer.save_pretrained("./tinyllama_cortex_finetuned_v2")
