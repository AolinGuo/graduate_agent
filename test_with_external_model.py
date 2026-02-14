#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用外部模型进行打分评估
利用GPT或其他大模型对生成的回复进行质量评分
"""

import json
import os
import sys
from typing import List, Dict, Any
import logging
from pathlib import Path
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 配置路径
BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "test_results"


class ExternalModelEvaluator:
    """使用外部模型评估"""

    def __init__(self, api_key: str = None, model_name: str = "gpt-3.5-turbo"):
        """
        初始化评估器

        Args:
            api_key: API密钥
            model_name: 模型名称
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        self.client = None

        if self.api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"外部模型评估器初始化成功，使用模型: {model_name}")
            except ImportError:
                logger.warning("未安装openai库，请运行: pip install openai")
            except Exception as e:
                logger.error(f"外部模型评估器初始化失败: {e}")
        else:
            logger.warning("未提供API密钥，外部模型评估将被跳过")

    def evaluate_response(
        self, instruction: str, reference: str, generated: str
    ) -> Dict[str, Any]:
        """
        评估生成的回复

        Args:
            instruction: 原始问题
            reference: 参考答案
            generated: 生成的答案

        Returns:
            评估结果，包含分数和评语
        """
        if not self.client:
            return {"score": 0.0, "reasoning": "外部模型评估器未初始化"}

        try:
            # 构建评估提示词
            prompt = f"""请作为一个专业的法律投诉处理专家，评估以下AI生成的回复质量。

用户问题：
{instruction}

标准答案：
{reference}

AI生成的回复：
{generated}

请从以下几个维度评估AI生成的回复（每个维度0-10分）：
1. 准确性：回复是否准确解答了用户问题
2. 完整性：回复是否涵盖了所有必要信息
3. 专业性：回复是否使用了恰当的法律术语和专业表述
4. 态度：回复是否礼貌、专业、有同理心
5. 法律依据：回复是否正确引用了相关法律条文

请按照以下JSON格式返回评估结果：
{{
    "accuracy": <分数>,
    "completeness": <分数>,
    "professionalism": <分数>,
    "attitude": <分数>,
    "legal_basis": <分数>,
    "overall_score": <总分（0-100）>,
    "reasoning": "<详细评语>"
}}
"""

            # 调用API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的法律文本评估专家。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            # 解析响应
            content = response.choices[0].message.content

            # 尝试解析JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # 如果不是JSON格式，手动解析
                result = {"overall_score": 0.0, "reasoning": content}

            return result

        except Exception as e:
            logger.error(f"外部模型评估失败: {e}")
            return {"score": 0.0, "reasoning": f"评估失败: {str(e)}"}

    def evaluate_all_versions(self):
        """评估所有版本的结果"""
        logger.info("=" * 70)
        logger.info("使用外部模型评估所有版本")
        logger.info("=" * 70)

        versions = ["base", "base_rag", "lora", "lora_rag"]
        all_evaluations = {}

        for version in versions:
            results_file = RESULTS_DIR / f"{version}_results.json"

            if not results_file.exists():
                logger.warning(f"{version} 结果文件不存在，跳过")
                continue

            logger.info(f"\n评估 {version} 版本...")

            # 加载结果
            with open(results_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            evaluations = []

            for idx, item in enumerate(data["detailed_results"]):
                logger.info(f"评估样本 {idx + 1}/{len(data['detailed_results'])}")

                evaluation = self.evaluate_response(
                    item["instruction"], item["reference"], item["generated"]
                )

                evaluations.append(
                    {
                        "index": idx,
                        "instruction": item["instruction"],
                        "evaluation": evaluation,
                    }
                )

                if "overall_score" in evaluation:
                    logger.info(f"  总分: {evaluation['overall_score']:.2f}")

            all_evaluations[version] = evaluations

            # 计算平均分
            if evaluations and "overall_score" in evaluations[0]["evaluation"]:
                avg_score = np.mean(
                    [e["evaluation"]["overall_score"] for e in evaluations]
                )
                logger.info(f"\n{version} 平均分: {avg_score:.2f}")

            # 保存评估结果
            eval_output_path = RESULTS_DIR / f"{version}_external_evaluation.json"
            with open(eval_output_path, "w", encoding="utf-8") as f:
                json.dump(evaluations, f, ensure_ascii=False, indent=2)

            logger.info(f"评估结果已保存到: {eval_output_path}")

        # 生成汇总报告
        self.generate_evaluation_summary(all_evaluations)

    def generate_evaluation_summary(self, all_evaluations: Dict):
        """生成评估汇总报告"""
        logger.info("\n" + "=" * 70)
        logger.info("生成外部模型评估汇总报告")
        logger.info("=" * 70)

        summary = {}

        for version, evaluations in all_evaluations.items():
            if not evaluations:
                continue

            # 提取所有分数
            overall_scores = []
            dimension_scores = {
                "accuracy": [],
                "completeness": [],
                "professionalism": [],
                "attitude": [],
                "legal_basis": [],
            }

            for eval_item in evaluations:
                evaluation = eval_item["evaluation"]

                if "overall_score" in evaluation:
                    overall_scores.append(evaluation["overall_score"])

                for dim in dimension_scores:
                    if dim in evaluation:
                        dimension_scores[dim].append(evaluation[dim])

            # 计算平均分
            summary[version] = {
                "overall_score": np.mean(overall_scores) if overall_scores else 0.0,
                "dimension_scores": {
                    dim: np.mean(scores) if scores else 0.0
                    for dim, scores in dimension_scores.items()
                },
            }

        # 保存汇总报告
        summary_path = RESULTS_DIR / "external_evaluation_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # 打印汇总表格
        logger.info("\n外部模型评估汇总:")
        logger.info("-" * 100)
        logger.info(
            f"{'版本':<15} {'总分':<12} {'准确性':<12} {'完整性':<12} {'专业性':<12} {'态度':<12} {'法律依据':<12}"
        )
        logger.info("-" * 100)

        for version, scores in summary.items():
            dim_scores = scores["dimension_scores"]
            logger.info(
                f"{version:<15} "
                f"{scores['overall_score']:<12.2f} "
                f"{dim_scores.get('accuracy', 0):<12.2f} "
                f"{dim_scores.get('completeness', 0):<12.2f} "
                f"{dim_scores.get('professionalism', 0):<12.2f} "
                f"{dim_scores.get('attitude', 0):<12.2f} "
                f"{dim_scores.get('legal_basis', 0):<12.2f}"
            )

        logger.info("-" * 100)
        logger.info(f"\n汇总报告已保存到: {summary_path}")


def main():
    """主函数"""
    # 从环境变量或命令行参数获取API密钥
    api_key = os.getenv("OPENAI_API_KEY")

    if len(sys.argv) > 1:
        api_key = sys.argv[1]

    if not api_key:
        logger.warning("未提供OpenAI API密钥")
        logger.info("使用方法:")
        logger.info("  1. 设置环境变量: export OPENAI_API_KEY=your_api_key")
        logger.info(
            "  2. 或通过命令行参数: python test_with_external_model.py your_api_key"
        )
        logger.info("\n如果使用其他API（如国内的大模型），请修改代码中的API调用部分")
        return

    evaluator = ExternalModelEvaluator(api_key=api_key)
    evaluator.evaluate_all_versions()


if __name__ == "__main__":
    main()
