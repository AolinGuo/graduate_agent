#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤2: 评估生成的回复
读取生成的回复并进行评估
评估指标：ROUGE、embedding相似度
"""

import json
from typing import Dict
import logging
from pathlib import Path
import numpy as np
from rouge import Rouge
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 配置路径
BASE_DIR = Path(__file__).parent
EMBEDDING_MODEL_DIR = BASE_DIR / "server" / "embedding_model"
GENERATED_DIR = BASE_DIR / "generated_responses"
EVALUATION_DIR = BASE_DIR / "evaluation_results"

# 创建输出目录
EVALUATION_DIR.mkdir(exist_ok=True)


class ResponseEvaluator:
    """回复评估器"""

    def __init__(self):
        """初始化评估器"""
        self.rouge = Rouge()
        self.embedding_model = None

    def load_embedding_model(self):
        """加载embedding模型"""
        logger.info("=" * 60)
        logger.info("加载Embedding模型")
        logger.info("=" * 60)

        try:
            # 先尝试加载本地模型
            if EMBEDDING_MODEL_DIR.exists():
                logger.info(f"从本地加载: {EMBEDDING_MODEL_DIR}")
                self.embedding_model = SentenceTransformer(str(EMBEDDING_MODEL_DIR))
                logger.info("✓ 本地Embedding模型加载成功")
            else:
                # 使用在线模型
                logger.info("本地模型不存在，使用在线模型")
                logger.info("模型: paraphrase-multilingual-MiniLM-L12-v2")
                self.embedding_model = SentenceTransformer(
                    "paraphrase-multilingual-MiniLM-L12-v2"
                )
                logger.info("✓ 在线Embedding模型加载成功")

            return True

        except Exception as e:
            logger.error(f"Embedding模型加载失败: {e}")
            logger.error("评估将跳过embedding相似度计算")
            return False

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
            # 检查输入
            if not hypothesis or not reference:
                logger.warning("生成文本或参考文本为空")
                return {"rouge-1": 0.0, "rouge-2": 0.0, "rouge-l": 0.0}

            # 确保文本不为空且有实际内容
            hypothesis = hypothesis.strip()
            reference = reference.strip()

            if not hypothesis or not reference:
                return {"rouge-1": 0.0, "rouge-2": 0.0, "rouge-l": 0.0}

            # 计算ROUGE分数
            scores = self.rouge.get_scores(hypothesis, reference)[0]

            return {
                "rouge-1": scores["rouge-1"]["f"],
                "rouge-2": scores["rouge-2"]["f"],
                "rouge-l": scores["rouge-l"]["f"],
            }

        except Exception as e:
            logger.error(f"ROUGE计算失败: {e}")
            logger.debug(f"生成文本: {hypothesis[:100]}...")
            logger.debug(f"参考文本: {reference[:100]}...")
            return {"rouge-1": 0.0, "rouge-2": 0.0, "rouge-l": 0.0}

    def calculate_embedding_similarity(self, text1: str, text2: str) -> float:
        """
        计算embedding相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            余弦相似度 (0-1之间)
        """
        try:
            if not self.embedding_model:
                return 0.0

            if not text1 or not text2:
                logger.warning("文本为空，无法计算embedding相似度")
                return 0.0

            # 编码文本
            embeddings = self.embedding_model.encode([text1, text2])

            # 计算余弦相似度
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

            return float(similarity)

        except Exception as e:
            logger.error(f"Embedding相似度计算失败: {e}")
            return 0.0

    def evaluate_version(self, version_name: str) -> Dict:
        """
        评估特定版本的回复

        Args:
            version_name: 版本名称

        Returns:
            评估结果
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"评估 {version_name} 版本")
        logger.info(f"{'=' * 60}")

        # 加载生成的回复
        generated_path = GENERATED_DIR / f"{version_name}_generated.json"

        if not generated_path.exists():
            logger.error(f"生成文件不存在: {generated_path}")
            logger.info("请先运行 generate_responses.py 生成回复")
            return None

        with open(generated_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = data["results"]
        logger.info(f"加载了 {len(results)} 条生成结果")

        # 评估每条结果
        evaluated_results = []

        for idx, item in enumerate(results, 1):
            logger.info(f"评估样本 {idx}/{len(results)}")

            generated = item["generated_output"]  # 修改这里
            reference = item["reference_output"]  # 修改这里

            # 计算ROUGE分数
            rouge_scores = self.calculate_rouge(generated, reference)

            # 计算embedding相似度
            emb_similarity = self.calculate_embedding_similarity(generated, reference)

            evaluated_results.append(
                {
                    **item,  # 保留原有信息
                    "metrics": {
                        "rouge": rouge_scores,
                        "embedding_similarity": emb_similarity,
                    },
                }
            )

            logger.info(
                f"  ROUGE-1: {rouge_scores['rouge-1']:.4f}, "
                f"ROUGE-2: {rouge_scores['rouge-2']:.4f}, "
                f"ROUGE-L: {rouge_scores['rouge-l']:.4f}, "
                f"Emb Sim: {emb_similarity:.4f}"
            )

        # 计算平均分数
        avg_rouge_1 = np.mean(
            [r["metrics"]["rouge"]["rouge-1"] for r in evaluated_results]
        )
        avg_rouge_2 = np.mean(
            [r["metrics"]["rouge"]["rouge-2"] for r in evaluated_results]
        )
        avg_rouge_l = np.mean(
            [r["metrics"]["rouge"]["rouge-l"] for r in evaluated_results]
        )
        avg_emb_sim = np.mean(
            [r["metrics"]["embedding_similarity"] for r in evaluated_results]
        )

        logger.info(f"\n{version_name} 平均分数:")
        logger.info(f"  ROUGE-1: {avg_rouge_1:.4f}")
        logger.info(f"  ROUGE-2: {avg_rouge_2:.4f}")
        logger.info(f"  ROUGE-L: {avg_rouge_l:.4f}")
        logger.info(f"  Embedding Similarity: {avg_emb_sim:.4f}")

        # 构建评估结果
        evaluation = {
            "version": version_name,
            "model_type": data.get("model_type"),
            "use_rag": data.get("use_rag"),
            "generated_at": data.get("generated_at"),
            "evaluated_at": __import__("datetime").datetime.now().isoformat(),
            "average_metrics": {
                "rouge_1": avg_rouge_1,
                "rouge_2": avg_rouge_2,
                "rouge_l": avg_rouge_l,
                "embedding_similarity": avg_emb_sim,
            },
            "detailed_results": evaluated_results,
        }

        # 保存评估结果
        output_path = EVALUATION_DIR / f"{version_name}_evaluation.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(evaluation, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 评估完成，结果已保存到: {output_path}")

        return evaluation

    def evaluate_all_versions(self):
        """评估所有版本"""
        logger.info("=" * 70)
        logger.info("开始评估所有版本")
        logger.info("=" * 70)

        # 加载embedding模型
        self.load_embedding_model()

        # 检查生成目录
        if not GENERATED_DIR.exists() or not any(GENERATED_DIR.iterdir()):
            logger.error(f"生成目录为空: {GENERATED_DIR}")
            logger.info("请先运行 generate_responses.py 生成回复")
            return

        # 评估所有版本
        versions = ["base", "base_rag", "lora", "lora_rag"]
        evaluations = {}

        for version in versions:
            try:
                evaluation = self.evaluate_version(version)
                if evaluation:
                    evaluations[version] = evaluation["average_metrics"]
            except Exception as e:
                logger.error(f"{version} 评估失败: {e}")
                import traceback

                logger.error(traceback.format_exc())
                continue

        # 生成汇总报告
        if evaluations:
            self.generate_summary_report(evaluations)

    def generate_summary_report(self, evaluations: Dict):
        """生成汇总报告"""
        logger.info(f"\n{'=' * 70}")
        logger.info("生成评估汇总报告")
        logger.info(f"{'=' * 70}")

        # 保存汇总报告
        summary_path = EVALUATION_DIR / "summary_report.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "evaluated_at": __import__("datetime").datetime.now().isoformat(),
                    "versions": evaluations,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        # 打印汇总表格
        logger.info("\n评估汇总:")
        logger.info("-" * 100)
        logger.info(
            f"{'版本':<15} "
            f"{'ROUGE-1':<12} "
            f"{'ROUGE-2':<12} "
            f"{'ROUGE-L':<12} "
            f"{'Embedding Sim':<15}"
        )
        logger.info("-" * 100)

        for version, metrics in evaluations.items():
            logger.info(
                f"{version:<15} "
                f"{metrics['rouge_1']:<12.4f} "
                f"{metrics['rouge_2']:<12.4f} "
                f"{metrics['rouge_l']:<12.4f} "
                f"{metrics['embedding_similarity']:<15.4f}"
            )

        logger.info("-" * 100)
        logger.info(f"\n✓ 汇总报告已保存到: {summary_path}")

        # 找出最佳版本
        best_version = max(
            evaluations.items(),
            key=lambda x: (
                x[1]["rouge_1"]
                + x[1]["rouge_2"]
                + x[1]["rouge_l"]
                + x[1]["embedding_similarity"]
            )
            / 4,
        )

        logger.info(f"\n🏆 综合表现最佳版本: {best_version[0]}")


def main():
    """主函数"""
    evaluator = ResponseEvaluator()
    evaluator.evaluate_all_versions()


if __name__ == "__main__":
    main()
