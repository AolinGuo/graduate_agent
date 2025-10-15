# 快速修复总结

## ✅ 已修复的问题

### 1. GPU显存不足问题
**问题**：CUDA error: device-side assert triggered

**原因**：GPU选择不当，部分GPU被其他进程占用

**解决方案**：
```python
# server/src/ai_service.py 第50行
physical_gpu = "2"  # 使用GPU 2（RTX 4090）
```

### 2. 时间戳生成错误
**问题**：`'Model' object has no attribute '_get_current_time'`

**原因**：调用了不存在的私有方法

**解决方案**：
```python
# server/src/views.py
from datetime import datetime

# 替换所有 model._get_current_time() 为
datetime.now().isoformat()
```

## 🎯 当前状态

### AI功能
- ✅ 模型加载：正常
- ✅ AI回复生成：正常
- ✅ GPU 2运行：正常

### 测试验证
```bash
cd server
source .venv/bin/activate

# 测试AI功能
python -c "
from src.ai_service import get_ai_service
ai_service = get_ai_service()
reply = ai_service.generate_reply_suggestion('商品质量问题')
print('✅ 成功:', reply[:100])
"
```

## 🚀 启动服务

```bash
cd server
source .venv/bin/activate
python run.py
```

服务将在 http://localhost:5000 启动

## 📝 修改的文件

1. **server/src/ai_service.py** - GPU配置
   - 第50行：设置使用GPU 2

2. **server/src/views.py** - 时间戳修复
   - 导入datetime模块
   - 替换_get_current_time()调用

3. **client/src/stores/complaint-store.ts** - 超时配置
   - 第11行：timeout从10秒改为120秒

## ⚠️ 注意事项

1. **GPU 2使用**：确保GPU 2可用，如被占用可改为GPU 5
2. **首次加载慢**：模型首次加载需10-15秒
3. **服务重启**：修改配置后需重启服务生效

## 🔧 快速切换GPU

如果GPU 2不可用，修改：
```python
# server/src/ai_service.py 第50行
physical_gpu = "5"  # 或其他空闲GPU
```

然后重启服务。

---
**修复时间**：2025-10-15
**状态**：✅ 已修复并验证

