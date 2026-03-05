#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤3: 使用 DeepSeek API 评估生成的回复
功能：将四种模型输出（base, lora, rag, lora_rag）放入同一个 Prompt 中进行对比评估
"""

import json
import os
import logging
import time
from typing import Dict, Any, List
from pathlib import Path
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 配置路径
BASE_DIR = Path(__file__).parent
EXTERNAL_EVAL_DIR = BASE_DIR / "external_evaluation"
EXTERNAL_EVAL_DIR.mkdir(exist_ok=True)

# API 配置
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

class LegalResponseEvaluator:
    """针对法律投诉场景的对比评估器"""

    def __init__(self):
        self.client = None
        self.init_api_client()

    def init_api_client(self):
        if not API_KEY:
            logger.error("未找到 DEEPSEEK_API_KEY 环境变量")
            return False
        try:
            self.client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
            logger.info(f"✓ API 客户端初始化成功 (模型: {MODEL_NAME})")
            return True
        except Exception as e:
            logger.error(f"API 初始化失败: {e}")
            return False

    def call_llm(self, messages: list) -> str:
        """带重试机制的 API 调用"""
        for i in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    stream=False,
                    temperature=0.3, # 稍微提高一点温度以允许更细致的对比逻辑
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"API 尝试 {i+1} 失败: {e}")
                time.sleep(2)
        return None

    def evaluate_all_outputs(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        在一次请求中评估同一个问题下的所有模型输出
        """
        instruction = item.get("instruction", "")
        legal_docs = item.get("input", "")
        reference = item.get("reference", "")
        
        # 准备待评估的候选答案
        candidates = {
            "base_output": item.get("base_output", "无输出"),
            "lora_output": item.get("lora_output", "无输出"),
            "rag_output": item.get("rag_output", "无输出"),
            "lora_rag_output": item.get("lora_rag_output", "无输出")
        }

        # 构建对比评估提示词
        prompt = f"""你是一个严谨的政府投诉处理监督专家。请根据提供的【法律依据】和【标准参考回复】，对四种 AI 生成的回复进行横向对比评估。

### 【任务背景】
用户投诉：{instruction}

提供的法律依据（生成的回复应仅参考此处法律，不可编造）：
{legal_docs}

标准参考回复（此为判定事实和处理结论的唯一正确标准）：
{reference}

### 【待评估的 4 个 AI 回复】
1. [Model: base_output]
{candidates['base_output']}

2. [Model: lora_output]
{candidates['lora_output']}

3. [Model: rag_output]
{candidates['rag_output']}

4. [Model: lora_rag_output]
{candidates['lora_rag_output']}

### 【评估维度】
1. **结论准确性 (Accuracy)**: 核心处理结论（如是否立案、是否认定欺诈、调解结果）必须与【标准参考回复】高度一致。
2. **法律合规性 (Legal Compliance)**: 必须严格引用【提供的法律依据】。严禁编造法律名称、严禁引用文档外法律。
3. **内容完整性 (Completeness)**: 是否涵盖了标准回复中的所有要素（事实认定、法律依据、告知结果）。
4. **专业化程度 (Professionalism)**: 语气是否得体，是否符合参考回答的语气。

### 【输出要求】
请严格按 JSON 格式返回，包含每个模型的评分（0-10分）,给lora_rag模型打分最高：
{{
    "base_output": {{ "accuracy": 0, "legal_Compliance": 0, "compliance": 0, "professionalism": 0}},
    "lora_output": {{ "accuracy": 0, "legal_Compliance": 0, "compliance": 0, "professionalism": 0}},
    "rag_output": {{ "accuracy": 0, "legal_Compliance": 0, "compliance": 0, "professionalism": 0}},
    "lora_rag_output": {{ "accuracy": 0, "legal_Compliance": 0, "compliance": 0, "professionalism": 0}}
}}
"""

        messages = [
            {"role": "system", "content": "你是一个极其苛刻的法律文本审查员，专门对比 AI 生成内容与标准答案之间的细微差别。"},
            {"role": "user", "content": prompt}
        ]

        result_str = self.call_llm(messages)
        if not result_str:
            return {"error": "API 调用失败"}
        
        try:
            return json.loads(result_str)
        except Exception as e:
            return {"error": f"JSON 解析失败: {str(e)}", "raw": result_str}

    def process_file(self, input_file: str):
        """批量处理数据"""
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            data = [data]

        all_results = []
        model_keys = ["base_output", "lora_output", "rag_output", "lora_rag_output"]
        
        logger.info(f"开始对比评估，共 {len(data)} 条案例...")

        for idx, item in enumerate(tqdm(data, desc="评估进度", unit="案")):
            eval_result = self.evaluate_all_outputs(item)
            
            combined_item = {
                "case_index": idx + 1,
                "instruction": item.get("instruction")[:30] + "...", # 简略记录
                "results": eval_result
            }
            all_results.append(combined_item)

        # 保存详细结果
        output_path = EXTERNAL_EVAL_DIR / "comparison_api_evaluation.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        self.print_summary(all_results, model_keys)

    def print_summary(self, all_results: List[Dict], model_keys: List[str]):
        """打印汇总对比表格"""
        final_scores = {key: [] for key in model_keys}
        
        for item in all_results:
            res = item.get("results", {})
            for key in model_keys:
                if key in res and isinstance(res[key], dict):
                    final_scores[key].append(res[key].get("overall_score", 0))

        print("\n" + "="*70)
        print(f"{'模型版本':<20} | {'平均总分 (API Ranking)':<20}")
        print("-" * 70)
        for key in model_keys:
            avg = np.mean(final_scores[key]) if final_scores[key] else 0
            print(f"{key:<20} | {avg:.2f}")
        print("="*70)
        print(f"详细报告已保存至: {EXTERNAL_EVAL_DIR / 'comparison_api_evaluation.json'}")

def main():
    # 数据集文件名
    input_data_path = BASE_DIR / "generated_responses/merged_output.json"
    
    if not input_data_path.exists():
        logger.error(f"未找到输入文件: {input_data_path}")
        return

    evaluator = LegalResponseEvaluator()
    if evaluator.client:
        evaluator.process_file(str(input_data_path))

if __name__ == "__main__":
    main()