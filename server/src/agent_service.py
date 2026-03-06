#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话Agent服务模块
支持自然语言意图识别和工具调用

核心工具（4个）：
1. read_frontend_display   - 读取前端当前显示的内容
2. update_frontend_filter  - 更改前端控制台的筛选条件
3. generate_report         - 编写投诉分析报告（调用 Deepseek API）
4. generate_reply_suggestion - 生成投诉辅助回复（调用本地 vLLM）
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List


class FuncCallRequest:
    def __init__(self, tool_name: str, parameters: Dict[str, Any], thought: str = ""):
        self.tool_name = tool_name
        self.parameters = parameters
        self.thought = thought

    def __str__(self) -> str:
        return json.dumps(
            {
                "FuncCallRequest": {
                    "thought": self.thought,
                    "tool": self.tool_name,
                    "parameters": self.parameters,
                }
            },
            ensure_ascii=False,
        )


class FuncCallResponse:
    def __init__(self, tool_name: str, result: Any, success: bool):
        self.tool_name = tool_name
        self.result = result
        self.success = success

    def __str__(self) -> str:
        return json.dumps(
            {
                "FuncCallResponse": {
                    "tool_name": self.tool_name,
                    "success": self.success,
                    "result": self.result,
                }
            },
            ensure_ascii=False,
        )


logger = logging.getLogger(__name__)


# ============================================================
# Deepseek API 服务
# ============================================================
class DeepseekService:
    """包装 Deepseek API 调用"""

    def __init__(self):
        from openai import OpenAI
        from dotenv import load_dotenv

        load_dotenv()
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            logger.warning(
                "未找到 DEEPSEEK_API_KEY 环境变量，Deepseek API 调用可能会失败"
            )

        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = "deepseek-chat"

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict]] = None,
    ):
        """调用 Deepseek chat completions，支持 tool calling。
        返回原始 response.choices[0].message 对象（而非字符串），
        以便调用方自行判断 finish_reason 和 tool_calls。
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
            if response_format:
                kwargs["response_format"] = response_format
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message
        except Exception as e:
            logger.error(f"Deepseek API 调用失败: {e}", exc_info=True)
            raise


_deepseek_instance = None


def get_deepseek_service() -> DeepseekService:
    global _deepseek_instance
    if _deepseek_instance is None:
        _deepseek_instance = DeepseekService()
    return _deepseek_instance


# ============================================================
# 工具定义（OpenAI / Deepseek 标准 function calling 格式）
# ============================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_frontend_display",
            "description": "读取前端仪表板当前显示的内容（统计、筛选、排名等）。分析现状前的必要步骤。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        # 内部元数据，不上传给模型
        "_action_type": "read_display",
    },
    {
        "type": "function",
        "function": {
            "name": "update_frontend_filter",
            "description": "更改前端全局筛选条件（日期、企业、行业等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "开始日期，格式 YYYY-MM-DD",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期，格式 YYYY-MM-DD",
                    },
                    "companies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "企业名称列表，精确匹配",
                    },
                    "industries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "行业名称列表",
                    },
                    "industry_level1": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "行业名称(一级)列表",
                    },
                    "industry_level2": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "行业名称(二级)列表",
                    },
                    "industry_level3": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "行业名称(三级)列表",
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "投诉问题分类列表",
                    },
                    "issue_level1": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "涉及问题(一级)列表",
                    },
                    "issue_level2": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "涉及问题(二级)列表",
                    },
                },
                "required": [],
            },
        },
        "_action_type": "filter_data",
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "基于当前统计数据编写专业的投诉分析报告。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "报告开始日期"},
                    "end_date": {"type": "string", "description": "报告结束日期"},
                },
                "required": [],
            },
        },
        "_action_type": "show_report",
    },
    {
        "type": "function",
        "function": {
            "name": "generate_reply_suggestion",
            "description": "调用本地大模型为用户提供的投诉原文生成官方回复建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "complaint_content": {"type": "string", "description": "投诉原文"},
                },
                "required": ["complaint_content"],
            },
        },
        "_action_type": "show_reply",
    },
]

# 传给模型的工具列表（只含 type + function，不含内部 _action_type）
_TOOLS_FOR_API = [{"type": t["type"], "function": t["function"]} for t in TOOLS]
# 内部映射表：工具名 → 完整元数据
_TOOL_MAP: Dict[str, dict] = {t["function"]["name"]: t for t in TOOLS}


class AgentService:
    """对话Agent服务类"""

    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self._last_context: Optional[Dict[str, Any]] = None
        logger.info("AgentService 初始化完成")

    def _get_deepseek_service(self):
        return get_deepseek_service()

    def _extract_context_info(self, context: Optional[Dict[str, Any]]) -> str:
        """从 context 中提取可读的当前状态描述"""
        if not context:
            return ""

        parts = []

        stats = context.get("currentStats")
        if stats:
            parts.append("**当前页面统计数据**：")
            parts.append(f"- 投诉总量：{stats.get('total_complaints', 0)} 条")
            parts.append(f"- 涉及企业：{stats.get('companies_count', 0)} 家")
            parts.append(f"- 涉及行业：{stats.get('industries_count', 0)} 个")
            parts.append(f"- 预警企业：{stats.get('repeat_companies_count', 0)} 家")
            ranking = stats.get("company_ranking", [])
            if ranking:
                parts.append("**投诉最多企业（前10名）**：")
                for idx, company in enumerate(ranking[:10], 1):
                    parts.append(
                        f"  {idx}. {company.get('name', '未知')}：{company.get('count', 0)} 条"
                    )

        filters = context.get("filters", {})
        if filters:
            if filters.get("startDate") or filters.get("endDate"):
                parts.append(
                    f"**当前时间筛选**：{filters.get('startDate', '开始')} 至 {filters.get('endDate', '结束')}"
                )
            if filters.get("selectedCompanies"):
                companies_str = "、".join(filters["selectedCompanies"][:3])
                if len(filters["selectedCompanies"]) > 3:
                    companies_str += " 等"
                parts.append(f"**已筛选企业**：{companies_str}")
            if filters.get("selectedIndustries"):
                industries_str = "、".join(filters["selectedIndustries"][:3])
                parts.append(f"**已筛选行业**：{industries_str}")

        # 趋势数据摘要
        trend = context.get("trendData", {})
        trend_mode = trend.get("mode", "empty")
        if trend_mode == "daily" and trend.get("data"):
            counts = [d["count"] for d in trend["data"] if "count" in d]
            if counts:
                parts.append(
                    f"**投诉趋势（按{context.get('trendPeriod', '天')}，共{len(counts)}个点）**："
                    f"最高 {max(counts)} 条，最低 {min(counts)} 条，均值 {sum(counts) / len(counts):.1f} 条"
                )
        elif trend_mode == "aggregated":
            monthly = trend.get("monthly", [])
            if monthly:
                counts = [d["count"] for d in monthly]
                parts.append(
                    f"**投诉趋势（按月聚合，共{len(monthly)}个月）**："
                    f"最高 {max(counts)} 条，最低 {min(counts)} 条"
                )

        # 旭日图摘要（问题分类 top-3）
        sunburst = context.get("sunburstSummary")
        if sunburst:
            cat3 = sunburst.get("category_top3", [])
            if cat3:
                cat_str = "、".join(f"{c['name']}({c['percent']}%)" for c in cat3)
                parts.append(f"**投诉问题分类 Top3**：{cat_str}")
            issue3 = sunburst.get("issue_top3", [])
            if issue3:
                issue_str = "、".join(f"{c['name']}({c['percent']}%)" for c in issue3)
                parts.append(f"**涉及问题类型 Top3**：{issue_str}")

        # 散点图摘要（高风险企业）
        scatter = context.get("scatterSummary")
        if scatter:
            parts.append(
                f"**企业风险分布**：共 {scatter.get('total_companies', 0)} 家，"
                f"预警企业 {scatter.get('warning_companies', 0)} 家"
            )
            top10 = scatter.get("top10_companies", [])
            if top10:
                parts.append("**散点图 Top10 企业（投诉量）**：")
                for idx, c in enumerate(top10, 1):
                    warn = "⚠️" if c.get("is_warning") else ""
                    parts.append(
                        f"  {idx}. {c['name']}{warn}：投诉 {c['count']} 条，问题类型 {c['diversity']} 种"
                    )

        return "\n" + "\n".join(parts) if parts else ""

    def process_message(
        self, user_message: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """使用 Deepseek 原生工具调用（function calling）处理用户消息。

        流程：
        1. 携带 tools 列表发起首轮请求
        2. 若模型返回 tool_calls → 逐个执行工具 → 将结果以 role:tool 追加进对话
        3. 若遇到 update_frontend_filter，立即中断并告知前端刷新
        4. 执行完所有工具后，发起第二轮请求获取最终自然语言回复
        """
        try:
            self._last_context = context
            deepseek = self._get_deepseek_service()

            context_info = self._extract_context_info(context)
            system_prompt = (
                "你是一个专业的投诉处理助手，可以调用工具帮助用户分析数据、筛选数据、生成报告或起草回复。"
                "请根据用户意图选择合适的工具，工具执行顺序应符合逻辑（如需先筛选再分析）。\n"
                "generate_reply_suggestion 仅在用户提供了具体投诉原文时调用。\n"
            )
            if context_info:
                system_prompt += f"\n## 当前仪表板状态\n{context_info}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            last_action = None
            thinking = None

            # ---- 工具调用循环 ----
            MAX_ROUNDS = 5  # 防止无限循环
            for _round in range(MAX_ROUNDS):
                msg = deepseek.chat(
                    messages,
                    temperature=0.1,
                    tools=_TOOLS_FOR_API,
                )

                # 将模型回复追加进对话历史
                messages.append(msg)  # openai message 对象可直接 append

                # 无工具调用 → 循环结束，使用当前内容作为最终回复
                if not msg.tool_calls:
                    final_message = msg.content or "已按要求完成操作。"
                    return {
                        "success": True,
                        "message": final_message,
                        "action": last_action,
                        "thinking": thinking,
                    }

                # 有工具调用 → 逐个执行
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        params = json.loads(tool_call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        params = {}

                    logger.info(
                        f"[Round {_round + 1}] 调用工具: {tool_name}, 参数: {params}"
                    )

                    res = self._call_tool(tool_name, params)
                    tool_result_str = json.dumps(
                        res.get("data")
                        if res.get("success")
                        else {"error": res.get("error")},
                        ensure_ascii=False,
                    )

                    # 追加工具结果消息（role: tool）
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result_str,
                        }
                    )

                    if res.get("success") and tool_name in _TOOL_MAP:
                        last_action = {
                            "type": _TOOL_MAP[tool_name]["_action_type"],
                            "data": res["data"],
                            "tool": tool_name,
                        }

                        # update_frontend_filter：立即中断，等待前端刷新后回调
                        if tool_name == "update_frontend_filter":
                            logger.info(
                                "检测到数据筛选请求，触发中断机制，等待前端刷新。"
                            )
                            return {
                                "success": True,
                                "message": "正在为您调整数据范围，请稍候...",
                                "action": last_action,
                                "thinking": thinking,
                                "need_callback": True,
                            }

            # 超过最大轮次，返回最后一条内容
            logger.warning("工具调用轮次已达上限，强制返回。")
            last_msg = messages[-1]
            final_message = (
                last_msg.get("content", "已按要求完成操作。")
                if isinstance(last_msg, dict)
                else getattr(last_msg, "content", "已按要求完成操作。")
            )
            return {
                "success": True,
                "message": final_message,
                "action": last_action,
                "thinking": thinking,
            }

        except Exception as e:
            logger.error(f"处理失败: {e}", exc_info=True)
            return {"success": False, "message": f"系统异常: {str(e)}"}

    def _parse_intent_json(self, ai_reply: str) -> Optional[dict]:
        try:
            return json.loads(ai_reply)
        except:
            return None

    def _call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "read_frontend_display":
            return self._tool_read_frontend_display()
        if tool_name == "update_frontend_filter":
            return self._tool_update_frontend_filter(parameters)
        if tool_name == "generate_report":
            return self._tool_generate_report(parameters)
        if tool_name == "generate_reply_suggestion":
            return self._tool_generate_reply_suggestion(parameters)
        return {"success": False, "error": f"未知工具: {tool_name}"}

    def _tool_read_frontend_display(self) -> Dict[str, Any]:
        context = self._last_context or {}
        return {"success": True, "data": context.get("currentStats", {})}

    def _tool_update_frontend_filter(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        工具2：更改前端控制台筛选条件
        返回新筛选条件，前端接收到 filter_data action 后自动刷新所有图表
        """
        # 清理空值参数
        clean_params = {
            k: v for k, v in parameters.items() if v is not None and v != "" and v != []
        }
        logger.info(f"update_frontend_filter: 新筛选条件 = {clean_params}")
        return {"success": True, "data": clean_params}

    def _tool_generate_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        工具3：生成投诉分析报告
        优化：完整读取前端 context 的细节，确保报告言之有物
        """
        # 1. 重新调用详细的上下文提取函数，获取包含趋势、排名、风险企业的全量信息
        context = self._last_context or {}
        # 利用类内现有的详细提取方法获取文本化的数据摘要
        detailed_data_summary = self._extract_context_info(context)

        if not detailed_data_summary or "投诉总量:0" in detailed_data_summary:
            return {
                "success": False,
                "error": "当前前端无有效统计数据，请先尝试筛选或刷新数据。",
            }

        # 3. 构建深度 Prompt
        system_prompt = f"""你是一位专业的政务数据分析专家。根据提供的详细统计数据编写分析报告。
仅使用纯文本格式，所有内容以自然段落呈现，无需任何格式标记
报告必须包含：数据基本面分析、投诉趋势研判、重点企业/行业风险评估、以及基于数据的监管对策建议。"""

        user_input = f"""请针对以下实时抓取的投诉数据进行深度分析：
        
{detailed_data_summary}

请确保分析中引用具体数字。"""

        deepseek = self._get_deepseek_service()
        # 增加 max_tokens 以容纳更详尽的分析
        report = deepseek.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.7,
            max_tokens=4096,
        )

        return {"success": True, "data": {"report": report}}

    def _tool_generate_reply_suggestion(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        工具4：生成投诉辅助回复
        （继续使用本地大模型 + LoRA 模块）
        """
        complaint_content = parameters.get("complaint_content", "").strip()
        if not complaint_content:
            return {"success": False, "error": "缺少投诉内容参数 complaint_content"}

        from src.ai_service_vllm import get_vllm_ai_service

        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        lora_dir = os.path.join(current_dir, "lora-dir")

        logger.info(f"generate_reply_suggestion: 调用本地 vLLM 并使用 LoRA: {lora_dir}")
        adapter_path = os.getenv("LORA_PATH", lora_dir)

        ai_service = get_vllm_ai_service(
            model_path=self.model_path, adapter_path=adapter_path
        )
        reply = ai_service.generate_reply_suggestion(complaint_content, stream=False)

        # vLLM generate_response返回的是一个 dict {"thinking": ..., "reply": ..., "full_response": ...}
        # generate_reply_suggestion 在 ai_service_vllm 里面返回 dict or Generator
        # 取 reply 字段返回给前端
        if isinstance(reply, dict):
            reply_text = reply.get("reply", str(reply))
        else:
            reply_text = str(reply)

        logger.info("generate_reply_suggestion: 生成投诉回复建议完成")
        return {
            "success": True,
            "data": {
                "reply": reply_text,
                "complaint_content": complaint_content,
            },
        }


def get_agent_service(model_path: str = None) -> AgentService:
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService(model_path=model_path)
    return _agent_service_instance


_agent_service_instance = None
