#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI服务模块 - 封装Qwen3-8B模型的加载和推理功能
用于AI报告生成和AI辅助回复
"""

import torch
import logging
from typing import Optional, Dict, Any
import os

logger = logging.getLogger()
# 导入配置

AI_CONFIG = {
    "gpu": {
        "device_id": 2,  # 使用第一个可见GPU（由CUDA_VISIBLE_DEVICES控制实际物理GPU）
        "use_single_gpu": True,
        "max_memory_per_gpu": "20GB",  # 增加到20GB
        "enable_cpu_fallback": True,
    },
    "model": {
        "torch_dtype": "bfloat16",
        "low_cpu_mem_usage": True,
        "trust_remote_code": True,
    },
    "inference": {
        "default_temperature": 0.7,
        "default_top_p": 0.8,
        "default_max_tokens": 2048,
        "report_temperature": 0.7,
        "report_max_tokens": 2048,
        "reply_temperature": 0.7,
        "reply_max_tokens": 512,
        "use_cache": True,
        "use_no_grad": True,
    },
    "logging": {
        "verbose": True,
        "show_gpu_status": True,
    },
}

# 设置CUDA设备（如果需要指定特定GPU）
gpu_config = AI_CONFIG["gpu"]
if gpu_config["use_single_gpu"]:
    # 根据nvidia-smi结果，选择显存最空闲的物理GPU
    # GPU 2 和 GPU 5 可用（RTX 4090）
    physical_gpu = "2"  # GPU 2 是RTX 4090（可改为"5"）
    os.environ["CUDA_VISIBLE_DEVICES"] = physical_gpu
    if AI_CONFIG["logging"]["verbose"]:
        logging.getLogger(__name__).info(
            f"设置使用物理GPU {physical_gpu}，在程序中显示为GPU 0"
        )

logger = logging.getLogger(__name__)


def check_gpu_status():
    """检查GPU状态和显存使用情况"""
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()

        logger.info("GPU状态检查:")
        logger.info(f"  - 可见GPU数量: {gpu_count}")

        # 检查所有可见GPU的显存使用情况
        best_gpu = 0
        max_free_memory = 0

        for i in range(gpu_count):
            try:
                props = torch.cuda.get_device_properties(i)
                total_memory = props.total_memory / 1024**3  # GB

                # 获取当前显存使用
                allocated = torch.cuda.memory_allocated(i) / 1024**3
                reserved = torch.cuda.memory_reserved(i) / 1024**3
                free_memory = total_memory - allocated

                logger.info(
                    f"  - GPU {i} ({props.name}): {allocated:.1f}GB / {total_memory:.1f}GB 已使用，{free_memory:.1f}GB 可用"
                )

                if free_memory > max_free_memory:
                    max_free_memory = free_memory
                    best_gpu = i
            except Exception as e:
                logger.warning(f"  - GPU {i}: 无法访问 ({e})")

        logger.info(
            f"  - 推荐使用GPU {best_gpu}（可用显存最多: {max_free_memory:.1f}GB）"
        )

        # 检查配置的GPU是否可用
        config_gpu = AI_CONFIG["gpu"]["device_id"]
        if config_gpu >= gpu_count:
            logger.warning(
                f"⚠️  配置的GPU {config_gpu} 不存在，当前只有 {gpu_count} 个可见GPU"
            )
            logger.warning(f"   建议修改为GPU 0 到 {gpu_count - 1} 之间的值")
            return True

        try:
            props = torch.cuda.get_device_properties(config_gpu)
            total_memory = props.total_memory / 1024**3
            allocated = torch.cuda.memory_allocated(config_gpu) / 1024**3
            config_free = total_memory - allocated

            if config_free < 18:  # 需要至少18GB可用显存
                logger.warning(
                    f"⚠️  配置的GPU {config_gpu} 可用显存不足({config_free:.1f}GB)，建议改为GPU {best_gpu}"
                )
                logger.warning(
                    f"   修改方法：将 AI_CONFIG['gpu']['device_id'] 改为 {best_gpu}"
                )
        except Exception as e:
            logger.warning(f"⚠️  无法检查配置的GPU {config_gpu}: {e}")

        return True
    else:
        logger.warning("CUDA不可用，将使用CPU运行（速度较慢）")
        return False


class AIService:
    """AI服务类 - 管理模型加载和推理"""

    def __init__(self, model_path: str = None, adapter_path: str = None):
        """
        初始化AI服务

        Args:
            model_path: 基础模型路径，默认使用 server/model-dir
            adapter_path: LoRA微调权重路径（可选）
        """
        self.model = None
        self.tokenizer = None
        self.model_loaded = False

        # 设置模型路径
        if model_path is None:
            # 默认使用 server/model-dir
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(current_dir, "model-dir")

        self.model_path = model_path
        self.adapter_path = adapter_path

        logger.info(f"AI服务初始化 - 模型路径: {self.model_path}")
        if adapter_path:
            logger.info(f"LoRA权重路径: {self.adapter_path}")

    def load_model(self):
        """加载模型和tokenizer"""
        if self.model_loaded:
            logger.info("模型已加载，跳过重复加载")
            return

        try:
            # 检查GPU状态
            gpu_available = check_gpu_status()

            logger.info(f"正在加载模型: {self.model_path}")

            from modelscope import AutoModelForCausalLM, AutoTokenizer

            # 获取配置
            gpu_config = AI_CONFIG["gpu"]
            model_config = AI_CONFIG["model"]

            # 确定torch数据类型
            dtype_map = {
                "bfloat16": torch.bfloat16,
                "float16": torch.float16,
                "float32": torch.float32,
            }
            torch_dtype = dtype_map.get(model_config["torch_dtype"], torch.bfloat16)

            # 加载模型 - 使用与 infer.py 完全相同的方式
            if gpu_available:
                # 使用 device_map="auto"，与 infer.py 完全一致
                logger.info("使用自动设备映射加载模型（与 infer.py 一致）")
                try:
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_path,
                        torch_dtype=torch_dtype,
                        device_map="auto",
                        trust_remote_code=True,
                    )
                except Exception as e:
                    # 如果auto失败，尝试使用cuda:0
                    logger.warning(f"auto模式加载失败 ({e})，尝试使用cuda:0")
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_path,
                        torch_dtype=torch_dtype,
                        device_map="cuda:0",
                        trust_remote_code=True,
                    )
            elif gpu_config["enable_cpu_fallback"]:
                # 使用CPU加载（备用方案）
                logger.warning("使用CPU加载模型，推理速度会较慢")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    torch_dtype=torch.float32,  # CPU使用float32
                    device_map="cpu",
                    trust_remote_code=model_config["trust_remote_code"],
                    low_cpu_mem_usage=model_config["low_cpu_mem_usage"],
                )
            else:
                raise RuntimeError("GPU不可用且CPU备用模式已禁用")

            # 加载tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, trust_remote_code=True
            )

            # 修复tokenizer配置，防止CUDA device-side assert错误
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            if self.tokenizer.pad_token_id is None:
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

            # 如果有微调的LoRA权重，加载并合并
            if self.adapter_path and os.path.exists(self.adapter_path):
                logger.info(f"正在加载LoRA权重: {self.adapter_path}")
                from peft import PeftModel

                self.model = PeftModel.from_pretrained(self.model, self.adapter_path)
                self.model = self.model.merge_and_unload()
                logger.info("LoRA权重合并完成")

            self.model_loaded = True
            logger.info("模型加载完成！")

            # 加载完成后检查显存使用情况
            if torch.cuda.is_available():
                current_device = torch.cuda.current_device()
                memory_allocated = torch.cuda.memory_allocated(current_device) / 1024**3
                memory_reserved = torch.cuda.memory_reserved(current_device) / 1024**3
                logger.info(
                    f"模型加载后显存使用: {memory_allocated:.2f}GB (预留: {memory_reserved:.2f}GB)"
                )

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self.model_loaded = False
            raise

    def generate_response(
        self,
        user_input: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.7,
        max_new_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> str:
        """
        生成AI回复

        Args:
            user_input: 用户输入内容
            system_prompt: 系统提示词
            temperature: 采样温度 (0-1)，越高越随机
            max_new_tokens: 最大生成token数
            top_p: nucleus采样参数

        Returns:
            str: AI生成的回复
        """
        if not self.model_loaded:
            self.load_model()

        try:
            # 构建对话消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ]

            # 应用对话模板
            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            # 编码输入
            model_inputs = self.tokenizer([text], return_tensors="pt").to(
                self.model.device
            )

            # 生成回复（使用与 infer.py 相同的方式）
            logger.info("正在生成AI回复...")

            # 使用简单的生成参数，与 infer.py 保持一致
            if AI_CONFIG["inference"]["use_no_grad"]:
                with torch.no_grad():  # 节省显存
                    generated_ids = self.model.generate(
                        **model_inputs,  # 直接展开，包含 input_ids 和 attention_mask
                        max_new_tokens=max_new_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        do_sample=True if temperature > 0 else False,
                    )
            else:
                generated_ids = self.model.generate(
                    **model_inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True if temperature > 0 else False,
                )

            # 解码输出
            generated_ids = [
                output_ids[len(input_ids) :]
                for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]

            response = self.tokenizer.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0]
            logger.info("AI回复生成完成")

            # 解析response，提取<think>内容
            parsed_response = self._parse_response(response)
            return parsed_response

        except Exception as e:
            logger.error(f"生成回复时出错: {e}")
            raise

    def generate_report(self, report_data: Dict[str, Any]) -> str:
        """
        生成投诉分析报告

        Args:
            report_data: 包含统计数据的字典

        Returns:
            str: 生成的报告内容
        """
        # 构建报告生成的提示词
        system_prompt = """你是一位专业的数据分析专家，擅长分析工商投诉数据并撰写详细的分析报告。
请根据提供的数据，生成一份专业、清晰、有洞察力的投诉分析报告。
报告应包含：数据概况、趋势分析、问题总结和监管建议。"""

        # 构建数据摘要
        user_input = f"""请根据以下投诉数据生成一份详细的分析报告：

数据概况：
- 分析时间范围：{report_data.get("time_range", "未指定")}
- 总投诉量：{report_data.get("total_complaints", 0)}条
- 涉及企业数：{report_data.get("total_companies", 0)}家
- 涉及行业数：{report_data.get("total_industries", 0)}个
- 重复投诉企业数：{report_data.get("repeat_companies", 0)}家

投诉趋势：
{report_data.get("trend_summary", "暂无趋势数据")}

投诉最多的企业排行（前10名）：
{report_data.get("top_companies", "暂无企业数据")}

请生成一份包含以下部分的专业报告：
1. 摘要（简明扼要总结关键发现）
2. 数据概况（详细说明数据范围和基本情况，包括总投诉量、涉及企业数、涉及行业数、重复投诉企业数）
3. 投诉趋势分析（分析投诉量的变化趋势和规律）
4. 重点企业分析（分析投诉最多的企业及其特点）
5. 问题总结（总结主要问题类型和特征）
6. 监管建议（提出针对性的监管措施和改进方向）

要求：语言专业、数据准确、分析深入、建议可行。务必在报告中使用所有提供的数据信息。"""

        # 使用配置的参数
        inference_config = AI_CONFIG["inference"]
        return self.generate_response(
            user_input=user_input,
            system_prompt=system_prompt,
            temperature=inference_config["report_temperature"],
            max_new_tokens=inference_config["report_max_tokens"],
        )

    def generate_reply_suggestion(self, complaint_content: str) -> str:
        """
        生成投诉回复建议

        Args:
            complaint_content: 市民投诉内容

        Returns:
            str: AI生成的回复建议
        """
        system_prompt = """你是一位经验丰富的市场监管局工作人员，负责处理市民投诉。
请根据市民的投诉内容，生成一份专业、得体、有效的官方回复。
回复应该：
1. 表明已收到并重视投诉
2. 说明处理措施或调查情况
3. 给出解决方案或处理结果
4. 语气专业、态度诚恳
5. 长度适中（100-200字）"""

        user_input = f"""市民投诉内容如下：

{complaint_content}

请生成一份专业的官方回复建议。"""

        # 使用配置的参数
        inference_config = AI_CONFIG["inference"]
        return self.generate_response(
            user_input=user_input,
            system_prompt=system_prompt,
            temperature=inference_config["reply_temperature"],
            max_new_tokens=inference_config["reply_max_tokens"],
        )

    def _parse_response(self, response: str) -> dict:
        """
        解析AI响应，提取<think>标签中的思考过程

        Args:
            response: AI生成的原始响应

        Returns:
            dict: 包含thinking和reply的字典
        """
        import re

        # 查找<think>标签内容
        think_pattern = r"<think>(.*?)</think>"
        think_match = re.search(think_pattern, response, re.DOTALL)

        if think_match:
            thinking = think_match.group(1).strip()
            # 移除<think>标签后的内容作为回复
            reply = re.sub(think_pattern, "", response, flags=re.DOTALL).strip()
        else:
            thinking = None
            reply = response.strip()

        return {"thinking": thinking, "reply": reply, "full_response": response}

    def unload_model(self):
        """卸载模型以释放显存"""
        if self.model_loaded:
            logger.info("正在卸载模型...")
            del self.model
            del self.tokenizer
            torch.cuda.empty_cache()
            self.model = None
            self.tokenizer = None
            self.model_loaded = False
            logger.info("模型已卸载")


# 全局AI服务实例（懒加载）
_ai_service_instance: Optional[AIService] = None


def get_ai_service(model_path: str = None, adapter_path: str = None) -> AIService:
    """
    获取AI服务实例（单例模式）

    Args:
        model_path: 模型路径（首次调用时设置）
        adapter_path: LoRA权重路径（可选）

    Returns:
        AIService: AI服务实例
    """
    global _ai_service_instance

    if _ai_service_instance is None:
        _ai_service_instance = AIService(
            model_path=model_path, adapter_path=adapter_path
        )

    return _ai_service_instance
