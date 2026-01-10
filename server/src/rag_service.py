#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG知识库服务 - 基于法律文档的检索增强生成
支持文档加载、向量化、检索和问答功能
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pickle
import json

# 导入langchain相关模块
try:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    
    try:
        from langchain_core.documents import Document
    except ImportError:
        from langchain.schema import Document
    
    HAS_LANGCHAIN = True
except ImportError as e:
    HAS_LANGCHAIN = False
    Document = None
    logging.warning(f"langchain未安装，RAG功能将被禁用: {e}")

logger = logging.getLogger(__name__)


class RAGKnowledgeBase:
    """RAG知识库类"""
    
    def __init__(
        self,
        data_dir: str = None,
        vector_store_path: str = None,
        embedding_model: str = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        初始化RAG知识库
        
        Args:
            data_dir: 法律文档数据目录
            vector_store_path: 向量库存储路径
            embedding_model: 向量化模型名称
            chunk_size: 文档切片大小
            chunk_overlap: 文档切片重叠大小
        """
        if not HAS_LANGCHAIN:
            raise ImportError("请先安装langchain相关依赖")
            
        # 设置路径
        self.project_root = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else self.project_root / "data" / "Office_law"
        self.vector_store_path = Path(vector_store_path) if vector_store_path else self.project_root / "data" / "vector_store"
        
        # 创建向量库目录
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # 配置参数
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 设置向量模型路径（优先使用本地模型）
        if embedding_model is None:
            local_model_path = self.project_root / "embedding_model"
            if local_model_path.exists():
                self.embedding_model_name = str(local_model_path)
                logger.info(f"使用本地向量模型: {local_model_path}")
            else:
                self.embedding_model_name = "shibing624/text2vec-base-chinese"
                logger.info(f"本地模型不存在，使用在线模型: {self.embedding_model_name}")
        else:
            self.embedding_model_name = embedding_model
        
        # 初始化组件
        self.embeddings = None
        self.vector_store = None
        self.text_splitter = None
        self.documents_metadata = {}
        
        logger.info(f"RAG知识库初始化完成，数据目录: {self.data_dir}")
        logger.info(f"向量库路径: {self.vector_store_path}")
        
    def initialize_components(self):
        """初始化向量模型和文本切分器"""
        try:
            # 初始化向量化模型
            logger.info(f"加载向量化模型: {self.embedding_model_name}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                model_kwargs={'device': 'cuda','trust_remote_code': True},  # 可以改为'cuda'使用GPU
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # 初始化文本切分器
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", "。", "；", "，", " ", ""]
            )
            
            logger.info("向量模型和文本切分器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化组件失败: {e}")
            return False
    
    def load_documents(self) -> List[Document]:
        """
        加载所有法律文档
        
        Returns:
            文档列表
        """
        documents = []
        
        # 遍历法律目录
        law_dir = self.data_dir / "法律"
        if law_dir.exists():
            logger.info(f"加载法律文档: {law_dir}")
            for file_path in law_dir.glob("*.txt"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 创建文档对象
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": str(file_path),
                            "filename": file_path.name,
                            "category": "法律",
                            "title": file_path.stem
                        }
                    )
                    documents.append(doc)
                    
                except Exception as e:
                    logger.error(f"加载文件失败 {file_path}: {e}")
        
        # 遍历行政法规目录
        regulation_dir = self.data_dir / "行政法规"
        if regulation_dir.exists():
            logger.info(f"加载行政法规文档: {regulation_dir}")
            for file_path in regulation_dir.glob("*.txt"):
                # 跳过"处理后_"开头的重复文件
                if file_path.name.startswith("处理后_"):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 创建文档对象
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": str(file_path),
                            "filename": file_path.name,
                            "category": "行政法规",
                            "title": file_path.stem
                        }
                    )
                    documents.append(doc)
                    
                except Exception as e:
                    logger.error(f"加载文件失败 {file_path}: {e}")
        
        logger.info(f"总共加载文档数量: {len(documents)}")
        return documents
    
    def build_knowledge_base(self, force_rebuild: bool = False):
        """
        构建知识库（加载文档、切分、向量化、存储）
        
        Args:
            force_rebuild: 是否强制重建知识库
        """
        # 检查是否已存在向量库
        faiss_index_path = self.vector_store_path / "index.faiss"
        faiss_pkl_path = self.vector_store_path / "index.pkl"
        metadata_path = self.vector_store_path / "metadata.json"
        
        if not force_rebuild and faiss_index_path.exists() and faiss_pkl_path.exists():
            logger.info("检测到已有向量库，正在加载...")
            try:
                self.load_knowledge_base()
                return True
            except Exception as e:
                logger.warning(f"加载现有向量库失败: {e}，将重新构建")
        
        # 初始化组件
        if not self.initialize_components():
            raise Exception("初始化组件失败")
        
        # 加载文档
        logger.info("开始加载法律文档...")
        documents = self.load_documents()
        
        if not documents:
            raise Exception("未找到任何文档")
        
        # 文档切分
        logger.info("开始切分文档...")
        split_docs = self.text_splitter.split_documents(documents)
        logger.info(f"文档切分完成，总片段数: {len(split_docs)}")
        
        # 构建向量库
        logger.info("开始构建向量库（这可能需要一些时间）...")
        try:
            self.vector_store = FAISS.from_documents(
                documents=split_docs,
                embedding=self.embeddings
            )
            
            # 保存向量库
            logger.info("保存向量库到磁盘...")
            self.vector_store.save_local(str(self.vector_store_path))
            
            # 保存元数据
            self.documents_metadata = {
                "total_documents": len(documents),
                "total_chunks": len(split_docs),
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "embedding_model": self.embedding_model_name,
                "categories": {
                    "法律": len([d for d in documents if d.metadata.get("category") == "法律"]),
                    "行政法规": len([d for d in documents if d.metadata.get("category") == "行政法规"])
                }
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.documents_metadata, f, ensure_ascii=False, indent=2)
            
            logger.info("知识库构建完成！")
            logger.info(f"总文档数: {self.documents_metadata['total_documents']}")
            logger.info(f"总片段数: {self.documents_metadata['total_chunks']}")
            return True
            
        except Exception as e:
            logger.error(f"构建向量库失败: {e}")
            raise
    
    def load_knowledge_base(self):
        """加载已有的知识库"""
        try:
            # 初始化向量模型
            if not self.embeddings:
                if not self.initialize_components():
                    raise Exception("初始化组件失败")
            
            # 加载向量库
            logger.info("加载向量库...")
            self.vector_store = FAISS.load_local(
                str(self.vector_store_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            # 加载元数据
            metadata_path = self.vector_store_path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.documents_metadata = json.load(f)
            
            logger.info("知识库加载完成")
            return True
            
        except Exception as e:
            logger.error(f"加载知识库失败: {e}")
            raise
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询问题
            top_k: 返回的文档数量
            
        Returns:
            相关文档列表
        """
        if not self.vector_store:
            raise Exception("知识库未初始化，请先构建或加载知识库")
        
        try:
            # 相似度搜索
            docs_with_scores = self.vector_store.similarity_search_with_score(
                query=query,
                k=top_k
            )
            
            # 格式化结果
            results = []
            for doc, score in docs_with_scores:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return {
            "is_initialized": self.vector_store is not None,
            "data_directory": str(self.data_dir),
            "vector_store_path": str(self.vector_store_path),
            "metadata": self.documents_metadata
        }


# 全局RAG服务实例
_rag_service_instance: Optional[RAGKnowledgeBase] = None


def get_rag_service(
    data_dir: str = None,
    vector_store_path: str = None,
    force_rebuild: bool = False
) -> RAGKnowledgeBase:
    """
    获取RAG服务单例
    
    Args:
        data_dir: 数据目录
        vector_store_path: 向量库路径
        force_rebuild: 是否强制重建
        
    Returns:
        RAG服务实例
    """
    global _rag_service_instance
    
    if _rag_service_instance is None:
        logger.info("创建新的RAG服务实例")
        _rag_service_instance = RAGKnowledgeBase(
            data_dir=data_dir,
            vector_store_path=vector_store_path
        )
    
    return _rag_service_instance


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 创建知识库
    rag = RAGKnowledgeBase()
    rag.build_knowledge_base(force_rebuild=True)
    
    # 测试检索
    results = rag.search("公司法中关于股东权利的规定", top_k=3)
    for i, result in enumerate(results, 1):
        print(f"\n===== 结果 {i} =====")
        print(f"来源: {result['metadata']['title']}")
        print(f"分数: {result['score']:.4f}")
        print(f"内容: {result['content'][:200]}...")

