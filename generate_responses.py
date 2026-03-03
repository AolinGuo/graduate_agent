# 生成回复
import json
import os
import sys
from typing import List, Dict, Any
import logging
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 配置路径
BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "server" / "model-dir"
LORA_DIR = BASE_DIR / "server" / "lora-dir"
TEST_DATA_PATH = BASE_DIR / "server" / "data" / "query_test.json"
GENERATED_DIR = BASE_DIR / "generated_responses"

# 创建输出目录
GENERATED_DIR.mkdir(exist_ok=True)


class ResponseGenerator:
    """模型回复生成器"""

    def __init__(self):
        """初始化生成器"""
        self.test_data = []
        self.current_model = None
        self.current_tokenizer = None

    def load_test_data(self):
        """加载测试数据"""
        if not TEST_DATA_PATH.exists():
            logger.error(f"测试数据文件不存在: {TEST_DATA_PATH}")
            return False
        with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
            self.test_data = json.load(f)
        logger.info(f"测试数据加载完成，共 {len(self.test_data)} 条")
        return True

    def load_model(self, model_type: str):
        """
        加载模型

        Args:
            model_type: 模型类型 (base 或 lora)

        Returns:
            是否加载成功
        """
        logger.info(f"加载 {model_type} 模型")

        try:
            # 先清理之前的模型
            if self.current_model is not None:
                del self.current_model
                del self.current_tokenizer
                torch.cuda.empty_cache()

            # 确定模型路径
            if model_type == "base":
                model_path = str(MODEL_DIR)
            elif model_type == "lora":
                model_path = str(LORA_DIR)
            else:
                logger.error(f"未知的模型类型: {model_type}")
                return False

            logger.info(f"模型路径: {model_path}")

            # 检查路径是否存在
            if not os.path.exists(model_path):
                logger.error(f"模型路径不存在: {model_path}")
                logger.info(f"请确保模型已下载到正确位置")
                logger.info(f"  Base模型应在: {MODEL_DIR}")
                logger.info(f"  LoRA模型应在: {LORA_DIR}")
                return False

            # 加载tokenizer
            logger.info("加载tokenizer...")
            self.current_tokenizer = AutoTokenizer.from_pretrained(
                model_path, trust_remote_code=True
            )

            # 修复tokenizer配置
            if self.current_tokenizer.pad_token is None:
                self.current_tokenizer.pad_token = self.current_tokenizer.eos_token
            if self.current_tokenizer.pad_token_id is None:
                self.current_tokenizer.pad_token_id = (
                    self.current_tokenizer.eos_token_id
                )

            # 加载模型
            logger.info("加载模型...")
            self.current_model = AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                torch_dtype=torch.float16,  # 使用半精度节省显存
                device_map="auto",  # 自动分配设备
            )

            logger.info(f"{model_type} 模型加载成功！")
            logger.info(f"模型设备: {self.current_model.device}")

            return True

        except Exception as e:
            logger.error(f"{model_type} 模型加载失败: {e}")
            logger.error("请检查:")
            logger.error("  1. 模型文件是否存在")
            logger.error("  2. 是否有足够的GPU显存")
            logger.error("  3. transformers库版本是否正确")
            return False

    def generate_single_response(
        self,
        instruction: str,
        input_text: str = "",
        system: str = "",
        max_new_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """
        生成单个回复

        Args:
            instruction: 用户问题
            input_text: RAG检索的参考材料（可选）
            system: 系统提示词
            max_new_tokens: 最大生成token数
            temperature: 温度参数
            top_p: top_p采样参数

        Returns:
            生成的回复
        """
        try:
            # 构造用户侧的内容
            if input_text:
                # 针对法律场景，明确区分投诉内容和法律条文
                user_content = f"【投诉内容】：\n{instruction}\n\n【参考法律条文】：\n{input_text}"
            else:
                user_content = f"【投诉内容】：\n{instruction}"

            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ]

            # 应用对话模板
            prompt = self.current_tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            logger.debug(f"Prompt长度: {len(prompt)} 字符")

            # 编码输入
            inputs = self.current_tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=4096,  # 限制输入长度
            ).to(self.current_model.device)

            # 生成回复
            logger.debug("开始生成...")
            with torch.no_grad():
                outputs = self.current_model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.current_tokenizer.pad_token_id,
                    eos_token_id=self.current_tokenizer.eos_token_id,
                )

            # 解码输出
            response = self.current_tokenizer.decode(
                outputs[0], skip_special_tokens=True
            )

            # 提取生成的部分（去掉prompt）
            # 通常模型输出会包含完整的对话，我们只需要assistant的回复
            if "<|assistant|>" in response:
                response = response.split("<|assistant|>")[-1].strip()
            elif "assistant" in response.lower():
                # 尝试其他可能的分隔符
                parts = response.lower().split("assistant")
                if len(parts) > 1:
                    # 找到对应的原文位置
                    idx = response.lower().rfind("assistant")
                    response = response[idx + len("assistant") :].strip()
                    # 去掉可能的冒号或换行
                    response = response.lstrip(":").strip()

            logger.debug(f"生成完成，回复长度: {len(response)} 字符")

            return response

        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return ""

    def generate_for_version(
        self, version_name: str, model_type: str, use_rag: bool
    ) -> List[Dict]:
        """
        为特定版本生成所有回复

        Args:
            version_name: 版本名称 (base, base_rag, lora, lora_rag)
            model_type: 模型类型 (base, lora)
            use_rag: 是否使用RAG

        Returns:
            生成结果列表
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"开始生成 {version_name} 版本的回复")
        logger.info(f"{'=' * 60}")
        logger.info(f"模型类型: {model_type}")
        logger.info(f"使用RAG: {'是' if use_rag else '否'}")

        # 加载模型
        if not self.load_model(model_type):
            logger.error(f"{version_name} 模型加载失败，跳过生成")
            return []

        results = []
        total = len(self.test_data)

        for idx, item in enumerate(self.test_data, 1):
            logger.info(f"\n进度: {idx}/{total}")
            
            # 1. 提取数据
            instruction = item.get("instruction", "")
            reference = item.get("output", "")  # 你的数据集中 output 是参考答案
            
            # 2. 获取 System Prompt (优先使用数据集中的，其次用类默认的)
            system_prompt = item.get("system", "你是一个专业的法律投诉处理助手。")

            # 3. 处理 RAG 逻辑
            # 根据 version 决定是否将数据集中的 input 作为上下文传入
            if use_rag:
                input_text = item.get("input", "")
            else:
                input_text = ""

            # 4. 调用生成逻辑
            generated = self.generate_single_response(
                instruction=instruction, 
                input_text=input_text, 
                system=system_prompt
            )

            # 5. 保存结果（映射回你的字段名，方便后续对比）
            result = {
                "index": idx - 1,
                "instruction": instruction,
                "reference_output": reference,
                "generated_output": generated,
                "system": system_prompt,
                "rag_input": input_text if use_rag else "N/A",
                "use_rag": use_rag,
            }
            results.append(result)

            logger.info(f"生成的回复: {generated[:100]}...")
            logger.info(f"回复长度: {len(generated)} 字符")

        # 保存生成结果
        output_path = GENERATED_DIR / f"{version_name}_generated.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": version_name,
                    "model_type": model_type,
                    "use_rag": use_rag,
                    "generated_at": datetime.now().isoformat(),
                    "total_samples": len(results),
                    "results": results,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(f"\n✓ {version_name} 版本生成完成！")
        logger.info(f"✓ 结果已保存到: {output_path}")

        return results

    def generate_all_versions(self):
        """生成所有版本的回复"""
        logger.info("=" * 70)
        logger.info("开始生成所有版本的模型回复")
        logger.info("=" * 70)

        # 加载测试数据
        if not self.load_test_data():
            logger.error("测试数据加载失败，终止生成")
            return

        # 生成配置：(版本名称, 模型类型, 是否使用RAG)
        configs = [
            ("base", "base", False),
            ("base_rag", "base", True),
            ("lora", "lora", False),
            ("lora_rag", "lora", True),
        ]

        success_count = 0

        for version_name, model_type, use_rag in configs:
            try:
                results = self.generate_for_version(version_name, model_type, use_rag)
                if results:
                    success_count += 1
            except KeyboardInterrupt:
                logger.warning("\n用户中断生成")
                logger.info(f"已完成 {success_count} 个版本的生成")
                break
            except Exception as e:
                logger.error(f"{version_name} 生成失败: {e}")
                import traceback

                logger.error(traceback.format_exc())
                continue

        logger.info(f"\n{'=' * 70}")
        logger.info(f"生成完成！")
        logger.info(f"{'=' * 70}")
        logger.info(f"成功生成: {success_count}/{len(configs)} 个版本")
        logger.info(f"结果保存在: {GENERATED_DIR}")
        logger.info(f"\n下一步: 运行 evaluate_responses.py 进行评估")


def main():
    """主函数"""
    generator = ResponseGenerator()
    generator.generate_all_versions()


if __name__ == "__main__":
    main()
