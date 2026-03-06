#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话Agent服务模块
支持自然语言意图识别和工具调用

核心工具（4个）：
1. read_frontend_display   - 读取前端当前显示的内容
2. update_frontend_filter  - 更改前端控制台的筛选条件（日期范围、企业、行业等）
3. generate_report         - 编写投诉分析报告（调用 Deepseek API）
4. generate_reply_suggestion - 生成投诉辅助回复（调用本地 vLLM）
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

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
        max_tokens: int = 1024,
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
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
            "调用本地大模型，针对一条具体的市民投诉内容，生成专业的官方回复建议。"
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
            model_path: 模型路径，给本地 vLLM 使用（仅用于回复建议）
        """
        self.ai_service = None
        self.model_path = model_path
        self._last_context: Optional[Dict[str, Any]] = None
        logger.info("AgentService 初始化完成 (Deepseek 集成版)")

    # ----------------------------------------------------------
    # 内部辅助方法
    # ----------------------------------------------------------

    def _get_deepseek_service(self):
        """获取 Deepseek API 服务实例"""
        return get_deepseek_service()

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

    # ----------------------------------------------------------
    # 核心公共方法
    # ----------------------------------------------------------

    def process_message(
        self, user_message: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息：意图识别 → 工具调用 → 构建响应
        使用 Deepseek API 进行意图识别。

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
   - 若用户要求「查看当前数据并生成报告」，应先调用 `read_frontend_display`，再调用 `generate_report`。
   - 单步任务（如仅筛选、仅查看、仅生成报告）只调用一个工具。
3. **参数解析**：
   - 年份（如「2023年」）→ start_date: "2023-01-01", end_date: "2023-12-31"
   - 「最近一个月」→ 基于今日 {datetime.now().strftime("%Y-%m-%d")} 计算
   - 企业名称 → companies 数组
4. **generate_reply_suggestion**：仅在用户明确提供投诉原文并要求起草回复时调用。
5. **read_frontend_display**：仅在用户询问当前显示内容时调用，无需任何参数。

## 响应格式（严格返回合法的 JSON 对象，不要包含多余的格式化符号或 markdown 代码块）
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

            # ── 2. 调用 Deepseek API 识别意图 ────────────────────────
            deepseek = self._get_deepseek_service()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            ai_reply = deepseek.chat(messages, temperature=0.1, max_tokens=1024)
            logger.info(f"Deepseek AI 原始响应: {ai_reply}")

            # ── 3. 解析 JSON ───────────────────────────────────
            intent = self._parse_intent_json(ai_reply)
            if intent is None:
                return {
                    "success": True,
                    "message": ai_reply if ai_reply else "抱歉，我没有理解您的需求。",
                    "action": None,
                    "thinking": None,
                }

            steps: List[dict] = intent.get("steps", [])

            # ── 4. 无工具调用 ──────────────────────────────────
            if not steps:
                return {
                    "success": True,
                    "message": intent.get(
                        "message", "抱歉，没有识别到具体的工具操作。"
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
                "thinking": intent.get("thought"),
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
        elif json_str.startswith("```"):
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
        """调用具体工具"""
        try:
            if tool_name == "read_frontend_display":
                return self._tool_read_frontend_display()

            elif tool_name == "update_frontend_filter":
                return self._tool_update_frontend_filter(parameters)

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

    def _tool_generate_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        工具3：生成投诉分析报告 (现在调用 Deepseek API)
        """
        stats = None
        use_context = False
        time_range_str = f"{parameters.get('start_date', '开始')} 至 {parameters.get('end_date', '结束')}"
        context = self._last_context or {}

        # 优先从 context 获取统计数据
        if context:
            context_stats = context.get("currentStats", {})
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
                filters = context.get("filters", {})
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

        # ── 构建 top-10 企业文本 ───────────────────────────────────────
        top_companies_lines = []
        for idx, company in enumerate(stats.get("company_ranking", [])[:10], 1):
            top_companies_lines.append(
                f"{idx}. {company.get('name', '未知')}（{company.get('count', 0)} 条）"
            )

        # ── 构建趋势摘要文本 ──────────────────────────────────────────
        trend = context.get("trendData", {})
        trend_mode = trend.get("mode", "empty")
        trend_summary = f"总投诉量为 {stats.get('total_complaints', 0)} 条"
        if trend_mode == "daily" and trend.get("data"):
            counts = [d["count"] for d in trend["data"] if "count" in d]
            if counts:
                trend_summary = (
                    f"总投诉量 {stats.get('total_complaints', 0)} 条；"
                    f"按{context.get('trendPeriod', '天')}统计共 {len(counts)} 个时间点，"
                    f"峰值 {max(counts)} 条，谷值 {min(counts)} 条，均值 {sum(counts) / len(counts):.1f} 条"
                )
        elif trend_mode == "aggregated":
            monthly = trend.get("monthly", [])
            if monthly:
                counts = [d["count"] for d in monthly]
                monthly_str = "、".join(
                    f"{d['time']}({d['count']}条)" for d in monthly[-6:]
                )
                trend_summary = (
                    f"总投诉量 {stats.get('total_complaints', 0)} 条；"
                    f"按月统计共 {len(monthly)} 个月，峰值 {max(counts)} 条，谷值 {min(counts)} 条；"
                    f"近6个月：{monthly_str}"
                )

        # ── 构建旭日图摘要文本 ────────────────────────────────────────
        category_summary = "暂无分类数据"
        sunburst = context.get("sunburstSummary")
        if sunburst:
            lines = []
            cat3 = sunburst.get("category_top3", [])
            if cat3:
                lines.append(
                    "问题分类 Top3："
                    + "、".join(
                        f"{c['name']}（占比{c['percent']}%，共{c['count']}条）"
                        for c in cat3
                    )
                )
            issue3 = sunburst.get("issue_top3", [])
            if issue3:
                lines.append(
                    "涉及问题 Top3："
                    + "、".join(
                        f"{c['name']}（占比{c['percent']}%，共{c['count']}条）"
                        for c in issue3
                    )
                )
            if lines:
                category_summary = "\n".join(lines)

        # ── 构建散点图摘要文本 ────────────────────────────────────────
        scatter_summary = "暂无散点图数据"
        scatter = context.get("scatterSummary")
        if scatter:
            total_co = scatter.get("total_companies", 0)
            warn_co = scatter.get("warning_companies", 0)
            top10 = scatter.get("top10_companies", [])
            top10_lines = [
                f"  {i + 1}. {c['name']}{'（预警）' if c.get('is_warning') else ''}："
                f"投诉 {c['count']} 条，问题类型 {c['diversity']} 种"
                for i, c in enumerate(top10)
            ]
            scatter_summary = (
                f"企业总数 {total_co} 家，其中预警企业 {warn_co} 家；\n"
                + ("\n".join(top10_lines) if top10_lines else "暂无企业数据")
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
            "trend_summary": trend_summary,
            "category_summary": category_summary,
            "scatter_summary": scatter_summary,
        }

        # 调用 Deepseek API 生成报告
        system_prompt = """你是一位专业的数据分析专家，擅长分析工商投诉数据并撰写详细的分析报告。
请根据提供的数据，生成一份专业、清晰、有洞察力的投诉分析报告。
报告应包含：数据概况、趋势分析、问题总结和监管建议。"""

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

请生成一份包含以下部分的专业报告（使用 Markdown 格式）：
1. 摘要（简明扼要总结关键发现）
2. 数据概况（详细说明数据范围和基本情况）
3. 投诉趋势分析（分析投诉量的变化趋势和规律）
4. 投诉分类分析（基于旭日图数据分析主要问题类型分布）
5. 重点企业分析（结合散点图风险分布，分析投诉最多和高风险企业）
6. 监管建议（提出针对性的监管措施和改进方向）

要求：语言专业、数据准确、分析深入、建议可行。"""

        deepseek = self._get_deepseek_service()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        logger.info("generate_report: 调用 Deepseek 生报告...")
        report = deepseek.chat(messages, temperature=0.7, max_tokens=2048)
        logger.info("generate_report: Deepseek 报告生成完成")

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


# ============================================================
# 全局单例
# ============================================================
_agent_service_instance: Optional[AgentService] = None


def get_agent_service(model_path: str = None) -> AgentService:
    """获取 AgentService 单例"""
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService(model_path=model_path)
    return _agent_service_instance
