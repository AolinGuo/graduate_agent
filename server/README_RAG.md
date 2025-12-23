# RAG知识库系统使用指南

## 📚 概述

本系统基于RAG（Retrieval-Augmented Generation，检索增强生成）技术，为模型提供法律知识库支持。系统使用`server/data/Office_law`目录下的法律文档和行政法规构建向量知识库，支持语义检索和智能问答。

## 🎯 主要功能

1. **文档加载**: 自动加载法律和行政法规文档
2. **文档切分**: 智能切分长文档为合适的片段
3. **向量化**: 使用中文向量模型将文档转换为向量表示
4. **语义检索**: 根据问题检索最相关的法律条款
5. **智能问答**: 结合检索结果和AI模型生成专业回答

## 📦 依赖安装

首先安装所需的依赖包：

```bash
cd server
pip install -r requirements.txt
```

主要依赖包括：
- `langchain`: RAG框架
- `langchain-community`: 社区组件
- `faiss-cpu`: 向量数据库
- `sentence-transformers`: 中文向量模型
- `chromadb`: 可选的向量数据库
- `tiktoken`: Token计数工具

## 🚀 快速开始

### 1. 初始化知识库

运行初始化脚本构建向量知识库：

```bash
cd server
python init_rag_knowledge_base.py
```

首次运行会：
1. 加载所有法律文档（约120个法律 + 160个行政法规）
2. 下载中文向量模型（shibing624/text2vec-base-chinese）
3. 将文档切分为片段
4. 生成向量并构建索引
5. 保存向量库到磁盘

**注意**: 首次构建可能需要5-10分钟，请耐心等待。

### 2. 启动服务器

```bash
python run.py
```

服务器启动后，RAG知识库会自动加载（如果已构建）。

### 3. 使用API接口

#### 3.1 查看知识库状态

```bash
curl http://localhost:8888/rag/status
```

响应示例：
```json
{
  "success": true,
  "status": "ready",
  "statistics": {
    "is_initialized": true,
    "data_directory": "/path/to/server/data/Office_law",
    "vector_store_path": "/path/to/server/data/vector_store",
    "metadata": {
      "total_documents": 280,
      "total_chunks": 15000,
      "categories": {
        "法律": 120,
        "行政法规": 160
      }
    }
  }
}
```

#### 3.2 检索相关文档

```bash
curl -X POST http://localhost:8888/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "公司法中关于股东权利的规定",
    "top_k": 5
  }'
```

响应示例：
```json
{
  "success": true,
  "query": "公司法中关于股东权利的规定",
  "count": 5,
  "results": [
    {
      "content": "第四条 有限责任公司的股东以其认缴的出资额为限对公司承担责任...",
      "metadata": {
        "source": "/path/to/中华人民共和国公司法.txt",
        "filename": "中华人民共和国公司法.txt",
        "category": "法律",
        "title": "中华人民共和国公司法"
      },
      "score": 0.8234
    }
  ]
}
```

#### 3.3 智能问答（检索+生成）

```bash
curl -X POST http://localhost:8888/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "股东在公司中享有哪些权利？",
    "top_k": 3,
    "use_ai": true
  }'
```

响应示例：
```json
{
  "success": true,
  "question": "股东在公司中享有哪些权利？",
  "retrieved_documents": [...],
  "answer": "根据《中华人民共和国公司法》的规定，股东主要享有以下权利：\n1. 资产收益权...\n2. 参与重大决策权...\n3. 选择管理者权...",
  "generated_at": "2025-10-29T10:30:00"
}
```

#### 3.4 重新构建知识库

```bash
curl -X POST http://localhost:8888/rag/build \
  -H "Content-Type: application/json" \
  -d '{
    "force_rebuild": true
  }'
```

## 🛠️ 配置说明

### RAG服务配置

在`src/rag_service.py`中可以配置：

```python
RAGKnowledgeBase(
    data_dir=None,                                          # 数据目录（默认：server/data/Office_law）
    vector_store_path=None,                                 # 向量库路径（默认：server/data/vector_store）
    embedding_model="shibing624/text2vec-base-chinese",    # 向量模型
    chunk_size=500,                                         # 文档片段大小
    chunk_overlap=50                                        # 片段重叠大小
)
```

### 向量模型选择

系统默认使用本地模型（`server/embedding_model/`目录），如果本地模型不存在则使用在线模型。

**推荐使用本地模型（Youtu-Embedding）**：

```bash
# 1. 创建模型目录
mkdir -p server/embedding_model

# 2. 下载 Youtu-Embedding 模型（推荐）
cd server/embedding_model
git clone https://huggingface.co/tencent/Youtu-Embedding .
# 或使用 modelscope
# git clone https://www.modelscope.cn/tencent/Youtu-Embedding.git .
```

其他可选模型：
- `tencent/Youtu-Embedding`: 腾讯优图，中文效果好（推荐）
- `shibing624/text2vec-base-chinese`: 轻量级，适合CPU
- `BAAI/bge-small-zh-v1.5`: 小型，性能更好
- `BAAI/bge-large-zh-v1.5`: 大型，性能最好（需要更多资源）

## 📊 系统架构

```
┌─────────────┐
│   用户查询   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  RAG服务层       │
│  - 查询理解     │
│  - 向量检索     │
└────────┬────────┘
         │
         ▼
┌──────────────────┐      ┌─────────────┐
│  向量数据库       │◄────│  法律文档    │
│  (FAISS)         │      │  - 法律      │
│  - 文档向量      │      │  - 行政法规  │
│  - 索引          │      └─────────────┘
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  AI生成层        │
│  - 上下文构建    │
│  - 回答生成      │
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│  返回结果    │
└─────────────┘
```

## 🔧 故障排除

### 问题1：导入错误

**错误信息**:
```
ImportError: langchain未安装，RAG功能将被禁用
```

**解决方法**:
```bash
pip install langchain langchain-community faiss-cpu sentence-transformers
```

### 问题2：向量模型下载失败

**错误信息**:
```
OSError: Can't load tokenizer for 'shibing624/text2vec-base-chinese'
```

**解决方法**:
1. 检查网络连接
2. 手动下载模型：
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('shibing624/text2vec-base-chinese')
```

### 问题3：内存不足

**错误信息**:
```
MemoryError: Unable to allocate array
```

**解决方法**:
1. 减小`chunk_size`参数（如改为300）
2. 减小`top_k`参数
3. 使用更小的向量模型
4. 增加系统内存

### 问题4：知识库加载失败

**错误信息**:
```
加载知识库失败: ...
```

**解决方法**:
```bash
# 删除旧的向量库，重新构建
rm -rf server/data/vector_store
python init_rag_knowledge_base.py
```

## 📈 性能优化

### 1. 使用GPU加速

修改`src/rag_service.py`中的向量模型配置：

```python
self.embeddings = HuggingFaceEmbeddings(
    model_name=self.embedding_model_name,
    model_kwargs={'device': 'cuda'},  # 改为cuda
    encode_kwargs={'normalize_embeddings': True}
)
```

### 2. 调整片段大小

根据实际需求调整`chunk_size`：
- 小文本（300-500）: 查询精确度高，但上下文少
- 中等文本（500-800）: 平衡精确度和上下文
- 大文本（800-1200）: 上下文丰富，但可能包含无关信息

### 3. 使用更好的向量模型

```python
embedding_model="BAAI/bge-large-zh-v1.5"
```

## 🔍 使用示例

### Python客户端示例

```python
import requests
import json

# RAG检索
def search_law(query, top_k=5):
    url = "http://localhost:8888/rag/search"
    data = {
        "query": query,
        "top_k": top_k
    }
    response = requests.post(url, json=data)
    return response.json()

# RAG问答
def ask_question(question, top_k=3):
    url = "http://localhost:8888/rag/query"
    data = {
        "question": question,
        "top_k": top_k,
        "use_ai": True
    }
    response = requests.post(url, json=data)
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 检索
    results = search_law("个人信息保护的法律要求")
    print("检索结果:")
    for i, result in enumerate(results['results'], 1):
        print(f"{i}. {result['metadata']['title']}")
    
    # 问答
    answer = ask_question("企业如何保护用户个人信息？")
    print("\n问答结果:")
    print(answer['answer'])
```

## 📝 API接口总结

| 接口 | 方法 | 功能 | 参数 |
|-----|------|------|------|
| `/rag/status` | GET | 获取知识库状态 | 无 |
| `/rag/build` | POST | 构建/重建知识库 | `force_rebuild` |
| `/rag/search` | POST | 检索相关文档 | `query`, `top_k` |
| `/rag/query` | POST | RAG问答 | `question`, `top_k`, `use_ai` |

## 📚 数据来源

- **法律**: `server/data/Office_law/法律/` (约120个文件)
  - 包括：公司法、劳动法、合同法、刑法等
  
- **行政法规**: `server/data/Office_law/行政法规/` (约160个文件)
  - 包括：各类管理条例、实施细则等

## 🎓 技术栈

- **向量数据库**: FAISS (Facebook AI Similarity Search)
- **向量模型**: text2vec-base-chinese
- **RAG框架**: LangChain
- **AI模型**: 集成现有的AI服务（transformers/vLLM）
- **Web框架**: Flask

## 📞 联系与支持

如有问题或建议，请：
1. 查看日志文件获取详细错误信息
2. 检查是否已正确安装所有依赖
3. 参考故障排除部分

---

**注意**: 首次使用需要下载向量模型，请确保网络连接正常。建议在服务器资源充足时进行知识库构建。

