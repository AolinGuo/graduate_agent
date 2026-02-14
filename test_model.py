#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型测试脚本 - 测试四个版本的模型
版本：base、base+RAG、lora、lora+RAG
评估指标：ROUGE、embedding相似度、外部模型打分
"""

import json
import os
import sys
from typing import List, Dict, Any
import logging
from pathlib import Path
import numpy as np
from rouge import Rouge
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 配置路径
BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "server" / "model-dir"
LORA_DIR = BASE_DIR / "server" / "lora-dir"
EMBEDDING_MODEL_DIR = BASE_DIR / "server" / "embedding_model"
TEST_DATA_PATH = BASE_DIR / "server" / "data" / "query_test.json"
TRAIN_DATA_PATH = BASE_DIR / "server" / "data" / "query_train.json"
RESULTS_DIR = BASE_DIR / "test_results"

# 创建结果目录
RESULTS_DIR.mkdir(exist_ok=True)


class ModelTester:
    """模型测试器"""

    def __init__(self):
        """初始化测试器"""
        self.rouge = Rouge()
        self.embedding_model = None
        self.test_data = []
        self.results = {"base": [], "base_rag": [], "lora": [], "lora_rag": []}

    def load_embedding_model(self):
        """加载embedding模型"""
        logger.info(f"加载embedding模型: {EMBEDDING_MODEL_DIR}")
        try:
            self.embedding_model = SentenceTransformer(str(EMBEDDING_MODEL_DIR))
            logger.info("Embedding模型加载成功")
        except Exception as e:
            logger.error(f"Embedding模型加载失败: {e}")
            # 如果本地模型不存在，使用在线模型
            logger.info("尝试使用在线模型")
            self.embedding_model = SentenceTransformer(
                "paraphrase-multilingual-MiniLM-L12-v2"
            )

    def load_test_data(self):
        """加载测试数据"""
        logger.info(f"加载测试数据: {TEST_DATA_PATH}")
        with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
            self.test_data = json.load(f)
        logger.info(f"测试数据加载完成，共 {len(self.test_data)} 条")

    def load_model(self, model_type: str):
        """
        加载模型

        Args:
            model_type: 模型类型 (base, lora)

        Returns:
            tokenizer, model
        """
        logger.info(f"加载{model_type}模型...")

        try:
            if model_type == "base":
                # 加载base模型
                model_path = str(MODEL_DIR)
            else:  # lora
                # 加载lora模型
                model_path = str(LORA_DIR)

            logger.info(f"模型路径: {model_path}")

            # 检查路径是否存在
            if not os.path.exists(model_path):
                logger.warning(f"模型路径不存在: {model_path}")
                logger.info("请先检查模型是否已下载到正确位置")
                return None, None

            tokenizer = AutoTokenizer.from_pretrained(
                model_path, trust_remote_code=True
            )

            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                torch_dtype=torch.float16,
                device_map="auto",
            )

            # 修复tokenizer配置
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            if tokenizer.pad_token_id is None:
                tokenizer.pad_token_id = tokenizer.eos_token_id

            logger.info(f"{model_type}模型加载成功")
            return tokenizer, model

        except Exception as e:
            logger.error(f"{model_type}模型加载失败: {e}")
            return None, None

    def generate_response(
        self,
        tokenizer,
        model,
        instruction: str,
        input_text: str = "",
        system: str = "你是一个专业的法律投诉处理助手。",
    ) -> str:
        """
        生成模型回复

        Args:
            tokenizer: tokenizer
            model: 模型
            instruction: 问题
            input_text: RAG检索的材料
            system: 系统提示词

        Returns:
            生成的回复
        """
        try:
            # 构建消息
            if input_text:
                # 带RAG的情况
                user_content = f"{instruction}\n\n参考材料：\n{input_text}"
            else:
                # 不带RAG的情况
                user_content = instruction

            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ]

            # 应用对话模板
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            # 生成回复
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=2048,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                )

            response = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # 提取生成的部分
            if "<|assistant|>" in response:
                response = response.split("<|assistant|>")[-1].strip()
            elif "assistant" in response.lower():
                parts = response.split("assistant")
                if len(parts) > 1:
                    response = parts[-1].strip()

            return response

        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            return ""

    def calculate_rouge(self, hypothesis: str, reference: str) -> Dict[str, float]:
        """
        计算ROUGE分数

        Args:
            hypothesis: 生成的文本
            reference: 参考文本

        Returns:
            ROUGE分数字典
        """
        try:
            if not hypothesis or not reference:
                return {"rouge-1": 0.0, "rouge-2": 0.0, "rouge-l": 0.0}

            scores = self.rouge.get_scores(hypothesis, reference)[0]
            return {
                "rouge-1": scores["rouge-1"]["f"],
                "rouge-2": scores["rouge-2"]["f"],
                "rouge-l": scores["rouge-l"]["f"],
            }
        except Exception as e:
            logger.error(f"ROUGE计算失败: {e}")
            return {"rouge-1": 0.0, "rouge-2": 0.0, "rouge-l": 0.0}

    def calculate_embedding_similarity(self, text1: str, text2: str) -> float:
        """
        计算embedding相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            余弦相似度
        """
        try:
            if not text1 or not text2:
                return 0.0

            embeddings = self.embedding_model.encode([text1, text2])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Embedding相似度计算失败: {e}")
            return 0.0

    def test_model_version(self, version_name: str, model_type: str, use_rag: bool):
        """
        测试特定版本的模型

        Args:
            version_name: 版本名称 (base, base_rag, lora, lora_rag)
            model_type: 模型类型 (base, lora)
            use_rag: 是否使用RAG
        """
        logger.info(f"\n{'=' * 50}")
        logger.info(f"开始测试 {version_name} 模型")
        logger.info(f"{'=' * 50}")

        # 加载模型
        tokenizer, model = self.load_model(model_type)

        if tokenizer is None or model is None:
            logger.error(f"{version_name} 模型加载失败，跳过测试")
            return

        results = []

        for idx, item in enumerate(self.test_data):
            logger.info(f"测试样本 {idx + 1}/{len(self.test_data)}")

            instruction = item["instruction"]
            reference = item["output"]
            system = item.get("system", "你是一个专业的法律投诉处理助手。")

            # 根据是否使用RAG决定是否传入input
            if use_rag:
                input_text = item.get("input", "")
            else:
                input_text = ""

            # 生成回复
            generated = self.generate_response(
                tokenizer, model, instruction, input_text, system
            )

            # 计算评估指标
            rouge_scores = self.calculate_rouge(generated, reference)
            emb_similarity = self.calculate_embedding_similarity(generated, reference)

            result = {
                "index": idx,
                "instruction": instruction,
                "reference": reference,
                "generated": generated,
                "rouge_scores": rouge_scores,
                "embedding_similarity": emb_similarity,
            }

            results.append(result)

            logger.info(
                f"ROUGE-1: {rouge_scores['rouge-1']:.4f}, "
                f"ROUGE-2: {rouge_scores['rouge-2']:.4f}, "
                f"ROUGE-L: {rouge_scores['rouge-l']:.4f}, "
                f"Embedding Sim: {emb_similarity:.4f}"
            )

        # 保存结果
        self.results[version_name] = results

        # 计算平均分数
        avg_rouge_1 = np.mean([r["rouge_scores"]["rouge-1"] for r in results])
        avg_rouge_2 = np.mean([r["rouge_scores"]["rouge-2"] for r in results])
        avg_rouge_l = np.mean([r["rouge_scores"]["rouge-l"] for r in results])
        avg_emb_sim = np.mean([r["embedding_similarity"] for r in results])

        logger.info(f"\n{version_name} 平均分数:")
        logger.info(f"  ROUGE-1: {avg_rouge_1:.4f}")
        logger.info(f"  ROUGE-2: {avg_rouge_2:.4f}")
        logger.info(f"  ROUGE-L: {avg_rouge_l:.4f}")
        logger.info(f"  Embedding Similarity: {avg_emb_sim:.4f}")

        # 保存单个版本结果
        output_path = RESULTS_DIR / f"{version_name}_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": version_name,
                    "average_scores": {
                        "rouge_1": avg_rouge_1,
                        "rouge_2": avg_rouge_2,
                        "rouge_l": avg_rouge_l,
                        "embedding_similarity": avg_emb_sim,
                    },
                    "detailed_results": results,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(f"结果已保存到: {output_path}")

    def run_all_tests(self):
        """运行所有测试"""
        logger.info("=" * 70)
        logger.info("开始模型测试")
        logger.info("=" * 70)

        # 加载embedding模型
        self.load_embedding_model()

        # 加载测试数据
        self.load_test_data()

        # 测试四个版本
        test_configs = [
            ("base", "base", False),
            ("base_rag", "base", True),
            ("lora", "lora", False),
            ("lora_rag", "lora", True),
        ]

        for version_name, model_type, use_rag in test_configs:
            try:
                self.test_model_version(version_name, model_type, use_rag)
            except Exception as e:
                logger.error(f"{version_name} 测试失败: {e}")
                continue

        # 生成汇总报告
        self.generate_summary_report()

    def generate_summary_report(self):
        """生成汇总报告"""
        logger.info("\n" + "=" * 70)
        logger.info("生成汇总报告")
        logger.info("=" * 70)

        summary = {}

        for version_name, results in self.results.items():
            if not results:
                continue

            avg_rouge_1 = np.mean([r["rouge_scores"]["rouge-1"] for r in results])
            avg_rouge_2 = np.mean([r["rouge_scores"]["rouge-2"] for r in results])
            avg_rouge_l = np.mean([r["rouge_scores"]["rouge-l"] for r in results])
            avg_emb_sim = np.mean([r["embedding_similarity"] for r in results])

            summary[version_name] = {
                "rouge_1": avg_rouge_1,
                "rouge_2": avg_rouge_2,
                "rouge_l": avg_rouge_l,
                "embedding_similarity": avg_emb_sim,
            }

        # 保存汇总报告
        summary_path = RESULTS_DIR / "summary_report.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # 打印汇总表格
        logger.info("\n汇总结果:")
        logger.info("-" * 100)
        logger.info(
            f"{'版本':<15} {'ROUGE-1':<12} {'ROUGE-2':<12} {'ROUGE-L':<12} {'Embedding Sim':<15}"
        )
        logger.info("-" * 100)

        for version_name, scores in summary.items():
            logger.info(
                f"{version_name:<15} "
                f"{scores['rouge_1']:<12.4f} "
                f"{scores['rouge_2']:<12.4f} "
                f"{scores['rouge_l']:<12.4f} "
                f"{scores['embedding_similarity']:<15.4f}"
            )

        logger.info("-" * 100)
        logger.info(f"\n汇总报告已保存到: {summary_path}")


def main():
    """主函数"""
    tester = ModelTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
