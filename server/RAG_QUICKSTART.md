# RAG知识库快速开始指南 🚀

## 📋 三步快速开始

### 步骤1：安装依赖

```bash
cd server
pip install -r requirements.txt
```

这将安装所有必要的依赖包，包括：
- `langchain` - RAG框架
- `faiss-cpu` - 向量数据库
- `sentence-transformers` - 中文向量模型

### 步骤2：下载向量模型（推荐使用本地模型）

```bash
# 创建模型目录并下载 Embedding 模型
cd server
hf download Qwen/Qwen3-Embedding-0.6B   --local-dir embedding_model

```

**注意**: 如果不下载本地模型，系统会自动下载在线模型（约400MB）

### 步骤3：初始化知识库

```bash
python create_rag.py
```

首次运行会：
- 加载所有法律文档（~280个文件）
- 使用本地向量模型（或在线模型）
- 生成向量索引并保存

⏱️ **预计时间**: 5-10分钟（取决于硬件）

### 步骤4：启动服务并测试

```bash
# 启动服务器
python run.py

# 在另一个终端测试RAG功能
python test_rag.py
```

## 🎯 核心API接口

### 1. 检索相关法律文档

```bash
curl -X POST http://localhost:8888/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "公司法关于股东权利的规定",
    "top_k": 5
  }'
```

**返回**: 最相关的5条法律条款

### 2. 智能问答

```bash
curl -X POST http://localhost:8888/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "股东在公司中享有哪些权利？",
    "top_k": 3,
    "use_ai": true
  }'
```

**返回**: 基于法律文档的AI生成回答

### 3. 查看知识库状态

```bash
curl http://localhost:8888/rag/status
```

**返回**: 知识库统计信息

## 🔧 常见问题

### Q1: 首次运行需要下载什么？

A: 推荐预先下载 Youtu-Embedding 模型到 `server/embedding_model/` 目录。如果没有本地模型，系统会自动下载在线模型（约400MB）。

### Q2: 知识库存储在哪里？

A: `server/data/vector_store/` 目录，包含：
- `index.faiss` - 向量索引
- `index.pkl` - 元数据
- `metadata.json` - 统计信息

### Q3: 如何重新构建知识库？

```bash
# 方法1：使用脚本重新初始化
python init_rag_knowledge_base.py

# 方法2：使用API接口
curl -X POST http://localhost:8888/rag/build \
  -H "Content-Type: application/json" \
  -d '{"force_rebuild": true}'
```

### Q4: 如何添加新的法律文档？

1. 将新文档放入 `server/data/Office_law/法律/` 或 `行政法规/`
2. 重新构建知识库：`python init_rag_knowledge_base.py`

### Q5: 系统资源要求？

- **最低配置**: 4GB RAM, CPU
- **推荐配置**: 8GB+ RAM, GPU（可选，用于加速）
- **存储空间**: ~2GB（包括模型和向量库）

## 📊 数据统计

当前知识库包含：
- **法律文档**: 约120个（如公司法、劳动法、民法典等）
- **行政法规**: 约160个（各类管理条例和实施细则）
- **总片段数**: 约15,000个（根据文档大小）

## 🎓 Python集成示例

```python
import requests

# 初始化客户端
class RAGClient:
    def __init__(self, base_url="http://localhost:8888"):
        self.base_url = base_url
    
    def search(self, query, top_k=5):
        """检索相关文档"""
        response = requests.post(
            f"{self.base_url}/rag/search",
            json={"query": query, "top_k": top_k}
        )
        return response.json()
    
    def ask(self, question, top_k=3, use_ai=True):
        """智能问答"""
        response = requests.post(
            f"{self.base_url}/rag/query",
            json={
                "question": question,
                "top_k": top_k,
                "use_ai": use_ai
            }
        )
        return response.json()

# 使用示例
client = RAGClient()

# 检索
results = client.search("个人信息保护")
for doc in results['results']:
    print(f"- {doc['metadata']['title']}")

# 问答
answer = client.ask("企业如何保护用户隐私？")
print(answer['answer'])
```

## 📚 进一步学习

- **详细文档**: 参考 `README_RAG.md`
- **API接口**: 查看 `server/src/views.py` 中的RAG接口部分
- **核心代码**: 查看 `server/src/rag_service.py`

## 🆘 获取帮助

遇到问题？尝试以下步骤：

1. **查看日志**: 运行服务器时的输出信息
2. **检查状态**: `curl http://localhost:8888/rag/status`
3. **重新构建**: `python init_rag_knowledge_base.py`
4. **查看文档**: `README_RAG.md` 中的故障排除部分

---

**🎉 现在开始使用RAG知识库吧！**

需要帮助？参考完整文档 `README_RAG.md`

