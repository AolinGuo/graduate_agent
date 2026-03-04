#!/bin/bash
# Linux 部署环境变量配置示例
# 在 server/ 目录下创建 .env 文件，或直接 export 这些变量后再启动 run.py

# ===== GPU 配置 =====
# 指定使用哪块物理GPU（单卡填单个编号，多卡填逗号分隔）
export GPU_ID=2
# export GPU_ID=2,5   # 多卡示例

# vLLM多卡并行数（与GPU数量保持一致）
export TENSOR_PARALLEL_SIZE=1

# GPU显存利用率（0.0~1.0）
export GPU_MEM_UTIL=0.9

# 模型数据格式
export MODEL_DTYPE=bfloat16

# 最大上下文长度（token数）
export MAX_MODEL_LEN=4096

# ===== 模型路径（Linux绝对路径）=====
# 基座大语言模型路径
export MODEL_PATH=/data/models/Qwen3-8B

# LoRA 微调权重路径（若无则不填或注释掉）
export LORA_PATH=/data/models/lora-adapter

# Embedding 模型路径（用于RAG）
export EMBEDDING_MODEL_PATH=/data/models/embedding-model

# RAG 向量库路径（相对于 server/ 或绝对路径）
export RAG_VECTOR_PATH=/data/rag_vector

# RAG 使用的GPU设备（填写逻辑GPU编号）
# 因为 CUDA_VISIBLE_DEVICES 决定了哪些物理卡可见，这里用逻辑编号
# 例如 GPU_ID=2 且 TENSOR_PARALLEL_SIZE=1，则 vLLM 占满 cuda:0，
# RAG embedding 可以用另一块空闲GPU
export RAG_GPU_DEVICE=cuda:0

# ===== Flask 服务配置 =====
export HOST=0.0.0.0
export PORT=8888
export DEBUG=False

# ===== 启动命令 =====
# source env_linux.sh && python run.py
