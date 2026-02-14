# 模型测试快速开始指南

## 🎯 测试目标

评估四个版本模型的性能：
- **base**: 基础模型
- **base+RAG**: 基础模型 + RAG检索
- **lora**: LoRA微调模型  
- **lora+RAG**: LoRA微调模型 + RAG检索

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
pip install -r requirements_test.txt
```

### 2️⃣ 配置API密钥（可选，用于步骤3）

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件，填写你的 DeepSeek API密钥
# DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx
```

### 3️⃣ 运行测试

```bash
# 步骤1: 生成所有版本的模型回复（耗时较长，需要GPU）
python generate_responses.py

# 步骤2: 自动评估（ROUGE + Embedding相似度）
python evaluate_responses.py

# 步骤3: 外部API评分（可选，使用DeepSeek API）
python evaluate_with_external_api.py
```

## 📁 输出文件

```
generated_responses/          # 步骤1输出
├── base_generated.json
├── base_rag_generated.json
├── lora_generated.json
└── lora_rag_generated.json

evaluation_results/           # 步骤2输出
├── base_evaluation.json
├── base_rag_evaluation.json
├── lora_evaluation.json
├── lora_rag_evaluation.json
└── summary_report.json       # 📊 自动评估汇总

external_evaluation/          # 步骤3输出
├── base_api_evaluation.json
├── base_rag_api_evaluation.json
├── lora_api_evaluation.json
├── lora_rag_api_evaluation.json
└── api_evaluation_summary.json  # 🏆 API评估汇总
```

## 📊 查看结果

### 自动评估结果
```bash
# 查看汇总
cat evaluation_results/summary_report.json

# 示例输出：
# {
#   "versions": {
#     "lora_rag": {
#       "rouge_1": 0.4834,
#       "rouge_2": 0.3012,
#       "rouge_l": 0.4234,
#       "embedding_similarity": 0.9145
#     },
#     ...
#   }
# }
```

### API评估结果
```bash
# 查看汇总
cat external_evaluation/api_evaluation_summary.json

# 示例输出：
# {
#   "versions": {
#     "lora_rag": {
#       "overall_score": 91.23,
#       "accuracy": 9.12,
#       "completeness": 9.23,
#       ...
#     },
#     ...
#   }
# }
```

## ⚠️ 注意事项

1. **GPU显存**: 步骤1需要足够GPU显存加载模型（建议16GB+）
2. **测试时间**: 完整测试可能需要数小时，取决于测试样本数量
3. **API费用**: 步骤3会产生API调用费用
4. **增量测试**: 可以单独运行某个步骤，无需每次都重新生成

## 🔧 故障排除

### 模型加载失败
```
错误: 模型路径不存在
解决: 确认模型文件在 server/model-dir/ 和 server/lora-dir/
```

### API调用失败
```
错误: 未找到 DEEPSEEK_API_KEY
解决: 检查 .env 文件配置，确保API密钥正确
```

### CUDA内存不足
```
错误: CUDA out of memory
解决: 减少测试样本数量，或在代码中调整batch size
```

## 📖 详细文档

查看 `README_TEST.md` 了解更多详细信息。
