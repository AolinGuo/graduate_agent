#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的AI服务接口 - 自动选择transformers或vLLM
根据配置和环境自动选择最优的推理引擎
"""

import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 配置：选择使用哪种推理引擎
AI_ENGINE_CONFIG = {
    "engine": os.getenv("AI_ENGINE", "transformers"),  # 'transformers' 或 'vllm'
    "auto_fallback": True,  # 如果vllm不可用，自动回退到transformers
}


class UnifiedAIService:
    """统一的AI服务 - 自动选择最佳引擎"""

    def __init__(self, model_path: str = None, adapter_path: str = None):
        """
        初始化统一AI服务

        Args:
            model_path: 模型路径
            adapter_path: LoRA权重路径（可选）
        """
        self.backend_service = None
        self.engine_type = AI_ENGINE_CONFIG["engine"]
        self.model_path = model_path
        self.adapter_path = adapter_path

        logger.info(f"初始化统一AI服务，配置引擎: {self.engine_type}")
        self._initialize_backend()

    def _initialize_backend(self):
        """初始化后端服务"""
        try:
            if self.engine_type == "vllm":
                # 尝试使用vLLM
                logger.info("尝试加载vLLM引擎...")
                try:
                    from src.ai_service_vllm import VLLMAIService

                    self.backend_service = VLLMAIService(model_path=self.model_path)
                    logger.info("✓ 成功初始化vLLM引擎")
                except ImportError as e:
                    if AI_ENGINE_CONFIG["auto_fallback"]:
                        logger.warning(
                            f"vLLM不可用 ({e})，回退到transformers引擎"
                        )
                        self.engine_type = "transformers"
                        self._load_transformers()
                    else:
                        raise
            else:
                # 使用transformers
                self._load_transformers()

        except Exception as e:
            logger.error(f"初始化AI服务失败: {e}")
            raise

    def _load_transformers(self):
        """加载transformers引擎"""
        logger.info("加载transformers引擎...")
        from src.ai_service import AIService

        self.backend_service = AIService(
            model_path=self.model_path, adapter_path=self.adapter_path
        )
        logger.info("✓ 成功初始化transformers引擎")

    def load_model(self):
        """加载模型（懒加载）"""
        if self.backend_service:
            self.backend_service.load_model()

    def generate_report(self, report_data: Dict[str, Any], stream: bool = False):
        """
        生成投诉分析报告

        Args:
            report_data: 报告数据
            stream: 是否流式输出（仅vLLM支持）

        Returns:
            dict or Generator: 报告内容
        """
        if not self.backend_service:
            raise RuntimeError("AI服务未初始化")

        # vLLM支持流式输出
        if self.engine_type == "vllm" and stream:
            return self.backend_service.generate_report(report_data, stream=True)

        # 非流式输出
        return self.backend_service.generate_report(report_data)

    def generate_reply_suggestion(
        self, complaint_content: str, stream: bool = False
    ):
        """
        生成投诉回复建议

        Args:
            complaint_content: 投诉内容
            stream: 是否流式输出（仅vLLM支持）

        Returns:
            dict or Generator: 回复建议
        """
        if not self.backend_service:
            raise RuntimeError("AI服务未初始化")

        # vLLM支持流式输出
        if self.engine_type == "vllm" and stream:
            return self.backend_service.generate_reply_suggestion(
                complaint_content, stream=True
            )

        # 非流式输出
        return self.backend_service.generate_reply_suggestion(complaint_content)

    def get_engine_info(self) -> Dict[str, Any]:
        """获取当前引擎信息"""
        return {
            "engine": self.engine_type,
            "model_loaded": (
                self.backend_service.model_loaded
                if self.backend_service
                else False
            ),
            "supports_streaming": self.engine_type == "vllm",
            "model_path": self.model_path,
        }

    def unload_model(self):
        """卸载模型"""
        if self.backend_service:
            self.backend_service.unload_model()


# 全局统一AI服务实例（懒加载）
_unified_ai_service_instance: Optional[UnifiedAIService] = None


def get_unified_ai_service(
    model_path: str = None, adapter_path: str = None
) -> UnifiedAIService:
    """
    获取统一AI服务实例（单例模式）

    Args:
        model_path: 模型路径
        adapter_path: LoRA权重路径

    Returns:
        UnifiedAIService: 统一AI服务实例
    """
    global _unified_ai_service_instance

    if _unified_ai_service_instance is None:
        _unified_ai_service_instance = UnifiedAIService(
            model_path=model_path, adapter_path=adapter_path
        )

    return _unified_ai_service_instance


def set_ai_engine(engine: str):
    """
    切换AI引擎

    Args:
        engine: 'transformers' 或 'vllm'
    """
    global _unified_ai_service_instance

    if engine not in ["transformers", "vllm"]:
        raise ValueError(f"不支持的引擎类型: {engine}")

    AI_ENGINE_CONFIG["engine"] = engine
    logger.info(f"切换AI引擎为: {engine}")

    # 重置实例，下次调用时会重新初始化
    if _unified_ai_service_instance:
        _unified_ai_service_instance.unload_model()
        _unified_ai_service_instance = None

