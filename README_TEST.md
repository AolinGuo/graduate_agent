# 模型测试说明

本文档说明如何测试四个版本的模型：base、base+RAG、lora、lora+RAG。

## 测试环境准备

### 1. 安装依赖

```bash
pip install rouge-chinese
pip install sentence-transformers
pip install scikit-learn
pip install openai  # 如果需要使用外部模型评估
```


## 测试流程

### 步骤1: 基本测试（ROUGE + Embedding相似度）

运行基本测试脚本:

```bash
python test_model.py
```

这个脚本会:
1. 加载embedding模型用于计算向量相似度
2. 加载测试数据
3. 依次测试四个版本的模型:
   - `base`: 基础模型，不使用RAG
   - `base_rag`: 基础模型 + RAG检索材料
   - `lora`: LoRA微调模型，不使用RAG
   - `lora_rag`: LoRA微调模型 + RAG检索材料
4. 计算每个样本的评估指标:
   - ROUGE-1, ROUGE-2, ROUGE-L (文本相似度)
   - Embedding相似度 (语义相似度)
5. 生成详细结果和汇总报告

### 步骤2: 外部API评估（可选）

如果需要使用外部API（DeepSeek）进行质量评分:

**准备工作：配置API密钥**

```bash
# 方法1: 创建 .env 文件（推荐）
# 在项目根目录创建 .env 文件，添加:
DEEPSEEK_API_KEY=your_deepseek_api_key

# 方法2: 设置环境变量
# Windows:
set DEEPSEEK_API_KEY=your_api_key

# Linux/Mac:
export DEEPSEEK_API_KEY=your_api_key
```

**运行API评估：**

```bash
python evaluate_with_external_api.py
```

这个脚本会:
1. 读取步骤1生成的评估结果（包含生成的回复）
2. 使用 DeepSeek API 对每个生成的回复进行专业评分
3. 评估维度包括:
   - 准确性
   - 完整性
   - 专业性
   - 态度
   - 法律依据
4. 生成评估报告

**注意**: 如果使用国内的大模型API（如通义千问、文心一言等），请修改 `test_with_external_model.py` 中的API调用部分。

## 测试结果

所有测试结果将保存在 `test_results/` 目录下:

### 基本测试结果

- `base_results.json`: base模型的详细测试结果
- `base_rag_results.json`: base+RAG模型的详细测试结果
- `lora_results.json`: lora模型的详细测试结果
- `lora_rag_results.json`: lora+RAG模型的详细测试结果
- `summary_report.json`: 汇总报告（包含所有版本的平均分数）

### 外部模型评估结果

- `base_external_evaluation.json`: base模型的外部评估结果
- `base_rag_external_evaluation.json`: base+RAG模型的外部评估结果
- `lora_external_evaluation.json`: lora模型的外部评估结果
- `lora_rag_external_evaluation.json`: lora+RAG模型的外部评估结果
- `external_evaluation_summary.json`: 外部评估汇总报告

## 评估指标说明

### ROUGE分数

- **ROUGE-1**: 基于单个词（unigram）的重叠度
- **ROUGE-2**: 基于两个连续词（bigram）的重叠度
- **ROUGE-L**: 基于最长公共子序列的评估

分数范围: 0-1，越高越好

### Embedding相似度

使用sentence-transformers计算生成文本和参考文本的语义相似度。

分数范围: -1 到 1，越接近1越相似

### 外部模型评分

使用大语言模型从多个维度评估回复质量:

- **准确性** (0-10分): 回复是否准确解答了用户问题
- **完整性** (0-10分): 回复是否涵盖了所有必要信息
- **专业性** (0-10分): 回复是否使用了恰当的法律术语
- **态度** (0-10分): 回复是否礼貌、专业、有同理心
- **法律依据** (0-10分): 回复是否正确引用了相关法律条文
- **总分** (0-100分): 综合评分

## 自定义测试

如果需要自定义测试流程，可以修改:

1. **测试样本数量**: 在 `test_model.py` 中修改 `self.test_data` 的子集
2. **生成参数**: 修改 `generate_response()` 方法中的 `max_new_tokens`, `temperature` 等参数
3. **评估维度**: 在 `test_with_external_model.py` 中修改评估提示词

## 注意事项

1. **GPU内存**: 测试需要足够的GPU内存加载模型，建议至少16GB显存
2. **测试时间**: 完整测试可能需要较长时间，取决于测试样本数量和模型大小
3. **API费用**: 使用外部模型评估会产生API调用费用，请注意控制测试样本数量
4. **模型路径**: 确保模型文件路径配置正确，如果模型不在本地，请先下载

## 故障排除

### 问题1: 模型加载失败

```
错误: 模型路径不存在
```

**解决方案**: 
- 检查模型是否已下载到正确位置
- 如果模型在远程，请参考 `server/src/ai_service_vllm.py` 配置模型下载

### 问题2: CUDA内存不足

```
错误: CUDA out of memory
```

**解决方案**:
- 减小测试样本数量
- 使用更小的模型
- 在 `load_model()` 中设置 `torch_dtype=torch.float16`
- 使用模型量化

### 问题3: ROUGE计算错误

```
错误: 生成文本或参考文本为空
```

**解决方案**:
- 检查模型是否正确生成了回复
- 确保测试数据中的 `output` 字段不为空

### 问题4: API调用失败

```
错误: OpenAI API调用失败
```

**解决方案**:
- 检查API密钥是否正确
- 检查网络连接
- 如果使用国内API，修改API调用代码

## 联系支持

如有问题，请查看:
- `server/src/ai_service_vllm.py`: 模型加载参考代码
- `server/data/query_train.json`: 数据格式参考
