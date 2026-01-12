import os
# ================= 指定 GPU 6 =================
# 【已注释】不再在此处设置 CUDA_VISIBLE_DEVICES，由主程序统一管理GPU分配
# os.environ["CUDA_VISIBLE_DEVICES"] = "6"
# =============================================

from langchain_community.vectorstores import FAISS
# 兼容导入
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

class LegalRAGService:
    def __init__(self, device: str = None):
        # 1. 定义路径 (根据你之前的设定)
        self.vector_db_path = os.path.join("rag_vector")
        self.model_path = os.path.join("embedding_model")
        self.vector_db = None
        
        # 2. 设备配置：如果未指定，默认使用 cuda:4（逻辑GPU 4，对应物理GPU 4）
        # 当 CUDA_VISIBLE_DEVICES="0,1,2,3,4" 时，逻辑GPU 4 = 物理GPU 4
        self.device = device if device else "cuda:4"
        
        # 3. 初始化加载
        self._load_service()

    def _load_service(self):
        """加载 Embedding 模型和 FAISS 向量库"""
        print("🚀 正在启动检索服务...")
        
        # 使用配置的设备
        device = self.device
        print(f"   Using device: {device.upper()}")

        try:
            # A. 加载 Embedding 模型 (必须与建库时参数一致)
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.model_path,
                model_kwargs={'device': device, 'trust_remote_code': True}, # 关键：允许腾讯模型代码
                encode_kwargs={'normalize_embeddings': True}
            )

            # B. 加载 FAISS 向量库
            # allow_dangerous_deserialization=True 是必须的，允许加载本地 pickle 文件
            self.vector_db = FAISS.load_local(
                self.vector_db_path, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
            print("✅ 向量库加载成功！服务已就绪。")
            
        except Exception as e:
            print(f"❌ 服务启动失败: {e}")
            raise e

    def search(self, query, top_k=5):
        """
        核心功能：根据问题检索最相关的法条
        :param query: 用户的提问
        :param top_k: 返回几条最相关的结果
        :return: 包含 content 和 metadata 的列表
        """
        if not self.vector_db:
            return []

        print(f"\n🔍 正在检索: {query}")
        
        # 执行相似度搜索
        # similarity_search_with_score 会返回 (文档, 距离分数)
        # 距离越小越好 (L2 distance)
        results = self.vector_db.similarity_search_with_score(query, k=top_k)
        
        parsed_results = []
        for doc, score in results:
            item = {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "未知来源"),
                "id": doc.metadata.get("id", ""),
                "score": float(score) # 距离分数
            }
            parsed_results.append(item)
            
        return parsed_results

# ================= 测试代码 =================
if __name__ == "__main__":
    # 实例化服务 (只会加载一次模型)
    rag = LegalRAGService()
    
    # 模拟几个测试问题
    test_queries = [
        "合同违约需要赔偿多少钱？",
        "买到假货怎么处理？",
        "非法捕猎野生动物判几年？"
    ]
    
    for q in test_queries:
        answers = rag.search(q, top_k=2)
        print(f"👉 问题: {q}")
        for i, ans in enumerate(answers):
            print(f"   [结果 {i+1}] (Score: {ans['score']:.4f})")
            print(f"   来源: 《{ans['source']}》{ans['id']}")
            print(f"   内容: {ans['content'][:80]}...") # 只显示前80字
        print("-" * 50)