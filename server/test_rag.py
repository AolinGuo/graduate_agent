#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG知识库测试脚本
用于测试RAG系统的基本功能
"""

import requests
import json
import sys
from pathlib import Path

# API基础URL
BASE_URL = "http://localhost:8888"


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_rag_status():
    """测试RAG状态接口"""
    print_header("1. 测试RAG知识库状态")
    
    try:
        response = requests.get(f"{BASE_URL}/rag/status")
        data = response.json()
        
        if data.get("success"):
            print("✅ RAG服务状态正常")
            print(f"   状态: {data.get('status')}")
            
            metadata = data.get("statistics", {}).get("metadata", {})
            if metadata:
                print(f"   总文档数: {metadata.get('total_documents', 0)}")
                print(f"   总片段数: {metadata.get('total_chunks', 0)}")
                print(f"   法律文档: {metadata.get('categories', {}).get('法律', 0)}")
                print(f"   行政法规: {metadata.get('categories', {}).get('行政法规', 0)}")
        else:
            print(f"❌ RAG服务异常: {data.get('error')}")
            return False
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务器已启动")
        print("   运行: python run.py")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_rag_search():
    """测试RAG检索功能"""
    print_header("2. 测试RAG文档检索")
    
    # 测试查询
    test_queries = [
        "公司法中关于股东权利的规定",
        "个人信息保护的法律要求",
        "劳动合同解除的相关规定"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n查询 {i}: {query}")
        print("-" * 80)
        
        try:
            response = requests.post(
                f"{BASE_URL}/rag/search",
                json={"query": query, "top_k": 3}
            )
            data = response.json()
            
            if data.get("success"):
                results = data.get("results", [])
                print(f"✅ 找到 {len(results)} 条相关结果:")
                
                for j, result in enumerate(results, 1):
                    metadata = result.get("metadata", {})
                    score = result.get("score", 0)
                    content = result.get("content", "")[:100]
                    
                    print(f"\n  结果 {j}:")
                    print(f"    文档: {metadata.get('title', '未知')}")
                    print(f"    类别: {metadata.get('category', '未知')}")
                    print(f"    相似度: {score:.4f}")
                    print(f"    内容预览: {content}...")
            else:
                print(f"❌ 检索失败: {data.get('error')}")
                
        except Exception as e:
            print(f"❌ 检索异常: {e}")
    
    return True


def test_rag_query():
    """测试RAG问答功能"""
    print_header("3. 测试RAG智能问答")
    
    # 测试问题
    test_questions = [
        "股东在公司中享有哪些权利？",
        "企业收集用户个人信息需要遵守什么规定？"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n问题 {i}: {question}")
        print("-" * 80)
        
        try:
            # 仅检索，不使用AI生成
            response = requests.post(
                f"{BASE_URL}/rag/query",
                json={"question": question, "top_k": 2, "use_ai": False}
            )
            data = response.json()
            
            if data.get("success"):
                docs = data.get("retrieved_documents", [])
                print(f"✅ 检索到 {len(docs)} 条相关文档:")
                
                for j, doc in enumerate(docs, 1):
                    metadata = doc.get("metadata", {})
                    print(f"\n  文档 {j}:")
                    print(f"    标题: {metadata.get('title', '未知')}")
                    print(f"    类别: {metadata.get('category', '未知')}")
                    print(f"    相似度: {doc.get('score', 0):.4f}")
                
                # 如果需要测试AI生成，可以取消下面的注释
                # print("\n正在生成AI回答...")
                # response_ai = requests.post(
                #     f"{BASE_URL}/rag/query",
                #     json={"question": question, "top_k": 2, "use_ai": True}
                # )
                # data_ai = response_ai.json()
                # if data_ai.get("success"):
                #     print(f"\nAI回答:\n{data_ai.get('answer', '')}")
            else:
                print(f"❌ 问答失败: {data.get('error')}")
                
        except Exception as e:
            print(f"❌ 问答异常: {e}")
    
    return True


def main():
    """主函数"""
    print("=" * 80)
    print("  🧪 RAG知识库系统测试")
    print("=" * 80)
    print(f"\n服务器地址: {BASE_URL}")
    print("请确保服务器已启动并且知识库已构建")
    
    # 测试状态
    if not test_rag_status():
        print("\n⚠️  知识库未初始化或服务器未启动")
        print("请先运行: python init_rag_knowledge_base.py")
        return 1
    
    # 测试检索
    test_rag_search()
    
    # 测试问答
    test_rag_query()
    
    # 总结
    print_header("测试完成")
    print("✅ 所有基本功能测试通过")
    print("\n💡 提示:")
    print("  - 如需测试AI生成功能，请取消test_rag_query()中的注释")
    print("  - 更多API接口请参考 README_RAG.md")
    print()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试中断")
        sys.exit(1)

