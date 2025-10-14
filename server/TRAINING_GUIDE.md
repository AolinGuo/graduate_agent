# 模型训练与推理指南

本指南说明如何使用提供的脚本进行模型微调和推理。

## 📋 目录结构

```
server/
├── model-dir/                    # Qwen3-8B 基础模型目录
├── data/
│   └── cleaned_training_data.jsonl  # 训练数据集
├── train.sh                      # 单GPU训练脚本
├── train_multi_gpu.sh           # 多GPU训练脚本（推荐）
├── infer.sh                      # Shell推理脚本
├── infer.py                      # Python推理脚本
└── output/                       # 训练输出目录（自动创建）
```

## 🚀 快速开始

### 1. 环境准备

确保已安装必要的依赖：

```bash
# 进入server目录
cd server

# 激活虚拟环境
source .venv/bin/activate

# 安装训练所需的包
pip install ms-swift -U
pip install transformers
pip install deepspeed          # 多GPU训练需要
pip install liger-kernel       # 节约显存
pip install flash-attn --no-build-isolation  # packing功能需要

# 检查GPU状态
nvidia-smi
```

### 2. 模型微调

#### 方案A：单GPU训练（显存要求较高）

```bash
# 给脚本添加执行权限
chmod +x train.sh

# 开始训练
./train.sh
```

#### 方案B：多GPU训练（推荐，使用DeepSpeed Zero3优化）

```bash
# 给脚本添加执行权限
chmod +x train_multi_gpu.sh

# 开始训练（使用4块GPU）
./train_multi_gpu.sh
```

**注意：** 如果你的GPU数量不是4块，需要修改 `train_multi_gpu.sh` 中的：
- `NPROC_PER_NODE=4` → 改为你的GPU数量
- `CUDA_VISIBLE_DEVICES=0,1,2,3` → 改为你要使用的GPU编号

### 3. 训练过程监控

训练过程中会在终端输出日志，包括：
- Loss值变化
- 训练速度（samples/s）
- 评估指标
- Checkpoint保存信息

训练输出会保存在 `output/` 目录下，结构如下：
```
output/
└── v0-20241014-123456/          # 训练版本目录
    ├── checkpoint-100/          # 第100步的检查点
    ├── checkpoint-200/          # 第200步的检查点
    └── ...
```

### 4. 模型推理

训练完成后，有两种方式进行推理：

#### 方案A：使用Swift框架推理（推荐）

```bash
# 给脚本添加执行权限
chmod +x infer.sh

# 修改infer.sh中的checkpoint路径
# 将 output/v0-20241014/checkpoint-100 改为你实际的checkpoint路径

# 运行推理
./infer.sh
```

这会启动一个交互式对话界面，你可以直接与模型对话。

#### 方案B：使用Python脚本推理

```bash
# 修改 infer.py 中的配置
# 设置 ADAPTER_PATH 为你的checkpoint路径，例如：
# ADAPTER_PATH = "output/v0-20241014/checkpoint-100"

# 运行推理脚本
python infer.py
```

这会启动一个Python交互式对话程序。

## 🔧 参数说明

### 训练参数

| 参数 | 说明 | 单GPU值 | 多GPU值 |
|------|------|---------|---------|
| `--model` | 基础模型路径 | model-dir | model-dir |
| `--train_type` | 训练类型 | lora | lora |
| `--dataset` | 数据集路径 | cleaned_training_data.jsonl | cleaned_training_data.jsonl |
| `--num_train_epochs` | 训练轮数 | 3 | 3 |
| `--learning_rate` | 学习率 | 1e-4 | 1e-5 |
| `--lora_rank` | LoRA秩 | 8 | 8 |
| `--lora_alpha` | LoRA alpha | 32 | 32 |
| `--max_length` | 最大序列长度 | 2048 | 2048 |
| `--deepspeed` | DeepSpeed配置 | - | zero3 |
| `--packing` | 序列打包 | - | true |

### 推理参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--adapters` | LoRA权重路径 | output/v0-xxx/checkpoint-xxx |
| `--stream` | 流式输出 | true |
| `--temperature` | 采样温度 | 0.7 |
| `--max_new_tokens` | 最大生成token数 | 2048 |

## 📊 性能优化建议

1. **显存不足**：
   - 使用多GPU训练（train_multi_gpu.sh）
   - 减小 `per_device_train_batch_size`
   - 减小 `max_length`
   - 启用 `gradient_checkpointing`

2. **训练速度慢**：
   - 使用 `packing=true`（多GPU脚本已启用）
   - 增大 `dataloader_num_workers`
   - 使用 `flash_attn`（多GPU脚本已启用）

3. **模型效果不佳**：
   - 增加训练轮数 `num_train_epochs`
   - 调整学习率 `learning_rate`
   - 检查数据集质量
   - 增加 `lora_rank` 值

## ⚠️ 常见问题

### Q1: 训练时显存溢出（OOM）
**A:** 使用多GPU训练脚本，或减小batch size和max_length

### Q2: 找不到checkpoint
**A:** 检查 `output/` 目录，找到最新的 `v0-xxx/checkpoint-xxx` 路径

### Q3: 推理时模型回复质量不好
**A:** 
- 确保使用了训练好的checkpoint
- 调整temperature参数（0.7左右较好）
- 检查训练是否充分收敛

### Q4: CUDA版本不兼容
**A:** 确保PyTorch和CUDA版本匹配，可能需要重新安装对应版本

## 📝 下一步

1. 根据实际GPU情况选择训练脚本
2. 监控训练过程，确保loss正常下降
3. 选择合适的checkpoint进行推理测试
4. 根据效果调整训练参数进行迭代

祝训练顺利！🎉

