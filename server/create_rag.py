#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG知识库初始化脚本
用于构建和初始化法律文档知识库
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 RAG知识库初始化脚本")
    print("=" * 80)
    
    try:
        # 导入RAG服务
        from src.rag_service import RAGKnowledgeBase
        
        print("\n📚 开始构建法律知识库...")
        print("数据源: server/data/Office_law/")
        print("包含: 法律文档和行政法规")
        print("-" * 80)
        
        # 创建RAG服务实例
        rag = RAGKnowledgeBase()
        
        # 检查向量模型
        logger.info(f"向量模型: {rag.embedding_model_name}")
        
        # 询问是否强制重建
        force_rebuild = False
        vector_store_exists = (rag.vector_store_path / "index.faiss").exists()
        
        if vector_store_exists:
            print("\n⚠️  检测到已存在的向量库")
            user_input = input("是否强制重建？(y/N): ").strip().lower()
            force_rebuild = user_input == 'y'
        else:
            print("\n✨ 未检测到现有向量库，将创建新的知识库")
            force_rebuild = True
        
        # 构建知识库
        print("\n" + "=" * 80)
        print("开始构建知识库（这可能需要几分钟时间，请耐心等待）...")
        print("=" * 80 + "\n")
        
        rag.build_knowledge_base(force_rebuild=force_rebuild)
        
        # 显示统计信息
        stats = rag.get_statistics()
        metadata = stats.get("metadata", {})
        
        print("\n" + "=" * 80)
        print("✅ 知识库构建完成！")
        print("=" * 80)
        print(f"\n📊 统计信息:")
        print(f"  - 总文档数: {metadata.get('total_documents', 0)}")
        print(f"  - 总片段数: {metadata.get('total_chunks', 0)}")
        print(f"  - 法律文档: {metadata.get('categories', {}).get('法律', 0)}")
        print(f"  - 行政法规: {metadata.get('categories', {}).get('行政法规', 0)}")
        print(f"  - 向量模型: {metadata.get('embedding_model', 'N/A')}")
        print(f"  - 片段大小: {metadata.get('chunk_size', 0)}")
        print(f"  - 重叠大小: {metadata.get('chunk_overlap', 0)}")
        print(f"\n💾 向量库路径: {rag.vector_store_path}")
        
        # 测试检索
        print("\n" + "=" * 80)
        print("🔍 测试检索功能...")
        print("=" * 80)
        
        test_queries = [
            "公司法中关于股东权利的规定",
            "个人信息保护的法律要求",
            "劳动合同法关于解除劳动合同的规定"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n测试查询 {i}: {query}")
            try:
                results = rag.search(query, top_k=2)
                print(f"  找到 {len(results)} 条相关结果:")
                for j, result in enumerate(results, 1):
                    print(f"    [{j}] {result['metadata']['title']} (相似度分数: {result['score']:.4f})")
            except Exception as e:
                print(f"  ❌ 检索失败: {e}")
        
        print("\n" + "=" * 80)
        print("🎉 RAG知识库初始化完成！")
        print("=" * 80)
        print("\n可用的API接口:")
        print("  - GET  /rag/status        - 查看知识库状态")
        print("  - POST /rag/build         - 重新构建知识库")
        print("  - POST /rag/search        - 检索相关文档")
        print("  - POST /rag/query         - RAG问答（检索+生成）")
        print("\n使用示例:")
        print('  curl -X POST http://localhost:8888/rag/search \\')
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'{"query": "公司法关于股东权利", "top_k": 5}\'')
        print()
        
        return 0
        
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        print("\n❌ 初始化失败：缺少必要的依赖包")
        print("请运行: pip install -r requirements.txt")
        print("\n确保已安装以下依赖:")
        print("  - langchain")
        print("  - langchain-community")
        print("  - faiss-cpu")
        print("  - sentence-transformers")
        return 1
        
    except Exception as e:
        logger.error(f"初始化失败: {e}", exc_info=True)
        print(f"\n❌ 初始化失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

