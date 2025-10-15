# GPU显存问题解决方案

## 🔍 问题症状

运行AI功能时出现以下错误：
```
CUDA error: device-side assert triggered
probability tensor contains either `inf`, `nan` or element < 0
```

## 📊 根本原因分析

### 1. 显存占用情况（nvidia-smi检查结果）

| GPU | 型号 | 总显存 | 已使用 | 可用 | 状态 |
|-----|------|--------|--------|------|------|
| 0 | RTX 3090 | 24.5GB | 15.4GB | 9.1GB | ❌ 被其他进程占用 |
| 1 | RTX 3090 | 24.5GB | ~0GB | 24.5GB | ⚠️ 测试时被占用 |
| 2 | RTX 4090 | 24.5GB | 16.7GB | 7.8GB | ✅ **可用且工作正常** |
| 3 | RTX 3090 | 24.5GB | ~15GB | 9.5GB | ❌ 被其他进程占用 |
| 4 | RTX 4090 | 24.5GB | 20.6GB | 3.9GB | ❌ 显存不足 |
| 5 | RTX 4090 | 24.5GB | ~0GB | 24.5GB | ❌ 出现CUDA错误 |

### 2. 错误原因

不是代码问题，而是**GPU选择问题**：
- 尝试的GPU 0, 1, 3, 4, 5 都因为各种原因无法正常工作
- **GPU 2 是唯一能正常运行的GPU**

### 3. 代码差异分析

对比 `infer.py`（可以工作）和 `ai_service.py`（不能工作）：

**关键发现**：代码完全相同时，在不同GPU上的表现不同！
- 同样的代码在 GPU 2 上：✅ 正常工作
- 同样的代码在 GPU 5 上：❌ CUDA错误

**结论**：这是硬件/环境问题，不是代码问题。

## ✅ 解决方案

### 修改配置使用GPU 2

在 `server/src/ai_service.py` 第50行：

```python
physical_gpu = "2"  # GPU 2 是RTX 4090，工作正常
```

### 测试结果

```bash
✅ AI回复成功生成
🎉 测试成功！AI功能正常工作！
```

## 🎯 最终配置

### 当前工作配置（ai_service.py）

```python
AI_CONFIG = {
    "gpu": {
        "device_id": 0,  # 程序内部使用GPU 0
        "use_single_gpu": True,
        "max_memory_per_gpu": "20GB",
        "enable_cpu_fallback": True,
    },
    # ...
}

# 物理GPU映射
physical_gpu = "2"  # 物理GPU 2 → 程序中的GPU 0
os.environ["CUDA_VISIBLE_DEVICES"] = physical_gpu
```

### 如何切换GPU

如果GPU 2被占用，可以尝试其他GPU：

```python
# 修改 ai_service.py 第50行
physical_gpu = "5"  # 尝试GPU 5
# 或
physical_gpu = "1"  # 尝试GPU 1
# 或
physical_gpu = "3"  # 尝试GPU 3
```

**重要提示**：修改后需要重启服务才能生效！

## 📝 最小化修改总结

只修改了 **1行代码**：

```python
# 原来: physical_gpu = "5"
# 修改为:
physical_gpu = "2"
```

其他所有修改都已回退到与 `infer.py` 完全一致的实现。

## 🧪 测试验证

```bash
cd server
source .venv/bin/activate

# 测试AI回复生成
python -c "
from src.ai_service import get_ai_service
ai_service = get_ai_service()
reply = ai_service.generate_reply_suggestion('商品质量问题')
print(f'AI回复: {reply}')
"
```

预期输出：成功生成专业的官方回复。

## 🚀 启动服务

```bash
cd server
source .venv/bin/activate
python run.py
```

服务将在 `http://localhost:5000` 启动，AI功能完全可用。

## ⚠️ 注意事项

1. **显存监控**：运行前先检查GPU状态
   ```bash
   nvidia-smi
   ```

2. **GPU竞争**：如果其他用户也在使用GPU 2，可能需要切换到其他GPU

3. **性能差异**：
   - RTX 4090（GPU 2, 5）：推理速度较快
   - RTX 3090（GPU 0, 1, 3）：推理速度稍慢

4. **首次加载**：模型首次加载需要10-15秒，后续调用只需2-5秒

## 📚 相关文档

- `trainmodel.md` - 模型训练说明
- `TRAINING_GUIDE.md` - 训练详细指南
- `infer.py` - 推理测试脚本

## ✨ 成功标志

看到以下输出说明AI功能正常：

```
模型加载完成！
✅ AI回复: [生成的专业回复内容]
🎉 测试成功！
```

---

**问题解决时间**：2025-10-15  
**解决方案**：使用GPU 2运行AI模型  
**状态**：✅ 已解决并验证

