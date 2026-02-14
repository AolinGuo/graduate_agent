#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤3（可选）: 使用外部API评估生成的回复
参考 new_train.py，使用 DeepSeek API 进行质量评分
"""

import json
import os
import sys
import time
from typing import Dict, Any
import logging
from pathlib import Path
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 配置路径
BASE_DIR = Path(__file__).parent
EVALUATION_DIR = BASE_DIR / "evaluation_results"
EXTERNAL_EVAL_DIR = BASE_DIR / "external_evaluation"

# 创建输出目录
EXTERNAL_EVAL_DIR.mkdir(exist_ok=True)

# ================= API 配置区域 =================
# 参考 new_train.py 的配置
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"


class ExternalAPIEvaluator:
    """使用外部API评估生成的回复"""

    def __init__(self):
        """初始化评估器"""
        self.client = None
        self.init_api_client()

    def init_api_client(self):
        """初始化API客户端"""
        logger.info("=" * 60)
        logger.info("初始化外部API客户端")
        logger.info("=" * 60)

        if not API_KEY:
            logger.error("未找到 DEEPSEEK_API_KEY 环境变量")
            logger.info("请设置环境变量或在 .env 文件中配置:")
            logger.info("  DEEPSEEK_API_KEY=your_api_key")
            return False

        try:
            self.client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
            logger.info(f"✓ API客户端初始化成功")
            logger.info(f"  API地址: {BASE_URL}")
            logger.info(f"  模型: {MODEL_NAME}")
            return True
        except Exception as e:
            logger.error(f"API客户端初始化失败: {e}")
            return False

    def call_llm(self, messages: list, retries: int = 3) -> str:
        """
        通用 LLM 调用函数，带重试机制
        参考 new_train.py 的实现

        Args:
            messages: 消息列表
            retries: 重试次数

        Returns:
            API响应内容
        """
        for i in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    stream=False,
                    temperature=0.3,  # 保持一定的确定性
                    response_format={"type": "json_object"},  # 强制返回JSON格式
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"API调用失败 (尝试 {i + 1}/{retries}): {e}")
                if i < retries - 1:
                    time.sleep(2)  # 等待2秒后重试

        logger.error(f"API调用失败，已重试{retries}次")
        return None

    def evaluate_single_response(
        self, instruction: str, reference: str, generated: str
    ) -> Dict[str, Any]:
        """
        评估单个生成的回复

        Args:
            instruction: 原始问题
            reference: 参考答案
            generated: 生成的答案

        Returns:
            评估结果，包含各维度分数和总分
        """
        if not self.client:
            return {
                "overall_score": 0.0,
                "accuracy": 0.0,
                "completeness": 0.0,
                "professionalism": 0.0,
                "attitude": 0.0,
                "legal_basis": 0.0,
                "reasoning": "API客户端未初始化",
            }

        # 构建评估提示词
        prompt = f"""请作为一个专业的法律投诉处理专家，评估以下AI生成的回复质量。

【用户投诉】:
{instruction}

【标准回复（参考）】:
{reference}

【AI生成的回复】:
{generated}

请从以下5个维度评估AI生成的回复（每个维度0-10分）：

1. **准确性** (accuracy): 回复是否准确解答了用户的投诉问题，是否正确理解了用户诉求
2. **完整性** (completeness): 回复是否涵盖了所有必要信息，是否遗漏重要内容
3. **专业性** (professionalism): 回复是否使用了恰当的法律术语和专业表述
4. **态度** (attitude): 回复是否礼貌、专业、有同理心，是否适合政府部门回复
5. **法律依据** (legal_basis): 回复是否正确引用了相关法律条文，法律依据是否充分

请严格按照以下JSON格式返回评估结果（不要输出其他内容）：
{{
    "accuracy": <0-10的分数>,
    "completeness": <0-10的分数>,
    "professionalism": <0-10的分数>,
    "attitude": <0-10的分数>,
    "legal_basis": <0-10的分数>,
    "overall_score": <总分，0-100，为5个维度的加权平均>,
    "reasoning": "<100字以内的简要评语，说明优点和不足>"
}}
"""

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的法律文本评估专家，擅长评估政府热线回复质量。请严格按照要求以JSON格式输出评估结果。",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            # 调用API
            result = self.call_llm(messages)

            if not result:
                return {
                    "overall_score": 0.0,
                    "accuracy": 0.0,
                    "completeness": 0.0,
                    "professionalism": 0.0,
                    "attitude": 0.0,
                    "legal_basis": 0.0,
                    "reasoning": "API调用失败",
                }

            # 解析JSON响应
            evaluation = json.loads(result)

            # 确保所有字段都存在
            required_fields = [
                "accuracy",
                "completeness",
                "professionalism",
                "attitude",
                "legal_basis",
                "overall_score",
                "reasoning",
            ]

            for field in required_fields:
                if field not in evaluation:
                    evaluation[field] = 0.0 if field != "reasoning" else "缺失字段"

            return evaluation

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.debug(f"原始响应: {result}")
            return {
                "overall_score": 0.0,
                "accuracy": 0.0,
                "completeness": 0.0,
                "professionalism": 0.0,
                "attitude": 0.0,
                "legal_basis": 0.0,
                "reasoning": f"JSON解析失败: {str(e)}",
            }
        except Exception as e:
            logger.error(f"评估失败: {e}")
            return {
                "overall_score": 0.0,
                "accuracy": 0.0,
                "completeness": 0.0,
                "professionalism": 0.0,
                "attitude": 0.0,
                "legal_basis": 0.0,
                "reasoning": f"评估失败: {str(e)}",
            }

    def evaluate_version(self, version_name: str) -> Dict:
        """
        评估特定版本的所有回复

        Args:
            version_name: 版本名称

        Returns:
            评估结果
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"评估 {version_name} 版本")
        logger.info(f"{'=' * 60}")

        # 加载评估结果（包含生成的回复）
        eval_path = EVALUATION_DIR / f"{version_name}_evaluation.json"

        if not eval_path.exists():
            logger.error(f"评估文件不存在: {eval_path}")
            logger.info(f"请先运行 evaluate_responses.py")
            return None

        with open(eval_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = data["detailed_results"]
        logger.info(f"加载了 {len(results)} 条评估结果")

        # 对每条结果进行API评分
        api_evaluations = []

        for idx, item in enumerate(results, 1):
            logger.info(f"API评分 {idx}/{len(results)}", end="", flush=True)

            instruction = item["instruction"]
            reference = item["reference"]
            generated = item["generated"]

            # 调用API评估
            api_eval = self.evaluate_single_response(instruction, reference, generated)

            api_evaluations.append(
                {
                    "index": item["index"],
                    "instruction": instruction,
                    "reference": reference,
                    "generated": generated,
                    "api_evaluation": api_eval,
                    "automatic_metrics": item.get("metrics", {}),
                }
            )

            logger.info(
                f" - 总分: {api_eval['overall_score']:.1f}, "
                f"准确性: {api_eval['accuracy']:.1f}, "
                f"完整性: {api_eval['completeness']:.1f}"
            )

        # 计算平均分
        avg_scores = {
            "overall_score": np.mean(
                [e["api_evaluation"]["overall_score"] for e in api_evaluations]
            ),
            "accuracy": np.mean(
                [e["api_evaluation"]["accuracy"] for e in api_evaluations]
            ),
            "completeness": np.mean(
                [e["api_evaluation"]["completeness"] for e in api_evaluations]
            ),
            "professionalism": np.mean(
                [e["api_evaluation"]["professionalism"] for e in api_evaluations]
            ),
            "attitude": np.mean(
                [e["api_evaluation"]["attitude"] for e in api_evaluations]
            ),
            "legal_basis": np.mean(
                [e["api_evaluation"]["legal_basis"] for e in api_evaluations]
            ),
        }

        logger.info(f"\n{version_name} API评估平均分:")
        logger.info(f"  总分: {avg_scores['overall_score']:.2f}")
        logger.info(f"  准确性: {avg_scores['accuracy']:.2f}")
        logger.info(f"  完整性: {avg_scores['completeness']:.2f}")
        logger.info(f"  专业性: {avg_scores['professionalism']:.2f}")
        logger.info(f"  态度: {avg_scores['attitude']:.2f}")
        logger.info(f"  法律依据: {avg_scores['legal_basis']:.2f}")

        # 构建评估结果
        evaluation = {
            "version": version_name,
            "model_type": data.get("model_type"),
            "use_rag": data.get("use_rag"),
            "evaluated_at": __import__("datetime").datetime.now().isoformat(),
            "api_config": {"base_url": BASE_URL, "model": MODEL_NAME},
            "average_scores": avg_scores,
            "detailed_evaluations": api_evaluations,
        }

        # 保存评估结果
        output_path = EXTERNAL_EVAL_DIR / f"{version_name}_api_evaluation.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(evaluation, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ API评估完成，结果已保存到: {output_path}")

        return evaluation

    def evaluate_all_versions(self):
        """评估所有版本"""
        logger.info("=" * 70)
        logger.info("使用外部API评估所有版本")
        logger.info("=" * 70)

        if not self.client:
            logger.error("API客户端初始化失败，无法继续")
            return

        # 检查评估目录
        if not EVALUATION_DIR.exists() or not any(EVALUATION_DIR.iterdir()):
            logger.error(f"评估目录为空: {EVALUATION_DIR}")
            logger.info("请先运行 evaluate_responses.py")
            return

        # 评估所有版本
        versions = ["base", "base_rag", "lora", "lora_rag"]
        all_evaluations = {}

        for version in versions:
            try:
                evaluation = self.evaluate_version(version)
                if evaluation:
                    all_evaluations[version] = evaluation["average_scores"]
            except KeyboardInterrupt:
                logger.warning("\n用户中断评估")
                logger.info(f"已完成 {len(all_evaluations)} 个版本的评估")
                break
            except Exception as e:
                logger.error(f"{version} 评估失败: {e}")
                import traceback

                logger.error(traceback.format_exc())
                continue

        # 生成汇总报告
        if all_evaluations:
            self.generate_summary_report(all_evaluations)

    def generate_summary_report(self, all_evaluations: Dict):
        """生成汇总报告"""
        logger.info(f"\n{'=' * 70}")
        logger.info("生成API评估汇总报告")
        logger.info(f"{'=' * 70}")

        # 保存汇总报告
        summary_path = EXTERNAL_EVAL_DIR / "api_evaluation_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "evaluated_at": __import__("datetime").datetime.now().isoformat(),
                    "api_config": {"base_url": BASE_URL, "model": MODEL_NAME},
                    "versions": all_evaluations,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        # 打印汇总表格
        logger.info("\nAPI评估汇总:")
        logger.info("-" * 110)
        logger.info(
            f"{'版本':<15} "
            f"{'总分':<10} "
            f"{'准确性':<10} "
            f"{'完整性':<10} "
            f"{'专业性':<10} "
            f"{'态度':<10} "
            f"{'法律依据':<10}"
        )
        logger.info("-" * 110)

        for version, scores in all_evaluations.items():
            logger.info(
                f"{version:<15} "
                f"{scores['overall_score']:<10.2f} "
                f"{scores['accuracy']:<10.2f} "
                f"{scores['completeness']:<10.2f} "
                f"{scores['professionalism']:<10.2f} "
                f"{scores['attitude']:<10.2f} "
                f"{scores['legal_basis']:<10.2f}"
            )

        logger.info("-" * 110)
        logger.info(f"\n✓ 汇总报告已保存到: {summary_path}")

        # 找出最佳版本
        best_version = max(all_evaluations.items(), key=lambda x: x[1]["overall_score"])

        logger.info(
            f"\n🏆 API评分最佳版本: {best_version[0]} (总分: {best_version[1]['overall_score']:.2f})"
        )


def main():
    """主函数"""
    evaluator = ExternalAPIEvaluator()

    if not evaluator.client:
        logger.error("\n请设置 DEEPSEEK_API_KEY 环境变量")
        logger.info("\n方法1: 在项目根目录创建 .env 文件，添加:")
        logger.info("  DEEPSEEK_API_KEY=your_api_key")
        logger.info("\n方法2: 在命令行中设置环境变量:")
        logger.info("  Windows: set DEEPSEEK_API_KEY=your_api_key")
        logger.info("  Linux/Mac: export DEEPSEEK_API_KEY=your_api_key")
        return

    evaluator.evaluate_all_versions()


if __name__ == "__main__":
    main()
