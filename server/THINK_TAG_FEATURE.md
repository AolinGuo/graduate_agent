# AI思考过程显示功能

## 功能描述

系统现在会自动解析并显示AI模型在 `<think>` 标签中输出的思考过程，让用户了解AI的推理逻辑。

## 实现方式

### 1. 后端解析（server/src/ai_service.py）

添加了 `_parse_response()` 方法来提取思考内容：

```python
def _parse_response(self, response: str) -> dict:
    """
    解析AI响应，提取<think>标签中的思考过程
    
    Args:
        response: AI生成的原始响应
        
    Returns:
        dict: 包含thinking和reply的字典
    """
    import re
    
    # 查找<think>标签内容
    think_pattern = r'<think>(.*?)</think>'
    think_match = re.search(think_pattern, response, re.DOTALL)
    
    if think_match:
        thinking = think_match.group(1).strip()
        # 移除<think>标签后的内容作为回复
        reply = re.sub(think_pattern, '', response, flags=re.DOTALL).strip()
    else:
        thinking = None
        reply = response.strip()
    
    return {
        'thinking': thinking,
        'reply': reply,
        'full_response': response
    }
```

### 2. API返回结构（server/src/views.py）

API接口返回的数据结构：

```python
{
    "success": True,
    "reply": "AI生成的回复内容",
    "thinking": "AI的思考过程（如果有）",
    "generated_at": "2025-10-15T10:30:00"
}
```

**涉及的接口**：
- `/ai/report` - AI报告生成
- `/ai/reply` - AI回复建议

### 3. 前端显示（client/src/pages/index.vue）

#### 数据状态
```javascript
const aiReportThinking = ref('') // AI报告的思考过程
const aiReplyThinking = ref('') // AI回复的思考过程
```

#### 获取思考内容
```javascript
// AI报告
if (response.data && response.data.success) {
  aiReport.value = response.data.report
  aiReportThinking.value = response.data.thinking || ''
}

// AI回复
if (response.data && response.data.success) {
  aiReply.value = response.data.reply
  aiReplyThinking.value = response.data.thinking || ''
}
```

#### UI显示
```vue
<!-- AI思考过程 -->
<div v-if="aiReportThinking" class="thinking-section">
  <h4 style="color: #909399; font-size: 14px; margin-bottom: 10px;">
    <el-icon style="vertical-align: middle;"><View /></el-icon>
    AI思考过程：
  </h4>
  <div class="thinking-content">
    {{ aiReportThinking }}
  </div>
</div>

<!-- AI生成的报告/回复 -->
<div class="report-text" v-html="formatReportText(aiReport)"></div>
```

### 4. 样式设计

```css
/* AI思考过程样式 */
.thinking-section {
  margin-bottom: 20px;
  padding: 15px;
  background: #f0f9ff;
  border-left: 4px solid #409eff;
  border-radius: 6px;
}

.thinking-content {
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  background: #fff;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  max-height: 200px;
  overflow-y: auto;
}
```

## 显示位置

思考过程会显示在**AI生成的内容之前**：

```
┌─────────────────────────┐
│ AI思考过程：            │
│ ┌─────────────────────┐ │
│ │ (思考内容)          │ │
│ └─────────────────────┘ │
└─────────────────────────┘

┌─────────────────────────┐
│ AI生成的报告/回复       │
│ ...                     │
└─────────────────────────┘
```

## 效果特点

1. ✅ **浅蓝色背景**：与普通内容区分
2. ✅ **眼睛图标**：表示"查看思考"
3. ✅ **等宽字体**：方便阅读推理步骤
4. ✅ **最大高度限制**：内容过长时可滚动
5. ✅ **可选显示**：只有当模型输出`<think>`标签时才显示

## 使用示例

### 模型输出格式

```
<think>
好的，用户让我生成专业的官方回复，针对市民投诉。
首先，我需要确保回复符合五个要点：
1. 收到并重视投诉
2. 处理措施或调查情况
3. 解决方案或处理结果
4. 语气专业诚恳
5. 长度适中

分析用户提供的投诉内容：商品质量问题，要求退款。
需要提到市场监管局的介入、调查情况、督促商家处理...
</think>

尊敬的市民：
您好！感谢您对我局工作的关注。您反映的商品质量问题已收悉...
```

### 用户看到的效果

```
┌─────────────────────────────────────┐
│ 👁️ AI思考过程：                      │
│ ┌─────────────────────────────────┐ │
│ │ 好的，用户让我生成专业的官方回   │ │
│ │ 复，针对市民投诉。               │ │
│ │ 首先，我需要确保回复符合五个要   │ │
│ │ 点：                             │ │
│ │ 1. 收到并重视投诉                │ │
│ │ 2. 处理措施或调查情况            │ │
│ │ ...                              │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘

尊敬的市民：
您好！感谢您对我局工作的关注。您反映
的商品质量问题已收悉...
```

## 数据修复

同时修复了报告数据传递的问题：

### 问题
- **涉及企业数**：0家（字段名错误：`company_count` → `companies_count`）
- **涉及行业数**：0个（字段名错误：`industry_count` → `industries_count`）

### 修复
```python
# server/src/views.py
report_data = {
    "total_complaints": stats.get("total_complaints", 0),
    "total_companies": stats.get("companies_count", 0),  # ✅ 修正
    "total_industries": stats.get("industries_count", 0),  # ✅ 修正
    "repeat_companies": stats.get("repeat_companies_count", 0),  # ✅ 新增
    "top_companies": _format_top_items(stats.get("company_ranking", [])),  # ✅ 修正
}
```

## 测试方法

### 1. 后端测试
```python
from src.ai_service import AIService

ai_service = AIService()
test_response = "<think>思考过程</think>\n回复内容"
result = ai_service._parse_response(test_response)

print("思考:", result['thinking'])
print("回复:", result['reply'])
```

### 2. 前端测试
1. 启动服务
2. 访问前端页面
3. 点击"生成AI报告"或"生成回复建议"
4. 观察是否显示思考过程区域

## 向后兼容

如果模型不输出 `<think>` 标签：
- `thinking` 字段为 `null`
- 前端不显示思考过程区域
- 只显示正常的回复内容

---

**实现时间**：2025-10-15  
**涉及文件**：
- `server/src/ai_service.py`
- `server/src/views.py`
- `client/src/pages/index.vue`

