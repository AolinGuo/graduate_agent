#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话Agent服务模块
支持自然语言意图识别和工具调用

核心工具（5个）：
1. read_frontend_display   - 读取前端当前显示的内容
2. update_frontend_filter  - 更改前端控制台的筛选条件（日期范围、企业、行业等）
3. run_time_series_analysis - 执行时序分析，获取投诉趋势数据
4. generate_report         - 编写投诉分析报告（调用 ai_service_vllm）
5. generate_reply_suggestion - 生成投诉辅助回复（调用 ai_service_vllm）
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================
# 工具定义
# ============================================================
TOOLS = [
    {
        "name": "read_frontend_display",
        "description": (
            "读取前端仪表板当前显示的内容，包括统计数据、当前筛选条件、"
            "投诉总量、涉及企业/行业数量、企业排名等。"
            "适用场景：用户询问「现在显示的是什么数据」「当前统计结果」"
            "「目前筛选了哪些条件」等需要了解当前页面状态的请求。"
            "注意：此工具直接从前端传来的 context 读取，无需调用后端 API。"
        ),
        "parameters": {},
        "action_type": "read_display",
    },
    {
        "name": "update_frontend_filter",
        "description": (
            "更改前端控制台的全局数据筛选条件，触发前端所有图表自动刷新。"
            "适用场景：用户要求「筛选2023年的数据」「只看某企业」"
            "「切换到某个行业」「重置筛选」等更改查询范围的请求。"
            "执行后前端会自动按新条件重新加载所有图表数据。"
        ),
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
            "categories": {
                "type": "array",
                "description": "投诉分类列表（可选）",
            },
        },
        "action_type": "filter_data",
    },
    {
        "name": "run_time_series_analysis",
        "description": (
            "执行时序分析，获取指定时间范围内的投诉量时间序列数据，"
            "并在前端趋势图中展示。"
            "适用场景：用户询问「投诉趋势」「某段时间内的变化」"
            "「按月/周/天统计」「分析时间规律」等时序相关请求。"
        ),
        "parameters": {
            "start_date": {
                "type": "string",
                "description": "开始日期，格式 YYYY-MM-DD（可选）",
            },
            "end_date": {
                "type": "string",
                "description": "结束日期，格式 YYYY-MM-DD（可选）",
            },
            "period": {
                "type": "string",
                "description": "时间粒度：day（按天）/ week（按周）/ month（按月），默认 day",
            },
            "companies": {
                "type": "array",
                "description": "限定企业范围（可选）",
            },
        },
        "action_type": "update_trend",
    },
    {
        "name": "generate_report",
        "description": (
            "调用 AI 模型，基于当前统计数据编写专业的投诉分析报告，"
            "内容包括数据概况、趋势分析、重点企业分析、问题总结和监管建议。"
            "适用场景：用户要求「生成报告」「写分析报告」「总结数据」"
            "「出一份报告」等报告撰写请求。"
            "注意：优先使用前端传来的 context 数据，避免重复调用后端 API。"
        ),
        "parameters": {
            "start_date": {
                "type": "string",
                "description": "报告覆盖的开始日期（可选，默认使用当前筛选条件）",
            },
            "end_date": {
                "type": "string",
                "description": "报告覆盖的结束日期（可选，默认使用当前筛选条件）",
            },
        },
        "action_type": "show_report",
    },
    {
        "name": "generate_reply_suggestion",
        "description": (
            "调用 AI 模型，针对一条具体的市民投诉内容，生成专业的官方回复建议。"
            "适用场景：用户输入或粘贴了一段投诉文字，要求「帮我写回复」"
            "「生成回复建议」「怎么回复这条投诉」等辅助回复请求。"
        ),
        "parameters": {
            "complaint_content": {
                "type": "string",
                "description": "市民投诉的原文内容（必填）",
            },
        },
        "action_type": "show_reply",
    },
]

# ============================================================
# 工具名称 -> 描述映射（用于 prompt 构建）
# ============================================================
_TOOL_MAP: Dict[str, dict] = {t["name"]: t for t in TOOLS}


class AgentService:
    """对话Agent服务类"""

    def __init__(self, model_path: str = None):
        """
        初始化Agent服务

        Args:
            model_path: 模型路径，默认使用现有 vLLM 配置
        """
        self.ai_service = None
        self.model_path = model_path
        self._last_context: Optional[Dict[str, Any]] = None
        logger.info("AgentService 初始化完成")

    # ----------------------------------------------------------
    # 内部辅助方法
    # ----------------------------------------------------------

    def _get_ai_service(self):
        """懒加载 AI 服务（单例）"""
        if self.ai_service is None:
            from src.ai_service_vllm import get_vllm_ai_service

            self.ai_service = get_vllm_ai_service(model_path=self.model_path)
        return self.ai_service

    def _build_tools_prompt(self) -> str:
        """构建工具描述 prompt 段落"""
        lines = []
        for i, tool in enumerate(TOOLS, 1):
            params_lines = []
            for param_name, param_info in tool["parameters"].items():
                params_lines.append(f"    - {param_name}: {param_info['description']}")
            params_text = (
                "\n".join(params_lines)
                if params_lines
                else "    （无参数，直接从前端 context 读取）"
            )
            lines.append(
                f"{i}. **{tool['name']}**\n"
                f"   功能：{tool['description']}\n"
                f"   参数：\n{params_text}"
            )
        return "\n\n".join(lines)

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
                parts.append("**投诉最多企业（前5名）**：")
                for idx, company in enumerate(ranking[:5], 1):
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

        return "\n" + "\n".join(parts) if parts else ""

    # ----------------------------------------------------------
    # 核心公共方法
    # ----------------------------------------------------------

    def process_message(
        self, user_message: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息：意图识别 → 工具调用 → 构建响应

        Args:
            user_message: 用户输入
            context: 前端传来的当前状态（统计数据、筛选条件等）

        Returns:
            dict: { success, message, action, thinking, steps }
        """
        try:
            self._last_context = context

            # ── 1. 构建 system prompt ──────────────────────────
            tools_prompt = self._build_tools_prompt()
            context_info = self._extract_context_info(context)

            system_prompt = f"""你是一个专业的工商投诉数据分析助手，协助监管人员分析投诉数据、操控可视化仪表板。

## 可用工具
{tools_prompt}

## 当前仪表板状态
{context_info if context_info else "（暂无上下文数据）"}

## 意图识别规则
1. **明确执行步骤**：先分析用户完整意图，再列出需要依次执行的工具步骤。
2. **工具调用顺序**：
   - 若用户要求「筛选数据后再分析」，应先调用 `update_frontend_filter`，再调用 `run_time_series_analysis`。
   - 若用户要求「查看当前数据并生成报告」，应先调用 `read_frontend_display`，再调用 `generate_report`。
   - 单步任务（如仅筛选、仅查看、仅生成报告）只调用一个工具。
3. **参数解析**：
   - 年份（如「2023年」）→ start_date: "2023-01-01", end_date: "2023-12-31"
   - 「最近一个月」→ 基于今日 {datetime.now().strftime("%Y-%m-%d")} 计算
   - 企业名称 → companies 数组
4. **generate_reply_suggestion**：仅在用户明确提供投诉原文并要求起草回复时调用。
5. **read_frontend_display**：仅在用户询问当前显示内容时调用，无需任何参数。

## 响应格式（严格 JSON）
{{
  "thought": "对用户意图的分析，说明选择该工具的原因",
  "steps": [
    {{
      "step": 1,
      "tool": "工具名称",
      "parameters": {{"参数名": "参数值"}},
      "reason": "此步骤的作用"
    }}
  ],
  "message": "给用户的简洁友好回复（中文，不超过50字）"
}}

若只需一个工具，steps 列表只有一项。
若无法理解意图，返回：
{{
  "thought": "无法确定意图",
  "steps": [],
  "message": "抱歉，我没有理解您的需求，请问您是想筛选数据、查看趋势、生成报告，还是需要投诉回复建议？"
}}
"""

            # ── 2. 调用 AI 模型识别意图 ────────────────────────
            ai_service = self._get_ai_service()
            response = ai_service.generate_response(
                user_input=user_message,
                system_prompt=system_prompt,
                temperature=0.2,  # 低温度，提升结构化输出稳定性
                max_tokens=1024,
                stream=False,
            )

            if isinstance(response, dict):
                ai_reply = response.get("reply", "")
                thinking = response.get("thinking")
            else:
                ai_reply = str(response)
                thinking = None

            logger.info(f"AI 原始响应: {ai_reply}")

            # ── 3. 解析 JSON ───────────────────────────────────
            intent = self._parse_intent_json(ai_reply)
            if intent is None:
                return {
                    "success": True,
                    "message": ai_reply if ai_reply else "抱歉，我没有理解您的需求。",
                    "action": None,
                    "thinking": thinking,
                }

            steps: List[dict] = intent.get("steps", [])

            # ── 4. 无工具调用 ──────────────────────────────────
            if not steps:
                return {
                    "success": True,
                    "message": intent.get(
                        "message",
                    ),
                    "action": None,
                    "thinking": intent.get("thought"),
                }

            # ── 5. 顺序执行工具步骤 ────────────────────────────
            results = []
            last_action = None

            for step_info in steps:
                tool_name = step_info.get("tool")
                parameters = step_info.get("parameters", {})

                if not tool_name or tool_name not in _TOOL_MAP:
                    logger.warning(f"未知工具: {tool_name}，跳过此步骤")
                    continue

                logger.info(
                    f"执行步骤 {step_info.get('step')}: {tool_name}({parameters})"
                )
                tool_result = self._call_tool(tool_name, parameters)

                if tool_result["success"]:
                    tool_config = _TOOL_MAP[tool_name]
                    last_action = {
                        "type": tool_config["action_type"],
                        "data": tool_result["data"],
                        "tool": tool_name,
                        "parameters": parameters,
                    }
                    results.append(
                        {
                            "step": step_info.get("step"),
                            "tool": tool_name,
                            "success": True,
                            "action": last_action,
                        }
                    )
                else:
                    error_msg = tool_result.get("error", "未知错误")
                    logger.error(f"工具 {tool_name} 执行失败: {error_msg}")
                    results.append(
                        {
                            "step": step_info.get("step"),
                            "tool": tool_name,
                            "success": False,
                            "error": error_msg,
                        }
                    )

            # ── 6. 构建最终响应 ────────────────────────────────
            all_success = all(r["success"] for r in results)

            return {
                "success": all_success,
                "message": intent.get("message", "已为您执行操作"),
                "action": last_action,  # 前端主要使用最后一步的 action
                "steps": results,  # 完整步骤结果（供前端按需使用）
                "thinking": intent.get("thought") or thinking,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"处理消息时出错: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"抱歉，处理您的请求时出现错误：{str(e)}",
                "action": None,
            }

    def _parse_intent_json(self, ai_reply: str) -> Optional[dict]:
        """从 AI 响应中提取并解析 JSON 意图"""
        json_str = ai_reply.strip()
        # 去除可能的 markdown 代码块
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}，原始内容: {json_str[:200]}")
            return None

    # ----------------------------------------------------------
    # 工具实现
    # ----------------------------------------------------------

    def _call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用具体工具

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            dict: { success, data } 或 { success, error }
        """
        try:
            if tool_name == "read_frontend_display":
                return self._tool_read_frontend_display()

            elif tool_name == "update_frontend_filter":
                return self._tool_update_frontend_filter(parameters)

            elif tool_name == "run_time_series_analysis":
                return self._tool_run_time_series_analysis(parameters)

            elif tool_name == "generate_report":
                return self._tool_generate_report(parameters)

            elif tool_name == "generate_reply_suggestion":
                return self._tool_generate_reply_suggestion(parameters)

            else:
                return {"success": False, "error": f"未知工具: {tool_name}"}

        except Exception as e:
            logger.error(f"调用工具 {tool_name} 时出错: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _tool_read_frontend_display(self) -> Dict[str, Any]:
        """
        工具1：读取前端当前显示的内容
        直接从 _last_context 中提取，无需调用后端 API
        """
        context = self._last_context or {}
        stats = context.get("currentStats", {})
        filters = context.get("filters", {})

        display_data = {
            "stats": {
                "total_complaints": stats.get("total_complaints", 0),
                "companies_count": stats.get("companies_count", 0),
                "industries_count": stats.get("industries_count", 0),
                "repeat_companies_count": stats.get("repeat_companies_count", 0),
                "company_ranking": stats.get("company_ranking", []),
            },
            "filters": {
                "start_date": filters.get("startDate"),
                "end_date": filters.get("endDate"),
                "selected_companies": filters.get("selectedCompanies", []),
                "selected_industries": filters.get("selectedIndustries", []),
            },
            "has_data": stats.get("total_complaints", 0) > 0,
        }

        logger.info("read_frontend_display: 从 context 读取前端显示数据")
        return {"success": True, "data": display_data}

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

    def _tool_run_time_series_analysis(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        工具3：执行时序分析，获取投诉趋势数据
        """
        from src.models import Model

        model = Model()

        data = model.get_trend_data(
            start_date=parameters.get("start_date"),
            end_date=parameters.get("end_date"),
            period=parameters.get("period", "day"),
            companies=parameters.get("companies"),
            industries=parameters.get("industries"),
        )
        logger.info(
            f"run_time_series_analysis: 获取趋势数据，period={parameters.get('period', 'day')}"
        )
        return {"success": True, "data": data}

    def _tool_generate_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        工具4：生成投诉分析报告
        优先使用前端 context 中的统计数据，避免重复调用 API
        """
        from src.ai_service_vllm import get_vllm_ai_service

        stats = None
        use_context = False
        time_range_str = f"{parameters.get('start_date', '开始')} 至 {parameters.get('end_date', '结束')}"

        # 优先从 context 获取统计数据
        if self._last_context:
            context_stats = self._last_context.get("currentStats", {})
            if context_stats.get("total_complaints", 0) > 0:
                stats = {
                    "total_complaints": context_stats.get("total_complaints", 0),
                    "companies_count": context_stats.get("companies_count", 0),
                    "industries_count": context_stats.get("industries_count", 0),
                    "repeat_companies_count": context_stats.get(
                        "repeat_companies_count", 0
                    ),
                    "company_ranking": context_stats.get("company_ranking", []),
                }
                use_context = True

                # 时间范围优先用 context filters
                filters = self._last_context.get("filters", {})
                if filters.get("startDate"):
                    time_range_str = f"{filters.get('startDate')} 至 {filters.get('endDate', '结束')}"

                logger.info(
                    "generate_report: 使用 context 统计数据（避免重复 API 调用）"
                )

        # context 无数据时回退到 API
        if not stats:
            from src.models import Model

            model = Model()
            stats = model.get_dashboard_stats(
                start_date=parameters.get("start_date"),
                end_date=parameters.get("end_date"),
            )
            logger.info("generate_report: 从后端 API 获取统计数据")

        # 构建报告数据
        top_companies_lines = []
        for idx, company in enumerate(stats.get("company_ranking", [])[:10], 1):
            top_companies_lines.append(
                f"{idx}. {company.get('name', '未知')}（{company.get('count', 0)} 条）"
            )

        report_data = {
            "time_range": time_range_str,
            "total_complaints": stats.get("total_complaints", 0),
            "total_companies": stats.get("companies_count", 0),
            "total_industries": stats.get("industries_count", 0),
            "repeat_companies": stats.get("repeat_companies_count", 0),
            "top_companies": "\n".join(top_companies_lines)
            if top_companies_lines
            else "暂无企业数据",
            "trend_summary": f"总投诉量为 {stats.get('total_complaints', 0)} 条",
        }

        ai_service = get_vllm_ai_service()
        report = ai_service.generate_report(report_data, stream=False)

        return {
            "success": True,
            "data": {
                "report": report,
                "stats": stats,
                "use_context": use_context,
            },
        }

    def _tool_generate_reply_suggestion(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        工具5：生成投诉辅助回复
        """
        complaint_content = parameters.get("complaint_content", "").strip()
        if not complaint_content:
            return {"success": False, "error": "缺少投诉内容参数 complaint_content"}

        from src.ai_service_vllm import get_vllm_ai_service

        ai_service = get_vllm_ai_service()
        reply = ai_service.generate_reply_suggestion(complaint_content, stream=False)

        logger.info("generate_reply_suggestion: 生成投诉回复建议完成")
        return {
            "success": True,
            "data": {
                "reply": reply,
                "complaint_content": complaint_content,
            },
        }


# ============================================================
# 全局单例
# ============================================================
_agent_service_instance: Optional[AgentService] = None


def get_agent_service(model_path: str = None) -> AgentService:
    """
    获取 AgentService 单例

    Args:
        model_path: 模型路径（可选）

    Returns:
        AgentService 实例
    """
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService(model_path=model_path)
    return _agent_service_instance
