#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import logging
import torch
import re

# ==========================================
# 1. GPU 物理隔离配置
# ==========================================
# 物理显卡 3,4,5 用于 vLLM (逻辑ID 0,1,2)
# 物理显卡 6 用于 RAG (逻辑ID 3)
os.environ["CUDA_VISIBLE_DEVICES"] = "3,4,5,6"

# ------------------------------------------
# 路径配置
# ------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(SERVER_ROOT, "src")
MODEL_DIR = os.path.join(SERVER_ROOT, "model-dir")

sys.path.append(SRC_DIR)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ------------------------------------------
# 导入服务
# ------------------------------------------
try:
    from ai_service_vllm import get_vllm_ai_service
    from rag_service import LegalRAGService
except ImportError as e:
    logger.error(f"模块导入失败: {e}")
    sys.exit(1)

# ------------------------------------------
# 辅助函数
# ------------------------------------------
def clean_query(text: str) -> str:
    """清洗模型生成的搜索关键词"""
    text = text.replace("输出：", "").replace("查询语句：", "").strip()
    text = text.strip('"').strip("'")
    return text

# ------------------------------------------
# 核心逻辑
# ------------------------------------------
def main():
    input_file = os.path.join(CURRENT_DIR, "qa_data.jsonl")
    output_file = os.path.join(CURRENT_DIR, "finetune_vllm_final.jsonl")

    # 1. 初始化 RAG
    logger.info(">>> Step 1: 初始化 RAG 服务 (Target: Logic GPU 3)...")
    try:
        rag_service = LegalRAGService()
    except Exception as e:
        logger.error(f"RAG 初始化失败: {e}")
        return

    # 2. 初始化 vLLM
    logger.info(">>> Step 2: 初始化 vLLM 服务 (Target: Logic GPU 0,1)...")
    try:
        ai_service = get_vllm_ai_service(model_path=MODEL_DIR)
        ai_service.load_model()
    except Exception as e:
        logger.error(f"vLLM 初始化失败: {e}")
        return

    logger.info(f"开始处理数据: {input_file}")
    
    try:
        total_lines = sum(1 for _ in open(input_file, 'r', encoding='utf-8') if _.strip())
    except FileNotFoundError:
        logger.error("找不到输入文件")
        return

    processed_count = 0
    success_count = 0

    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            if not line.strip(): continue
            processed_count += 1
            
            if processed_count % 10 == 0:
                logger.info(f"进度: [{processed_count}/{total_lines}] ...")

            try:
                data = json.loads(line)
                raw_question = data.get('question', '')
                raw_answer = data.get('answer', '')
                
                # ==========================================
                # Step A: 口语转法言法语 (Rewrite)
                # ==========================================
                rewrite_prompt = f"""任务：将以下市民投诉转化为一个标准的、书面化的法律查询语句。
【市民投诉】{raw_question}
【要求】去除所有专有名词，输出为连贯的法律问题。
请输出查询语句："""
                
                rewrite_resp = ai_service.generate_response(
                    user_input=rewrite_prompt,
                    system_prompt="你是一个法律检索专家。",
                    temperature=0.3,
                    max_tokens=100,
                    stream=False 
                )
                search_query = clean_query(rewrite_resp['reply'])

                # ==========================================
                # Step B: RAG 检索
                # ==========================================
                legal_context_str = ""
                try:
                    retrieved_docs = rag_service.search(search_query, top_k=3)
                    if retrieved_docs:
                        doc_texts = []
                        for idx, doc in enumerate(retrieved_docs):
                            source = doc.get('source', '法律法规')
                            content = doc.get('content', '').strip()
                            doc_texts.append(f"条款{idx+1}（出自《{source}》）: {content}")
                        legal_context_str = "\n".join(doc_texts)
                    else:
                        legal_context_str = "（未检索到具体匹配的法律条文）"
                except Exception as e:
                    logger.warning(f"RAG检索微小异常: {e}")
                    legal_context_str = "（检索服务暂时不可用）"

                # ==========================================
                # Step C: 生成正式回复 (Generation)
                # ==========================================
                # 注意：这里我们**仍然使用** raw_answer 来生成 target output，
                # 因为我们要教模型输出“正确的回复”。如果这里不给 raw_answer，模型生成出来的 output 也是空的。
                if not raw_answer or len(raw_answer.strip()) < 5:
                    processing_status = "（暂无详细结案记录，请生成‘已受理并正在调查’的阶段性回复）"
                else:
                    processing_status = raw_answer

                final_user_input = f"""请为以下市民诉求撰写一份正式答复。

【市民诉求摘要】
{raw_question}

【参考法律依据（RAG检索）】
{legal_context_str}

【当前办理进度/结果】
{processing_status}

【写作指令】
1. **首部**：使用“尊敬的市民您好”，并确认收到投诉。
2. **正文**：
   - 有结果则陈述结果（基于【当前办理进度】）。
   - 无结果则告知已受理，正在调查。
   - 必须结合【参考法律依据】说明合理性。
3. **尾部**：感谢监督。
4. **格式**：禁止使用Markdown标题，直接分段书写。

请直接生成回复内容："""

                final_resp = ai_service.generate_response(
                    user_input=final_user_input,
                    system_prompt="你是一名专业的政府投诉处理AI助手。",
                    temperature=0.4,
                    max_tokens=600,
                    stream=False
                )
                final_output = final_resp['reply']

                # ==========================================
                # Step D: 保存 (已根据你的要求修改)
                # ==========================================
                # 【修改点】Input 只包含 "参考法条"，不包含 "原始处理记录"
                # 这样训练出来的模型，输入只有“问题+法律”，它需要学会自己组织语言。
                final_input_content = f"【参考法律条文】\n{legal_context_str}"
                
                train_item = {
                    "instruction": raw_question,
                    "input": final_input_content,
                    "output": final_output,
                    "system": "你是一名专业的政府投诉处理AI助手，专门负责生成标准化的投诉处理回复。\n\n你的职责包括：\n1. 准确理解市民的投诉内容\n2. 严格按照政府工作流程和法律法规进行回复\n3. 使用正式、规范的公务语言\n\n请根据市民投诉内容，生成符合上述要求的专业回复。"
                }

                f_out.write(json.dumps(train_item, ensure_ascii=False) + "\n")
                f_out.flush()
                success_count += 1

            except Exception as e:
                logger.error(f"处理第 {processed_count} 行时出错: {e}")
                continue

    # 卸载模型
    ai_service.unload_model()
    logger.info(f"任务完成！成功处理 {success_count}/{total_lines} 条数据。")
    logger.info(f"结果已保存至: {output_file}")

if __name__ == "__main__":
    main()