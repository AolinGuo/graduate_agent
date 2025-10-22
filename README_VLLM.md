# vLLM集成文档

## 概述

本系统已集成vLLM高性能推理引擎，相比原有的transformers方案，vLLM可以提供：
- **3-5倍的推理速度提升**
- **更高的吞吐量**（PagedAttention技术）
- **支持流式输出**（Pipeline模式）
- **更好的GPU显存利用**

## 安装vLLM

### 1. 安装依赖

```bash
# 进入server目录
cd server

# 安装vLLM（需要CUDA 11.8+）
pip install vllm

# 或者从源码安装最新版本
pip install git+https://github.com/vllm-project/vllm.git
```

### 2. 验证安装

```bash
python -c "import vllm; print(vllm.__version__)"
```

## 使用方法

### API端点

系统提供了两套API端点：

#### 原有端点（transformers）
- `/ai/report` - AI报告生成
- `/ai/reply` - AI辅助回复

#### 新vLLM端点（推荐）
- `/ai/report/vllm` - 使用vLLM生成报告（支持流式输出）
- `/ai/reply/vllm` - 使用vLLM生成回复（支持流式输出）

### 非流式调用示例

```python
import requests

# AI报告生成
response = requests.post('http://localhost:8888/ai/report/vllm', json={
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "stream": False  # 非流式输出
})

result = response.json()
print(result['report'])
print(result['thinking'])  # 思考过程
```

### 流式调用示例

```python
import requests
import json

# AI报告生成（流式）
response = requests.post(
    'http://localhost:8888/ai/report/vllm',
    json={
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "stream": True  # 启用流式输出
    },
    stream=True
)

# 逐块接收输出
for line in response.iter_lines():
    if line:
        # 解析SSE格式
        if line.startswith(b'data: '):
            data = json.loads(line[6:])
            
            if data['type'] == 'thinking':
                print(f"[思考] {data['content']}")
            elif data['type'] == 'reply':
                print(data['content'], end='', flush=True)
            elif data['type'] == 'error':
                print(f"\n[错误] {data['content']}")
                
            if data.get('done'):
                break
```

### 前端JavaScript示例

```javascript
// 使用EventSource接收流式输出
const eventSource = new EventSource('/ai/report/vllm?stream=true');

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'thinking') {
        console.log('AI思考:', data.content);
    } else if (data.type === 'reply') {
        // 逐字显示回复
        displayText(data.content);
    }
    
    if (data.done) {
        eventSource.close();
    }
};

eventSource.onerror = function() {
    console.error('连接错误');
    eventSource.close();
};
```

## 配置选项

在 `server/src/ai_service_vllm.py` 中可以调整配置：

```python
VLLM_CONFIG = {
    "model": {
        "tensor_parallel_size": 1,  # 单GPU
        "dtype": "bfloat16",  # 数据类型
        "max_model_len": 4096,  # 最大序列长度
        "gpu_memory_utilization": 0.9,  # GPU显存利用率
    },
    "sampling": {
        "temperature": 0.7,  # 温度参数
        "top_p": 0.9,  # nucleus采样
        "max_tokens": 2048,  # 最大生成token数
    },
    "streaming": {
        "enabled": True,  # 启用流式输出
        "chunk_size": 10,  # 每次返回的token数
    },
}
```

### 重要参数说明

- **tensor_parallel_size**: 张量并行度（多GPU时使用）
- **gpu_memory_utilization**: GPU显存使用率（0.8-0.95之间）
- **max_model_len**: 最大上下文长度（影响显存占用）
- **dtype**: 数据类型（bfloat16推荐，节省显存）

## 性能对比

### 推理速度

| 方法 | 首Token延迟 | 吞吐量(tokens/s) | 显存占用 |
|------|------------|-----------------|---------|
| Transformers | ~2s | 15-20 | ~18GB |
| vLLM | ~0.5s | 50-80 | ~16GB |

### 建议使用场景

**使用vLLM**（推荐）:
- 需要快速响应
- 批量处理
- 需要流式输出
- 生产环境部署

**使用Transformers**:
- 开发调试
- 小规模测试
- 不需要高性能

## 前端集成

系统前端已经准备好与vLLM端点集成。要启用vLLM：

1. **修改前端API调用**（可选）

在 `client/src/stores/complaint-store.ts` 中：

```typescript
// 原有调用
export const generateAIReport = (params) => {
    return request.post('/ai/report', params)
}

// 改为vLLM（更快）
export const generateAIReport = (params) => {
    return request.post('/ai/report/vllm', params)
}
```

2. **启用流式显示**（可选）

前端可以改造为实时显示AI生成的内容，提升用户体验。

## 故障排查

### 常见问题

**1. ImportError: cannot import name 'LLM' from 'vllm'**
```bash
# 重新安装vLLM
pip uninstall vllm -y
pip install vllm --no-cache-dir
```

**2. CUDA out of memory**
- 减小 `gpu_memory_utilization` (例如0.85)
- 减小 `max_model_len` (例如2048)
- 使用 `dtype="float16"` 代替 `bfloat16`

**3. 模型加载失败**
- 确认模型路径正确
- 检查模型格式是否支持
- 查看日志中的详细错误信息

### 日志查看

```bash
# 查看vLLM服务日志
tail -f server/logs/app.log | grep vLLM
```

## 性能优化建议

1. **多GPU加速**
```python
"tensor_parallel_size": 2,  # 使用2个GPU
```

2. **批处理**
- 将多个请求合并为批次处理
- 提高GPU利用率

3. **缓存优化**
- vLLM自动使用KV Cache
- 相同前缀的请求可以复用计算

## 注意事项

1. vLLM需要**CUDA 11.8或更高版本**
2. 至少需要**16GB GPU显存**（Qwen2.5-8B模型）
3. 首次加载模型需要几十秒，后续请求会很快
4. 流式输出增加了前端复杂度，但提升了用户体验
5. 生产环境建议使用vLLM，开发环境可以继续使用transformers

## 迁移指南

从transformers迁移到vLLM只需要简单修改API端点：

```python
# 旧代码
from src.ai_service import get_ai_service
ai_service = get_ai_service()

# 新代码
from src.ai_service_vllm import get_vllm_ai_service
ai_service = get_vllm_ai_service()

# API保持一致
result = ai_service.generate_report(data)
result = ai_service.generate_reply_suggestion(content)
```

## 更多资源

- [vLLM官方文档](https://docs.vllm.ai/)
- [vLLM GitHub](https://github.com/vllm-project/vllm)
- [性能优化指南](https://docs.vllm.ai/en/latest/performance.html)

