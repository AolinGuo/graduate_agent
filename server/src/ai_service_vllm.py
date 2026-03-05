import logging
from typing import Optional, Dict, Any, Generator
import os

logger = logging.getLogger(__name__)

# RAG 服务懒加载单例（避免在模块导入时就初始化占用资源）
_rag_service_instance = None


def _get_rag_service():
    """懒加载并返回 LegalRAGService 单例"""
    global _rag_service_instance
    if _rag_service_instance is None:
        try:
            from .rag_service import LegalRAGService

            _rag_service_instance = LegalRAGService()
            logger.info("LegalRAGService 初始化成功")
        except Exception as e:
            logger.warning(f"LegalRAGService 初始化失败，将跳过 RAG 检索: {e}")
    return _rag_service_instance


# vLLM配置（支持通过环境变量覆盖）
VLLM_CONFIG = {
    "model": {
        # tensor_parallel_size: 使用GPU数量，单卡设为1，多卡改为对应数量
        "tensor_parallel_size": int(os.getenv("TENSOR_PARALLEL_SIZE", "1")),
        "dtype": os.getenv("MODEL_DTYPE", "bfloat16"),
        "max_model_len": int(os.getenv("MAX_MODEL_LEN", "4096")),
        "gpu_memory_utilization": float(os.getenv("GPU_MEM_UTIL", "0.9")),
        "trust_remote_code": True,
    },
    "sampling": {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2048,
        "report_temperature": 0.7,
        "report_max_tokens": 2048,
        "reply_temperature": 0.7,
        "reply_max_tokens": 512,
    },
    "streaming": {
        "enabled": True,
        "chunk_size": 10,
    },
}


class VLLMAIService:
    """基于vLLM的AI服务类 - 高性能推理"""

    def __init__(self, model_path: str = None, adapter_path: str = None):
        """
        初始化vLLM AI服务

        Args:
            model_path: 基础模型路径，优先级：参数 > 环境变量 MODEL_PATH > server/model-dir
            adapter_path: LoRA 权重路径（vLLM 原生支持），优先级：参数 > 环境变量 LORA_PATH
        """
        self.llm = None
        self.tokenizer = None
        self.model_loaded = False

        # 设置基础模型路径：参数 > 环境变量 > 默认相对路径
        if model_path is None:
            env_path = os.getenv("MODEL_PATH")
            if env_path:
                model_path = env_path
            else:
                current_dir = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                model_path = os.path.join(current_dir, "model-dir")

        self.model_path = model_path

        # 设置 LoRA 路径：参数 > 环境变量 > None
        if adapter_path is None:
            adapter_path = os.getenv("LORA_PATH") or None
        self.adapter_path = adapter_path

        # 记录当前 GPU 配置
        gpu_visible = os.environ.get("CUDA_VISIBLE_DEVICES", "(未设置，使用全部GPU)")
        logger.info(f"vLLM AI服务初始化 - 模型路径: {self.model_path}")
        logger.info(f"vLLM AI服务初始化 - LoRA路径: {self.adapter_path}")
        logger.info(f"vLLM AI服务初始化 - CUDA_VISIBLE_DEVICES: {gpu_visible}")

    def load_model(self):
        """加载vLLM模型"""
        if self.model_loaded:
            logger.info("vLLM模型已加载，跳过重复加载")
            return

        try:
            logger.info(f"正在使用vLLM加载模型: {self.model_path}")
            if self.adapter_path:
                logger.info(f"同时加载 LoRA 权重: {self.adapter_path}")

            from vllm import LLM
            from transformers import AutoTokenizer

            # 获取配置
            model_config = VLLM_CONFIG["model"]

            # 构建 LLM 初始化参数
            llm_kwargs = dict(
                model=self.model_path,
                tensor_parallel_size=model_config["tensor_parallel_size"],
                dtype=model_config["dtype"],
                max_model_len=model_config["max_model_len"],
                gpu_memory_utilization=model_config["gpu_memory_utilization"],
                trust_remote_code=model_config["trust_remote_code"],
            )

            # 如果指定了 LoRA 权重，通过 enable_lora 启用
            if self.adapter_path:
                llm_kwargs["enable_lora"] = True

            # 初始化vLLM引擎
            self.llm = LLM(**llm_kwargs)

            # 加载tokenizer用于构建提示词
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, trust_remote_code=True
            )

            # 修复tokenizer配置
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            if self.tokenizer.pad_token_id is None:
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

            self.model_loaded = True
            logger.info("vLLM模型加载完成！")

        except Exception as e:
            logger.error(f"vLLM模型加载失败: {e}")
            self.model_loaded = False
            raise

    def generate_response(
        self,
        user_input: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        max_new_tokens: int = None,  # 兼容 ai_service.py 的调用参数名
        top_p: float = 0.9,
        stream: bool = False,
    ):
        """
        生成AI回复

        Args:
            user_input: 用户输入内容
            system_prompt: 系统提示词
            temperature: 采样温度
            max_tokens: 最大生成token数（vLLM原生参数名）
            max_new_tokens: 兼容 transformers 风格的参数名，与 max_tokens 二选一
            top_p: nucleus采样参数
            stream: 是否启用流式输出

        Returns:
            str or Generator: AI生成的回复（非流式）或生成器（流式）
        """
        if not self.model_loaded:
            self.load_model()

        # 兼容 max_new_tokens 参数名
        if max_new_tokens is not None:
            max_tokens = max_new_tokens

        try:
            from vllm import SamplingParams

            # 构建对话消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ]

            # 应用对话模板
            prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            # 设置采样参数
            sampling_params = SamplingParams(
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )

            logger.info(f"正在生成AI回复... (stream={stream})")

            if stream:
                # 流式输出 - 返回生成器
                return self._generate_stream(prompt, sampling_params)
            else:
                # 非流式输出 - 直接返回完整结果
                outputs = self.llm.generate([prompt], sampling_params)
                response = outputs[0].outputs[0].text
                logger.info("AI回复生成完成")

                # 解析response，提取<think>内容
                return self._parse_response(response)

        except Exception as e:
            logger.error(f"生成回复时出错: {e}")
            raise

    def _generate_stream(
        self, prompt: str, sampling_params
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式生成回复

        Args:
            prompt: 输入提示词
            sampling_params: 采样参数

        Yields:
            dict: 包含生成的文本片段
        """
        # vLLM的流式生成使用异步方式
        # 这里我们使用批处理模拟流式输出
        full_text = ""

        try:
            outputs = self.llm.generate([prompt], sampling_params)
            response = outputs[0].outputs[0].text

            # 解析完整响应
            parsed = self._parse_response(response)

            # 如果有thinking，先返回
            if parsed["thinking"]:
                yield {
                    "type": "thinking",
                    "content": parsed["thinking"],
                    "done": False,
                }

            # 分块返回回复内容
            reply = parsed["reply"]
            chunk_size = VLLM_CONFIG["streaming"]["chunk_size"]

            for i in range(0, len(reply), chunk_size):
                chunk = reply[i : i + chunk_size]
                full_text += chunk
                yield {
                    "type": "reply",
                    "content": chunk,
                    "done": False,
                }

            # 最后一个chunk，标记完成
            yield {
                "type": "reply",
                "content": "",
                "done": True,
                "full_text": full_text,
            }

        except Exception as e:
            logger.error(f"流式生成出错: {e}")
            yield {
                "type": "error",
                "content": str(e),
                "done": True,
            }

    def generate_report(self, report_data: Dict[str, Any], stream: bool = False):
        """
        生成投诉分析报告

        Args:
            report_data: 包含统计数据的字典
            stream: 是否启用流式输出

        Returns:
            dict or Generator: 生成的报告内容
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

投诉分类分布（旭日图）：
{report_data.get("category_summary", "暂无分类数据")}

企业风险分布（散点图，投诉量前10名）：
{report_data.get("scatter_summary", "暂无散点图数据")}

投诉最多的企业排行（前10名）：
{report_data.get("top_companies", "暂无企业数据")}

请生成一份包含以下部分的专业报告：
1. 摘要（简明扼要总结关键发现）
2. 数据概况（详细说明数据范围和基本情况）
3. 投诉趋势分析（分析投诉量的变化趋势和规律）
4. 投诉分类分析（基于旭日图数据分析主要问题类型分布）
5. 重点企业分析（结合散点图风险分布，分析投诉最多和高风险企业）
6. 监管建议（提出针对性的监管措施和改进方向）

要求：语言专业、数据准确、分析深入、建议可行。"""

        # 使用配置的参数
        sampling_config = VLLM_CONFIG["sampling"]
        return self.generate_response(
            user_input=user_input,
            system_prompt=system_prompt,
            temperature=sampling_config["report_temperature"],
            max_tokens=sampling_config["report_max_tokens"],
            stream=stream,
        )

    def generate_reply_suggestion(self, complaint_content: str, stream: bool = False):
        """
        生成投诉回复建议

        在生成回复之前，先通过 RAG 服务检索与投诉内容最相关的法律条文，
        并将其作为参考资料注入到系统提示词中，使模型能够引用具体法律依据。

        Args:
            complaint_content: 市民投诉内容
            stream: 是否启用流式输出

        Returns:
            dict or Generator: AI生成的回复建议
        """
        # ── 1. RAG 检索相关法律条文 ──────────────────────────────────────
        legal_context = ""
        try:
            rag = _get_rag_service()
            if rag is not None:
                logger.info("正在通过 RAG 检索相关法律条文...")
                results = rag.search(complaint_content, top_k=3)
                if results:
                    legal_lines = []
                    for idx, item in enumerate(results, start=1):
                        source = item.get("source", "未知来源")
                        article_id = item.get("id", "")
                        content = item.get("content", "").strip()
                        legal_lines.append(
                            f"【法条{idx}】《{source}》{article_id}\n{content}"
                        )
                    legal_context = "\n\n".join(legal_lines)
                    logger.info(f"RAG 检索到 {len(results)} 条相关法律条文")
                else:
                    logger.info("RAG 未检索到相关法律条文")
        except Exception as e:
            logger.warning(f"RAG 检索出错，将跳过法律召回: {e}")

        # ── 2. 构建系统提示词（含法律参考）──────────────────────────────
        base_prompt = """
你是一个专业的法律投诉处理助手。请根据用户的投诉内容和提供的法律条文，以第一人称（我/我们）的口吻，生成回复。回复需涵盖事件处理结果，并有理有据地引用法律条文解释原因，态度礼貌且专业。"
"""

        if legal_context:
            system_prompt = (
                base_prompt
                + "\n\n以下是与本次投诉相关的法律法规，请在回复中适当引用，使回复具有法律依据：\n\n"
                + legal_context
            )
        else:
            system_prompt = base_prompt

        # ── 3. 构建用户输入 ───────────────────────────────────────────────
        user_input = f"""市民投诉内容如下：

{complaint_content}

请生成一份专业的官方回复建议。"""

        # ── 4. 调用模型生成回复 ───────────────────────────────────────────
        sampling_config = VLLM_CONFIG["sampling"]
        return self.generate_response(
            user_input=user_input,
            system_prompt=system_prompt,
            temperature=sampling_config["reply_temperature"],
            max_tokens=sampling_config["reply_max_tokens"],
            stream=stream,
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
            logger.info("正在卸载vLLM模型...")
            del self.llm
            del self.tokenizer
            self.llm = None
            self.tokenizer = None
            self.model_loaded = False
            logger.info("vLLM模型已卸载")


# 全局vLLM AI服务实例（懒加载）
_vllm_ai_service_instance: Optional[VLLMAIService] = None


def get_vllm_ai_service(
    model_path: str = None, adapter_path: str = None
) -> VLLMAIService:
    """
    获取vLLM AI服务实例（单例模式）

    Args:
        model_path: 模型路径，为 None 时从环境变量 MODEL_PATH 读取
        adapter_path: LoRA 权重路径，为 None 时从环境变量 LORA_PATH 读取

    Returns:
        VLLMAIService: vLLM AI服务实例
    """
    global _vllm_ai_service_instance

    if _vllm_ai_service_instance is None:
        _vllm_ai_service_instance = VLLMAIService(
            model_path=model_path, adapter_path=adapter_path
        )

    return _vllm_ai_service_instance
