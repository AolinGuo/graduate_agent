#!/bin/bash
# 多GPU模型微调脚本（使用DeepSpeed Zero3优化）
# 使用LoRA方法微调Qwen3-8B模型

# 设置使用4块GPU进行训练
NPROC_PER_NODE=4 \
CUDA_VISIBLE_DEVICES=0,1,2,3 \
swift sft \
    --model '/mnt/disk2/aolin.guo/graduate_agent/server/model-dir' \
    --train_type lora \
    --dataset '/mnt/disk2/aolin.guo/graduate_agent/server/data/cleaned_training_data.jsonl' \
    --load_from_cache_file true \
    --split_dataset_ratio 0.01 \
    --torch_dtype bfloat16 \
    --num_train_epochs 3 \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 2 \
    --learning_rate 1e-5 \
    --lora_rank 8 \
    --lora_alpha 32 \
    --target_modules all-linear \
    --gradient_accumulation_steps 4 \
    --packing true \
    --eval_steps 100 \
    --save_steps 100 \
    --logging_steps 5 \
    --max_length 2048 \
    --warmup_ratio 0.05 \
    --dataloader_num_workers 4 \
    --dataset_num_proc 8 \
    --save_total_limit 2 \
    --save_only_model true \
    --output_dir output \
    --deepspeed zero3 \
    --use_liger_kernel true \
    --attn_impl flash_attn \
    --system 'You are a helpful assistant.' \
    --model_author graduate-agent \
    --model_name graduate-agent-qwen3

