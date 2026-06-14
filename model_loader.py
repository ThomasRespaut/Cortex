from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parent
DEFAULT_BASE_MODEL = ROOT / "tinyllama_cortex_finetuned"
DEFAULT_LORA_ADAPTER = ROOT / "tinyllama_cortex_finetuned_v3_lora"
FALLBACK_LORA_ADAPTER = ROOT / "tinyllama_cortex_finetuned_v2_lora"
LOCAL_SYSTEM_PROMPT = (
    "Tu es Cortex, un assistant vocal local pour Thomas. "
    "Réponds en français, brièvement, avec un ton naturel. "
    "Quand une action doit être exécutée par l'application, réponds uniquement "
    "avec un appel d'outil Cortex au format attendu par l'application. "
    "N'invente jamais d'outil."
)


def resolve_path(path):
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return ROOT / candidate


def load_local_cortex_model(
    base_model=DEFAULT_BASE_MODEL,
    adapter=DEFAULT_LORA_ADAPTER,
    device=None,
):
    """Load TinyLlama Cortex with the v3 LoRA adapter, falling back to v2."""
    base_model = resolve_path(base_model)
    adapter = resolve_path(adapter) if adapter else None
    if (
        adapter == DEFAULT_LORA_ADAPTER
        and not (adapter / "adapter_config.json").exists()
        and (FALLBACK_LORA_ADAPTER / "adapter_config.json").exists()
    ):
        adapter = FALLBACK_LORA_ADAPTER
    adapter_available = adapter and (adapter / "adapter_config.json").exists()
    tokenizer_path = adapter if adapter_available else base_model

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        local_files_only=True,
        low_cpu_mem_usage=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )

    active_model_path = base_model
    if adapter_available:
        try:
            from peft import PeftModel
        except ImportError as error:
            raise RuntimeError(
                "L'adaptateur LoRA existe, mais la dépendance peft est absente."
            ) from error

        model = PeftModel.from_pretrained(model, adapter, local_files_only=True)
        active_model_path = adapter

    target_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model.to(target_device)
    model.eval()

    return tokenizer, model, str(active_model_path), target_device


def build_local_prompt(question, context=None):
    parts = [f"Instruction: {LOCAL_SYSTEM_PROMPT}"]
    if context:
        parts.append(f"Contexte: {context.strip()}")
    parts.append(f"Question: {question.strip()}")
    parts.append("Réponse :")
    return "\n".join(parts)
