#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话Agent服务模块
支持自然语言意图识别和工具调用
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 定义可调用的工具
TOOLS = [
    {
        "name": "get_dashboard_stats",
        "description": "获取仪表板统计数据，包括总投诉量、企业数量、行业数量等关键指标。适用于用户询问统计信息、数据概览时调用。",
        "parameters": {
            "start_date": {
                "type": "string",
                "description": "开始日期，格式YYYY-MM-DD（可选）",
            },
            "end_date": {
                "type": "string",
                "description": "结束日期，格式YYYY-MM-DD（可选）",
            },
            "companies": {"type": "array", "description": "企业名称列表（可选）"},
            "industries": {"type": "array", "description": "行业列表（可选）"},
        },
        "action_type": "update_stats",
    },
    {
        "name": "get_trend_data",
        "description": "获取投诉趋势数据，显示时间序列的投诉量变化。适用于用户询问趋势、变化、走势时调用。",
        "parameters": {
            "start_date": {"type": "string", "description": "开始日期（可选）"},
            "end_date": {"type": "string", "description": "结束日期（可选）"},
            "period": {
                "type": "string",
                "description": "时间粒度：day/week/month，默认day",
            },
            "companies": {"type": "array", "description": "企业名称列表（可选）"},
        },
        "action_type": "update_trend",
    },
    {
        "name": "get_company_details",
        "description": "获取指定企业的投诉详情列表，包括投诉时间、问题描述、回复等。适用于用户询问某个具体企业的投诉情况。",
        "parameters": {
            "company_name": {"type": "string", "description": "企业名称（必填）"},
            "start_date": {"type": "string", "description": "开始日期（可选）"},
            "end_date": {"type": "string", "description": "结束日期（可选）"},
        },
        "action_type": "show_company",
    },
    {
        "name": "get_sunburst_data",
        "description": "获取旭日图数据，展示分类或问题的层级结构分布。适用于用户想看分类结构、层级关系时调用。",
        "parameters": {
            "start_date": {"type": "string", "description": "开始日期（可选）"},
            "end_date": {"type": "string", "description": "结束日期（可选）"},
            "chart_type": {
                "type": "string",
                "description": "图表类型：category（分类）或issue（问题），默认category",
            },
        },
        "action_type": "switch_chart_sunburst",
    },
    {
        "name": "get_quadrant_data",
        "description": "获取四象限散点图数据，展示企业的投诉量和问题多样性分布。适用于用户想看散点图、象限图、企业分布时调用。",
        "parameters": {
            "start_date": {"type": "string", "description": "开始日期（可选）"},
            "end_date": {"type": "string", "description": "结束日期（可选）"},
        },
        "action_type": "switch_chart_quadrant",
    },
    {
        "name": "generate_report",
        "description": "使用AI生成投诉分析报告，包含数据概况、趋势分析、问题总结和监管建议。适用于用户要求生成报告、分析总结时调用。",
        "parameters": {
            "start_date": {"type": "string", "description": "开始日期（可选）"},
            "end_date": {"type": "string", "description": "结束日期（可选）"},
        },
        "action_type": "show_report",
    },
    {
        "name": "rag_query",
        "description": "检索法律法规知识库并生成回答。适用于用户咨询法律问题、法规条款时调用。",
        "parameters": {
            "question": {"type": "string", "description": "法律问题（必填）"},
            "top_k": {"type": "integer", "description": "检索文档数量，默认3"},
        },
        "action_type": "show_rag",
    },
    {
        "name": "filter_data",
        "description": "设置全局数据筛选条件，影响所有图表和统计。适用于用户要求筛选、过滤特定条件的数据。",
        "parameters": {
            "start_date": {"type": "string", "description": "开始日期（可选）"},
            "end_date": {"type": "string", "description": "结束日期（可选）"},
            "companies": {"type": "array", "description": "企业名称列表（可选）"},
            "industries": {"type": "array", "description": "行业列表（可选）"},
            "categories": {"type": "array", "description": "分类列表（可选）"},
        },
        "action_type": "filter_data",
    },
]


class AgentService:
    """对话Agent服务类"""

    def __init__(self, model_path: str = None):
        """
        初始化Agent服务

        Args:
            model_path: 模型路径，默认使用现有vLLM配置
        """
        self.ai_service = None
        self.model_path = model_path
        logger.info("AgentService初始化完成")

    def _get_ai_service(self):
        """懒加载AI服务"""
        if self.ai_service is None:
            from src.ai_service_vllm import get_vllm_ai_service

            self.ai_service = get_vllm_ai_service(model_path=self.model_path)
        return self.ai_service

    def _build_tools_prompt(self) -> str:
        """构建工具描述的prompt"""
        tools_desc = []
        for i, tool in enumerate(TOOLS, 1):
            params_desc = []
            for param_name, param_info in tool["parameters"].items():
                params_desc.append(f"  - {param_name}: {param_info['description']}")

            tool_desc = (
                f"{i}. {tool['name']}\n   功能: {tool['description']}\n   参数:\n"
                + "\n".join(params_desc)
            )
            tools_desc.append(tool_desc)

        return "\n\n".join(tools_desc)

    def process_message(
        self, user_message: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息

        Args:
            user_message: 用户输入的消息
            context: 对话上下文（可选，包含当前筛选条件等）

        Returns:
            dict: 包含action、data、message的响应
        """
        try:
            # 保存context供工具调用使用
            self._last_context = context

            # 1. 构建系统提示词
            tools_prompt = self._build_tools_prompt()

            # 提取上下文中的统计数据
            context_info = ""
            if context:
                if "currentStats" in context:
                    stats = context["currentStats"]
                    context_info += "\n\n**当前页面统计数据**：\n"
                    context_info += (
                        f"- 投诉总量：{stats.get('total_complaints', 0)}条\n"
                    )
                    context_info += f"- 涉及企业：{stats.get('companies_count', 0)}家\n"
                    context_info += (
                        f"- 涉及行业：{stats.get('industries_count', 0)}个\n"
                    )
                    context_info += (
                        f"- 预警企业：{stats.get('repeat_companies_count', 0)}家\n"
                    )

                    if stats.get("company_ranking"):
                        context_info += "\n**投诉最多的企业（前5名）**：\n"
                        for i, company in enumerate(stats["company_ranking"][:5], 1):
                            context_info += f"{i}. {company.get('name', '未知')}：{company.get('count', 0)}条\n"

                if "filters" in context:
                    filters = context["filters"]
                    if filters.get("startDate") or filters.get("endDate"):
                        context_info += f"\n**数据时间范围**：{filters.get('startDate', '开始')} 至 {filters.get('endDate', '结束')}\n"
                    if filters.get("selectedCompanies"):
                        companies_str = ", ".join(filters["selectedCompanies"][:3])
                        if len(filters["selectedCompanies"]) > 3:
                            companies_str += "等"
                        context_info += f"**已筛选企业**：{companies_str}\n"

            system_prompt = f"""你是一个智能数据分析助手，可以帮助用户查询和分析工商投诉数据。

你可以调用以下工具来完成任务：

{tools_prompt}

**重要规则**：
1. 仔细分析用户的意图，选择最合适的工具
2. 如果用户提到具体的时间范围（如"2024年"、"最近一个月"），要解析成start_date和end_date参数
3. 如果用户提到具体的企业名称，要提取到companies参数中
4. **当用户要求生成报告时，如果上下文中已有完整的统计数据，优先使用这些数据而非重新调用API**
5. 必须返回JSON格式的响应，格式如下：
{{
  "thought": "对用户意图的分析",
  "tool": "要调用的工具名称",
  "parameters": {{"参数名": "参数值"}},
  "message": "给用户的友好回复"
}}

6. 如果无法理解用户意图或需要更多信息，则返回：
{{
  "thought": "无法确定意图",
  "tool": null,
  "parameters": {{}},
  "message": "抱歉，我没有理解您的需求，请问您想要..."
}}
{context_info}
"""

            # 2. 调用AI模型理解意图
            ai_service = self._get_ai_service()

            response = ai_service.generate_response(
                user_input=user_message,
                system_prompt=system_prompt,
                temperature=0.3,  # 较低温度，提高准确性
                max_tokens=512,
                stream=False,
            )

            # 3. 解析AI响应
            if isinstance(response, dict):
                ai_reply = response.get("reply", "")
                thinking = response.get("thinking")
            else:
                ai_reply = response
                thinking = None

            logger.info(f"AI原始响应: {ai_reply}")

            # 尝试解析JSON
            try:
                # 提取JSON部分（去除可能的markdown代码块）
                json_str = ai_reply.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:]
                if json_str.startswith("```"):
                    json_str = json_str[3:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
                json_str = json_str.strip()

                intent = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败: {e}，使用默认响应")
                return {
                    "success": True,
                    "message": ai_reply if ai_reply else "抱歉，我没有理解您的需求。",
                    "action": None,
                    "thinking": thinking,
                }

            # 4. 如果没有工具调用，直接返回消息
            if not intent.get("tool"):
                return {
                    "success": True,
                    "message": intent.get(
                        "message", "我可以帮您查询投诉数据、生成分析报告等。"
                    ),
                    "action": None,
                    "thinking": intent.get("thought"),
                }

            # 5. 调用相应的工具
            tool_name = intent["tool"]
            parameters = intent.get("parameters", {})

            action_result = self._call_tool(tool_name, parameters)

            # 6. 构建响应
            if action_result["success"]:
                # 找到工具配置以获取action_type
                tool_config = next((t for t in TOOLS if t["name"] == tool_name), None)
                action_type = tool_config["action_type"] if tool_config else "unknown"

                return {
                    "success": True,
                    "message": intent.get("message", "已为您获取数据"),
                    "action": {
                        "type": action_type,
                        "data": action_result["data"],
                        "tool": tool_name,
                        "parameters": parameters,
                    },
                    "thinking": intent.get("thought"),
                    "generated_at": datetime.now().isoformat(),
                }
            else:
                return {
                    "success": False,
                    "message": f"调用工具失败: {action_result.get('error', '未知错误')}",
                    "action": None,
                    "thinking": intent.get("thought"),
                }

        except Exception as e:
            logger.error(f"处理消息时出错: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"抱歉，处理您的请求时出现错误：{str(e)}",
                "action": None,
            }

    def _call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用后端API工具

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            dict: 工具执行结果
        """
        try:
            # 这里使用内部调用方式，直接调用model的方法
            from src.models import Model

            model = Model()

            # 根据工具名称调用相应的方法
            if tool_name == "get_dashboard_stats":
                data = model.get_dashboard_stats(
                    start_date=parameters.get("start_date"),
                    end_date=parameters.get("end_date"),
                    companies=parameters.get("companies"),
                    industries=parameters.get("industries"),
                )
                return {"success": True, "data": data}

            elif tool_name == "get_trend_data":
                data = model.get_trend_data(
                    start_date=parameters.get("start_date"),
                    end_date=parameters.get("end_date"),
                    period=parameters.get("period", "day"),
                    companies=parameters.get("companies"),
                    industries=parameters.get("industries"),
                )
                return {"success": True, "data": data}

            elif tool_name == "get_company_details":
                company_name = parameters.get("company_name")
                if not company_name:
                    return {"success": False, "error": "缺少企业名称参数"}

                data = model.get_company_details(
                    company_name=company_name,
                    start_date=parameters.get("start_date"),
                    end_date=parameters.get("end_date"),
                )
                return {"success": True, "data": data}

            elif tool_name == "get_sunburst_data":
                data = model.get_sunburst_data(
                    start_date=parameters.get("start_date"),
                    end_date=parameters.get("end_date"),
                    chart_type=parameters.get("chart_type", "category"),
                )
                return {"success": True, "data": data}

            elif tool_name == "get_quadrant_data":
                data = model.get_quadrant_data(
                    start_date=parameters.get("start_date"),
                    end_date=parameters.get("end_date"),
                )
                return {"success": True, "data": data}

            elif tool_name == "generate_report":
                # 调用AI报告生成
                # 优先尝试从context获取统计数据，避免重复API调用
                stats = None
                use_context = False

                if hasattr(self, "_last_context") and self._last_context:
                    context_stats = self._last_context.get("currentStats")
                    if context_stats and context_stats.get("total_complaints", 0) > 0:
                        # 使用context中的统计数据
                        stats = {
                            "total_complaints": context_stats.get(
                                "total_complaints", 0
                            ),
                            "companies_count": context_stats.get("companies_count", 0),
                            "industries_count": context_stats.get(
                                "industries_count", 0
                            ),
                            "repeat_companies_count": context_stats.get(
                                "repeat_companies_count", 0
                            ),
                            "company_ranking": context_stats.get("company_ranking", []),
                        }
                        use_context = True
                        logger.info(
                            "使用context中的统计数据生成报告（避免重复API调用）"
                        )

                # 如果context中没有数据，则调用API获取
                if not stats:
                    stats = model.get_dashboard_stats(
                        start_date=parameters.get("start_date"),
                        end_date=parameters.get("end_date"),
                    )
                    logger.info("从API获取统计数据生成报告")

                from src.ai_service_vllm import get_vllm_ai_service

                ai_service = get_vllm_ai_service()

                # 提取时间范围（优先从context的filters）
                time_range = f"{parameters.get('start_date', '开始')} 至 {parameters.get('end_date', '结束')}"
                if use_context and hasattr(self, "_last_context"):
                    filters = self._last_context.get("filters", {})
                    if filters.get("startDate"):
                        time_range = f"{filters.get('startDate')} 至 {filters.get('endDate', '结束')}"

                report_data = {
                    "time_range": time_range,
                    "total_complaints": stats.get("total_complaints", 0),
                    "total_companies": stats.get("companies_count", 0),
                    "total_industries": stats.get("industries_count", 0),
                    "repeat_companies": stats.get("repeat_companies_count", 0),
                }

                # 添加企业排行信息
                if stats.get("company_ranking"):
                    top_companies_list = []
                    for i, company in enumerate(stats["company_ranking"][:10], 1):
                        top_companies_list.append(
                            f"{i}. {company.get('name', '未知')}（{company.get('count', 0)}条）"
                        )
                    report_data["top_companies"] = "\n".join(top_companies_list)
                else:
                    report_data["top_companies"] = "暂无企业数据"

                report_data["trend_summary"] = (
                    f"总投诉量为{stats.get('total_complaints', 0)}条"
                )

                report = ai_service.generate_report(report_data, stream=False)

                return {
                    "success": True,
                    "data": {
                        "report": report,
                        "stats": stats,
                        "use_context": use_context,
                    },
                }

            elif tool_name == "rag_query":
                question = parameters.get("question")
                if not question:
                    return {"success": False, "error": "缺少问题参数"}

                from src.rag_service import get_rag_service

                rag_service = get_rag_service()

                results = rag_service.search(
                    query=question, top_k=parameters.get("top_k", 3)
                )

                return {
                    "success": True,
                    "data": {"results": results, "question": question},
                }

            elif tool_name == "filter_data":
                # 筛选操作返回筛选条件本身
                return {"success": True, "data": parameters}

            else:
                return {"success": False, "error": f"未知工具: {tool_name}"}

        except Exception as e:
            logger.error(f"调用工具 {tool_name} 时出错: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# 全局Agent服务实例
_agent_service_instance: Optional[AgentService] = None


def get_agent_service(model_path: str = None) -> AgentService:
    """
    获取Agent服务实例（单例模式）

    Args:
        model_path: 模型路径（可选）

    Returns:
        AgentService: Agent服务实例
    """
    global _agent_service_instance

    if _agent_service_instance is None:
        _agent_service_instance = AgentService(model_path=model_path)

    return _agent_service_instance
