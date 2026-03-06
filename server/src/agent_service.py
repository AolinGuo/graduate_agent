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
    ) -> str:
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

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
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
# 工具定义
# ============================================================
TOOLS = [
    {
        "name": "read_frontend_display",
        "description": "读取前端仪表板当前显示的内容（统计、筛选、排名等）。分析现状前的必要步骤。",
        "parameters": {},
        "action_type": "read_display",
    },
    {
        "name": "update_frontend_filter",
        "description": "更改前端全局筛选条件（日期、企业、行业等）。",
        "parameters": {
            "start_date": {
                "type": "string",
                "description": "开始日期，格式 YYYY-MM-DD（可选）",
            },
            "end_date": {
                "type": "string",
                "description": "结束日期，格式 YYYY-MM-DD（可选）",
            },
            "companies": {
                "type": "array",
                "description": "企业名称列表，精确匹配（可选）",
            },
            "industries": {
                "type": "array",
                "description": "行业名称列表（可选）",
            },
            "industry_level1": {
                "type": "array",
                "description": "行业名称(一级)列表（可选）",
            },
            "industry_level2": {
                "type": "array",
                "description": "行业名称(二级)列表（可选）",
            },
            "industry_level3": {
                "type": "array",
                "description": "行业名称(三级)列表（可选）",
            },
            "categories": {
                "type": "array",
                "description": "投诉问题分类列表（可选）",
            },
            "issue_level1": {
                "type": "array",
                "description": "涉及问题(一级)列表（可选）",
            },
            "issue_level2": {
                "type": "array",
                "description": "涉及问题(二级)列表（可选）",
            },
        },
        "action_type": "filter_data",
    },
    {
        "name": "generate_report",
        "description": "基于当前统计数据编写专业的分析报告。",
        "parameters": {
            "start_date": {"type": "string", "description": "开始日期"},
            "end_date": {"type": "string", "description": "结束日期"},
        },
        "action_type": "show_report",
    },
    {
        "name": "generate_reply_suggestion",
        "description": "调用本地大模型生成官方回复建议。",
        "parameters": {
            "complaint_content": {"type": "string", "description": "投诉原文"},
        },
        "action_type": "show_reply",
    },
]

_TOOL_MAP: Dict[str, dict] = {t["name"]: t for t in TOOLS}


class AgentService:
    """对话Agent服务类"""

    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self._last_context: Optional[Dict[str, Any]] = None
        logger.info("AgentService 初始化完成")

    def _get_deepseek_service(self):
        return get_deepseek_service()

    def _build_tools_prompt(self) -> str:
        lines = []
        for i, tool in enumerate(TOOLS, 1):
            lines.append(f"{i}. {tool['name']}: {tool['description']}")
        return "\n".join(lines)

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
        """多轮对话与流水线执行逻辑"""
        try:
            self._last_context = context
            deepseek = self._get_deepseek_service()
            messages = []

            # --- Round 1: 规划 ---
            tools_prompt = self._build_tools_prompt()
            context_info = self._extract_context_info(context)
            system_planner = f"""你是一个投诉处理助手。请分析用户意图并拆解任务。
## 可用工具
{tools_prompt}
## 当前状态
{context_info}

#意图识别规则
# 1.**明确执行步骤**:先分析用户完整意图，再列出需要依次执行的工具步骤。
# 2.**工具调用顺序**若用户要求「筛选数据后再分析」，应先调用‘update_frontend_filter，再调用‘run_time_series_analysis'。若用户要求「查看当前数据并生成报告」，应先调用 ‘read_frontend_display，再调用 ‘generate_report。单步任务(如仅筛选、仅查看、仅生成报告)只调用一个工具。
# 3.**参数解析**:
- 年份 (如 [2023年」)  start_date:"2023-01-01",end_date:"2023-12-31"
- 企业名称>companies数组
# 4.**generate_reply_suggestion**:仅在用户明确提供投诉原文并要求起草回复时调用。
5.**read_frontend_display**:仅在用户询问当前显示内容时调用，无需任何参数。

{
  "thought": "对用户意图的分析，说明选择该工具的原因",
  "steps": [
    {
      "step": 1,
      "tool": "工具名称",
      "parameters": {
        "参数名": "参数值"
      },
      "reason": "此步骤的作用"
    }
  ],
  "message": "给用户的简洁友好回复（中文，不超过50字）"
}
若只需一个工具，steps列表只有一项。

"""

            messages.append({"role": "system", "content": system_planner})
            messages.append({"role": "user", "content": user_message})

            planner_reply = deepseek.chat(
                messages, temperature=0.1, response_format={"type": "json_object"}
            )
            intent = json.loads(planner_reply)
            steps = intent.get("steps", [])

            # 如果没有工具调用，直接返回消息
            if not steps:
                final_message = intent.get("message", "已按要求完成操作。")
                return {
                    "success": True,
                    "message": final_message,
                    "action": None,
                    "thinking": intent.get("thought"),
                }

            # --- 执行流水线 ---
            last_action = None

            requests_str_list = []
            responses_str_list = []

            for step in steps:
                tool_name = step.get("tool")
                if not tool_name:
                    continue
                params = step.get("parameters", {})

                # 实例化 FuncCallRequest
                req = FuncCallRequest(
                    tool_name=tool_name,
                    parameters=params,
                    thought=step.get("reason", ""),
                )
                requests_str_list.append(str(req))

                # 执行当前工具
                res = self._call_tool(tool_name, params)

                # 实例化 FuncCallResponse
                resp = FuncCallResponse(
                    tool_name=tool_name,
                    result=res.get("data") if res.get("success") else res.get("error"),
                    success=res.get("success", False),
                )
                responses_str_list.append(str(resp))

                if res.get("success") and tool_name in _TOOL_MAP:
                    # 记录动作
                    last_action = {
                        "type": _TOOL_MAP[tool_name]["action_type"],
                        "data": res["data"],
                        "tool": tool_name,
                    }
                    if tool_name == "update_frontend_filter":
                        logger.info("检测到数据筛选请求，触发中断机制，等待前端刷新。")
                        return {
                            "success": True,
                            "message": f"正在为您调整数据范围，请稍候...",
                            "action": last_action,
                            "thinking": intent.get("thought"),
                            "need_callback": True,  # 告知前端执行完此 action 后需要自动回调
                        }

            # --- Round 2: 结合工具结果生成最终回复 ---
            if requests_str_list and responses_str_list:
                # 将 str(FuncCallRequest) 附加为 assistant 消息
                messages.append(
                    {"role": "assistant", "content": "\n".join(requests_str_list)}
                )
                # 将 str(FuncCallResponse) 附加为 user 消息，请求最终总结
                messages.append(
                    {
                        "role": "user",
                        "content": f"以下是工具执行的结果：\n{chr(10).join(responses_str_list)}\n请根据以上工具返回结果，直接给出对我的最终回复（请直接使用自然语言回复，不要输出JSON）。",
                    }
                )

                # 发起第二轮对话生成最终结果
                final_reply = deepseek.chat(messages, temperature=0.7)
                final_message = final_reply
            else:
                final_message = intent.get("message", "已按要求完成操作。")

            return {
                "success": True,
                "message": final_message,
                "action": last_action,
                "thinking": intent.get("thought"),
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
