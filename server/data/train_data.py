#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import logging

# ==========================================
# 1. GPU 配置 (必须在导入 torch 之前设置)
# ==========================================
# 将物理显卡 3,4,5,6 映射为逻辑设备 cuda:0, cuda:1...
os.environ["CUDA_VISIBLE_DEVICES"] = "3,4,5,6"

# -----------------------------------------------------------------------------
# 2. 路径配置与模块导入
# -----------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(SERVER_ROOT, "src")
MODEL_DIR = os.path.join(SERVER_ROOT, "model-dir")

# 将 src 目录加入 Python 搜索路径
sys.path.append(SRC_DIR)

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 3. 导入服务 (关键修改部分)
# -----------------------------------------------------------------------------
try:
    # 导入 AI 服务
    from ai_service import get_ai_service

    # 导入 RAG 服务类 (而不是导入函数)
    from rag_service import LegalRAGService

except ImportError as e:
    logger.error(f"模块导入失败: {e}")
    logger.error(f"当前 sys.path: {sys.path}")
    logger.error(
        "请确保 server/src/ai_service.py 和 server/src/rag_service.py 中定义了正确的类"
    )
    sys.exit(1)

# -----------------------------------------------------------------------------
# 4. 核心 Prompt 与处理逻辑
# -----------------------------------------------------------------------------


def generate_legal_search_query(ai_service, question: str) -> str:
    """
    Step 1: 将市民口语投诉重写为法言法语查询句
    """
    prompt = f"""任务：将以下市民投诉转化为一个标准的、书面化的法律查询语句。
    
    【市民投诉】
    {question}
    
    【处理要求】
    1. 去除所有专有名词（如人名、地名、品牌、单号）。
    2. 去除情绪化表达和无关细节。
    3. 提炼核心法律争议点。
    4. **输出必须是一个连贯的问句或陈述句**，不要输出关键词列表。
    
    请输出查询语句："""

    response = ai_service.generate_response(
        user_input=prompt,
        system_prompt="你是一个法律检索专家。",
        max_new_tokens=100,
        temperature=0.3,
    )

    # 清洗一下，防止模型输出 "输出：" 之类的前缀
    query = response["reply"].replace("输出：", "").strip()
    return query


def generate_official_reply(
    ai_service, question: str, old_answer: str, legal_context: str
) -> str:
    """
    步骤 2: 结合 RAG 检索结果和旧回答，生成正式回复
    (优化版：处理无记录情况，增强得体性)
    """
    # 预处理：如果 old_answer 为空或太短，标记为无记录，防止模型产生幻觉
    if not old_answer or len(old_answer.strip()) < 5:
        processing_status = "（暂无详细结案记录，请生成‘已受理并正在调查’的阶段性回复）"
    else:
        processing_status = old_answer

    system_prompt = (
        "你是一名经验丰富的市场监督管理局公关专员，擅长撰写得体、专业、有温度的官方回复。\n"
        "你的回复需要兼顾法律的严肃性和服务的亲和力。\n"
        "核心原则：\n"
        "1. 严格根据实际处理情况来回复，如果没有请自行根据法律生成回复。\n"
        "2. 引用符合该案例的法律条文。\n"
        "3. 禁止使用Markdown格式，生成完整的一段话。"
    )

    user_input = f"""请为以下市民诉求撰写一份正式答复。

【市民诉求摘要】
{question}

【参考法律依据（RAG检索）】
{legal_context}

【当前办理进度/结果】
{processing_status}

【写作指令 - 请严格执行】
请输出一段纯文本回复，包含以下逻辑结构：

1. **首部（共情与确认）**：
   - 使用尊称“尊敬的市民您好”。
   - 确认收到投诉，并使用“我局高度重视”、“已立即开展核查”等得体话术。

2. **正文（事实与法律）**：
依据【当前办理进度】，简述调查经过和最终结果（如商家同意退款、或解释为何无法支持诉求）。结合【参考法律依据】说明处理的合理性。

3. **尾部（服务承诺）**：
   - 感谢市民的监督与信任。


请直接生成回复内容，字数控制在250字左右："""

    response = ai_service.generate_response(
        user_input=user_input,
        system_prompt=system_prompt,
        max_new_tokens=600,
        temperature=0.4,  # 保持低温度，防止胡编乱造
    )

    # 后处理：清理可能残留的格式符号
    reply = response["reply"].replace("**", "").replace("###", "").strip()

    return reply


def process_dataset():
    input_path = os.path.join(CURRENT_DIR, "qa_data.jsonl")
    output_path = os.path.join(CURRENT_DIR, "finetune_dataset_processed.jsonl")

    logger.info(f"输入文件: {input_path}")
    logger.info(f"输出文件: {output_path}")
    logger.info(f"模型路径: {MODEL_DIR}")

    # 1. 初始化 AI 模型服务
    logger.info("正在加载 AI 模型...")
    ai = get_ai_service(model_path=MODEL_DIR)
    ai.load_model()

    # 2. 初始化 RAG 检索服务 (实例化类)
    logger.info("正在加载 RAG 检索服务...")
    try:
        rag_service = LegalRAGService()  # 实例化
    except Exception as e:
        logger.error(f"RAG服务初始化失败: {e}")
        return

    processed_count = 0

    try:
        total_lines = sum(
            1 for _ in open(input_path, "r", encoding="utf-8") if _.strip()
        )
    except FileNotFoundError:
        logger.error(f"找不到输入文件: {input_path}")
        return

    logger.info(f"开始处理，共 {total_lines} 条数据...")

    with (
        open(input_path, "r", encoding="utf-8") as f_in,
        open(output_path, "w", encoding="utf-8") as f_out,
    ):
        for line in f_in:
            if not line.strip():
                continue

            try:
                data = json.loads(line)
                question = data.get("question", "")
                old_answer = data.get("answer", "")

                logger.info(f"[{processed_count + 1}/{total_lines}] 正在处理...")

                # --- Step A: 重写查询 ---
                search_query = generate_legal_search_query(ai, question)

                # --- Step B: RAG 检索 ---
                legal_context_str = ""
                try:
                    # 调用类的实例方法 search
                    retrieved_docs = rag_service.search(search_query, top_k=3)

                    if retrieved_docs:
                        doc_texts = []
                        for idx, doc in enumerate(retrieved_docs):
                            source = doc.get("source", "法律法规")
                            content = doc.get("content", "").strip()
                            doc_texts.append(
                                f"条款{idx + 1}（出自《{source}》）: {content}"
                            )
                        legal_context_str = "\n".join(doc_texts)
                    else:
                        legal_context_str = "（未检索到具体匹配的法律条文）"

                except Exception as e:
                    logger.warning(f"    RAG检索异常: {e}")
                    legal_context_str = "（检索服务暂时不可用）"

                # --- Step C: 生成回复 ---
                new_reply = generate_official_reply(
                    ai, question, old_answer, legal_context_str
                )

                # --- Step D: 写入文件 ---
                final_input_content = f"【参考法律条文】\n{legal_context_str}"

                train_item = {
                    "instruction": question,
                    "input": final_input_content,
                    "output": new_reply,
                    "system": "你是一名专业的政府投诉处理AI助手，专门负责生成标准化的投诉处理回复。\n\n你的职责包括：\n1. 准确理解市民的投诉内容\n2. 严格按照政府工作流程和法律法规进行回复\n3. 使用正式、规范的公务语言\n\n请根据市民投诉内容，生成符合上述要求的专业回复。",
                }

                f_out.write(json.dumps(train_item, ensure_ascii=False) + "\n")
                f_out.flush()

                processed_count += 1

            except Exception as e:
                logger.error(f"处理数据出错: {e}")
                continue

    # 释放显存
    ai.unload_model()
    logger.info(f"全部处理完成！文件已保存至: {output_path}")


if __name__ == "__main__":
    process_dataset()
