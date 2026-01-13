#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import logging
import re

# ==========================================
# 1. 环境与路径配置
# ==========================================
# 【修改】显卡分配：确保GPU 3被使用
# 设置为 "0,1,3,4,2"，这样程序内部看到的逻辑编号为：
# 逻辑0 -> 物理0 (vLLM TP0)
# 逻辑1 -> 物理1 (vLLM TP1)
# 逻辑2 -> 物理3 (vLLM TP2)
# 逻辑3 -> 物理4 (vLLM TP3)
# 逻辑4 -> 物理2 (RAG)
os.environ["CUDA_VISIBLE_DEVICES"] = "1,3,4,6"


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(SERVER_ROOT, "src")
MODEL_DIR = os.path.join(SERVER_ROOT, "model-dir")

sys.path.append(SRC_DIR)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 2. VLLM 配置
# ==========================================
VLLM_CONFIG = {
    "model": {
        # 【修改】vLLM 将自动使用可见的前N张卡。这里设为4，即使用 cuda:0,1,2,3
        "tensor_parallel_size": 1,      
        "dtype": "bfloat16",
        "max_model_len": 16384,
        "gpu_memory_utilization": 0.85, # 使用85%显存（RTX 4090有充足显存）
        "trust_remote_code": True,
    },
    "sampling": {
        "temperature": 0.6,
        "top_p": 0.95,
        "max_tokens": 2048,
    },
}

# ==========================================
# 3. AI Service 类 (逻辑保持不变)
# ==========================================
class VLLMAIService:
    """基于vLLM的AI服务类"""

    def __init__(self, model_path: str = None):
        self.llm = None
        self.tokenizer = None
        self.model_loaded = False
        
        self.model_path = model_path if model_path else MODEL_DIR

        logger.info(f"AI服务初始化 - 模型路径: {self.model_path}")

    def load_model(self):
        """加载vLLM模型"""
        if self.model_loaded: return

        try:
            logger.info(f"正在加载基座模型 (TP={VLLM_CONFIG['model']['tensor_parallel_size']})...")
            from vllm import LLM
            from transformers import AutoTokenizer

            cfg = VLLM_CONFIG["model"]
            
            # 初始化引擎
            self.llm = LLM(
                model=self.model_path,
                tensor_parallel_size=cfg["tensor_parallel_size"],
                dtype=cfg["dtype"],
                max_model_len=cfg["max_model_len"],
                gpu_memory_utilization=cfg["gpu_memory_utilization"],
                trust_remote_code=cfg["trust_remote_code"]
            )

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model_loaded = True
            logger.info("vLLM模型加载完成！")

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise


    def generate_response(self, user_input: str, system_prompt: str = "You are a helpful assistant.", **kwargs) -> str:
        if not self.model_loaded: self.load_model()
        from vllm import SamplingParams

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        default_sampling = VLLM_CONFIG["sampling"].copy()
        default_sampling.update(kwargs)
        
        # 【修复】移除可能导致问题的停止词，使用模型默认停止词
        # 原停止词列表可能导致模型过早停止或生成异常
        sampling_params = SamplingParams(
            temperature=default_sampling.get("temperature"),
            top_p=default_sampling.get("top_p"),
            max_tokens=default_sampling.get("max_tokens"),
            stop=None,  # 使用模型默认停止词，避免意外截断
            # 移除 repetition_penalty，避免与采样参数冲突
        )

        # 调试信息
        logger.info("使用基座模型")

        try:
            # 生成响应
            outputs = self.llm.generate([prompt], sampling_params)
            response = outputs[0].outputs[0].text
            
            # 调试：打印原始输出（前200字符）
            logger.debug(f"原始输出（前200字符）: {response[:200]}")
            
            # 检查输出是否为空或过短
            if not response or len(response.strip()) < 10:
                logger.warning("输出为空或过短")

            # 额外的重复内容检测和清理
            if len(response) > 100:
                # 检查是否有明显的重复模式
                words = response.split()
                if len(words) > 20:
                    # 计算前20个词的重复率
                    unique_words = len(set(words[:20]))
                    if unique_words <= 3:  # 如果前20个词中只有3个或更少的不同词
                        logger.warning("检测到重复内容模式，截取前100字符作为输出")
                        response = response[:100] + "..."
            
            parsed = self._parse_response(response)
            reply = parsed["reply"]
            
            # 【修复】检查输出是否异常（全是重复字符，如感叹号）
            if len(reply) > 50:
                unique_chars = len(set(reply[:50]))
                if unique_chars <= 2:
                    logger.warning(f"检测到异常输出（重复字符）: {reply[:100]}...")
                    logger.error("输出异常，返回截取的内容")
                    reply = reply[:200] + "..."  # 截取前200字符作为输出
            
            return reply
        except Exception as e:
            logger.error(f"生成出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ""

    def _parse_response(self, response: str) -> dict:
        think_pattern = r"<think>(.*?)</think>"
        think_match = re.search(think_pattern, response, re.DOTALL)
        if think_match:
            thinking = think_match.group(1).strip()
            reply = re.sub(think_pattern, "", response, flags=re.DOTALL).strip()
        else:
            thinking = None
            reply = response.strip()
        return {"thinking": thinking, "reply": reply}

# ==========================================
# 4. 业务主流程
# ==========================================

def clean_query(text: str) -> str:
    text = text.replace("输出：", "").replace("查询语句：", "").strip()
    return text.strip('"').strip("'")

def main():
    # 1. 初始化 AI Service (vLLM 会占用 cuda:0,1,2,3)
    ai_service = VLLMAIService()
    
    # 2. 初始化 RAG 
    rag_service = None
    try:
        from rag_service import LegalRAGService
        logger.info("正在初始化 RAG")
        
        # 【修改】这里需要显式传入 device 参数。
        # 注意：你需要确保 rag_service.py 里的代码能接收 device 参数并传给 embedding 模型
        rag_service = LegalRAGService(device="cuda:4") 
        
    except ImportError:
        logger.error("RAG模块导入失败，请检查路径")
        return
    except TypeError:
        # 如果你的 LegalRAGService 不支持 device 参数，会进这里
        logger.warning("LegalRAGService 不支持 device 参数，尝试默认初始化（可能会导致显存冲突）...")
        try:
            rag_service = LegalRAGService()
        except Exception as e:
            logger.error(f"RAG 初始化彻底失败: {e}")
            return
    except Exception as e:
        logger.error(f"RAG 初始化未知错误: {e}")
        return

    # 读取数据
    input_file = os.path.join(CURRENT_DIR, "test.jsonl")
    output_file = os.path.join(CURRENT_DIR, "test_data_processed.jsonl")
    
    raw_data = []
    if os.path.exists(input_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip(): raw_data.append(json.loads(line))
    else:
        logger.error("输入文件不存在")
        return

    logger.info(f"开始处理 {len(raw_data)} 条数据...")
    results = []

    for idx, item in enumerate(raw_data):
        if idx % 10 == 0: logger.info(f"进度: {idx}/{len(raw_data)}")
        
        raw_q = item.get('question', '')
        raw_a = item.get('answer', '')

        # 步骤 1: 查询改写 (vLLM GPU 0-3)
        prompt_rewrite = f"任务：将以下市民诉求提取成一个事件。\n【投诉】{raw_q}\n【要求】去隐私，提取核心事件经过，精简输出。"
        search_query_raw = ai_service.generate_response(
            user_input=prompt_rewrite,
            system_prompt="你是一个事件概括专家。",
            temperature=0.1,  # 降低温度，提高准确性
            max_tokens=100
        )
        search_query = clean_query(search_query_raw)

        # 步骤 2: RAG 检索 (RAG GPU 4)
        try:
            # 检索服务通常不涉及大量显存计算，主要在 Embedding 阶段
            docs = rag_service.search(search_query, top_k=2)
            if docs:
                texts = [f"条款{i+1}（《{d['source']}》）: {d['content'].strip()}" for i, d in enumerate(docs)]
                legal_ctx = "\n".join(texts)
            else:
                legal_ctx = "（未检索到条文）"
        except Exception as e:
            logger.error(f"检索出错: {e}")
            legal_ctx = "（检索服务不可用）"

        # 步骤 3: 生成回复 (vLLM GPU 0-3)
        status = raw_a if (raw_a and len(raw_a) > 5) else "（已受理，正在调查中）"
        prompt_generate = f"""请根据法律依据和事件的结果撰写正式答复，严格按照事件结果。
【诉求】
{search_query}
【法律依据】
{legal_ctx}
【事件结果】
{status}
"""

        # 生成回复
        logger.info(f"正在生成回复（数据 {idx+1}/{len(raw_data)}）...")
        final_reply = ai_service.generate_response(
            user_input=prompt_generate,
            system_prompt="你是一名专业的政府投诉处理专员，请根据法律依据和事件结果撰写正式、客观的答复。",
            temperature=0.2,  # 降低温度，提高生成稳定性
            max_tokens=512
        )
        
        # 最终验证：如果输出仍然异常，记录警告
        if len(final_reply) > 50 and len(set(final_reply[:50])) <= 2:
            logger.error(f"警告：最终输出仍然异常（重复字符）")
        elif len(final_reply.strip()) < 20:
            logger.warning(f"警告：输出过短（{len(final_reply)}字符），可能需要调整提示词或参数")

        save_item = {
            "instruction": raw_q,
            "input": f"【法条】\n{legal_ctx}\n\n【记录】\n{raw_a}",
            "output": final_reply
        }
        results.append(save_item)

    with open(output_file, 'w', encoding='utf-8') as f:
        for res in results:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            
    logger.info(f"处理完成，结果保存在: {output_file}")

if __name__ == "__main__":
    main()