#!/bin/bash
# 模型推理脚本
# 使用微调后的模型进行推理

# 请将 vx-xxx/checkpoint-xxx 替换为实际训练输出的checkpoint路径
# 例如：output/v0-20231015-123456/checkpoint-100

CUDA_VISIBLE_DEVICES=0 \
swift infer \
    --adapters output/v0-20241014/checkpoint-100 \
    --stream true \
    --temperature 0.7 \
    --max_new_tokens 2048

# 使用说明：
# 1. 查看 output 目录下的训练结果
# 2. 找到最新的checkpoint目录，例如 output/v0-20241014/checkpoint-100
# 3. 将上面的 --adapters 参数替换为实际路径
# 4. 运行此脚本即可进行交互式推理

