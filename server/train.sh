#!/bin/bash
# 模型微调脚本
# 使用LoRA方法微调Qwen3-8B模型

# 设置使用的GPU（可根据实际情况调整）
# 单GPU训练
CUDA_VISIBLE_DEVICES=0 \
swift sft \
    --model '/mnt/disk2/aolin.guo/graduate_agent/server/model-dir' \
    --train_type lora \
    --dataset '/mnt/disk2/aolin.guo/graduate_agent/server/data/cleaned_training_data.jsonl' \
    --load_from_cache_file true \
    --torch_dtype bfloat16 \
    --num_train_epochs 3 \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 1 \
    --learning_rate 1e-4 \
    --lora_rank 8 \
    --lora_alpha 32 \
    --target_modules all-linear \
    --gradient_accumulation_steps 16 \
    --eval_steps 100 \
    --save_steps 100 \
    --save_total_limit 2 \
    --logging_steps 5 \
    --max_length 2048 \
    --output_dir output \
    --system 'You are a helpful assistant.' \
    --warmup_ratio 0.05 \
    --dataloader_num_workers 4 \
    --model_author graduate-agent \
    --model_name graduate-agent-qwen3

