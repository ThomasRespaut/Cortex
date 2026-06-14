#!/usr/bin/env bash
set -euo pipefail

cd /workspace/cortex

python -m pip install --upgrade pip
python -m pip install \
  "torch" \
  "transformers==4.47.1" \
  "accelerate==1.2.1" \
  "peft==0.19.1" \
  "safetensors==0.4.5" \
  "tqdm==4.66.5"

python tools/validate_finetune_dataset.py --dataset-dir training/finetune_cortex_v3

python tools/train_cortex_lora.py \
  --model tinyllama_cortex_finetuned \
  --dataset-dir training/finetune_cortex_v3 \
  --output-dir tinyllama_cortex_finetuned_v3_lora \
  --epochs 2 \
  --batch-size 1 \
  --gradient-accumulation-steps 8 \
  --max-length 512 \
  --learning-rate 2e-4 \
  --eval-steps 50 \
  --save-steps 50

tar -czf /workspace/cortex_tinyllama_lora_v3.tar.gz tinyllama_cortex_finetuned_v3_lora
echo "Training terminé: /workspace/cortex_tinyllama_lora_v3.tar.gz"
