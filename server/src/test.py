def process_message(
    self, user_message: str, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    基于多轮对话机制优化流程：
    1. 意图识别与子任务规划（Round 1）
    2. 顺序执行工具：更新筛选 -> 读取前端 -> 执行生成
    3. 针对分析报告，直接在工具调用阶段要求输出纯段落文本
    4. 本地大模型回复直接透传
    """
    try:
        self._last_context = context
        deepseek = self._get_deepseek_service()

        # 初始化对话历史 (在实际生产中，建议根据 sessionId 持久化此 messages 列表)
        messages = []

        # ── Round 1: 意图识别与规划 ──────────────────────────
        tools_prompt = self._build_tools_prompt()
        context_info = self._extract_context_info(context)

        system_prompt = f"""你是一个政务投诉分析专家。请分析用户意图并拆解任务。
## 可用工具
{tools_prompt}
## 当前状态
{context_info}

## 强制逻辑顺序：
1. 若需分析特定范围数据：1. update_frontend_filter -> 2. read_frontend_display -> 3. generate_report。
2. 若仅生成投诉回复：直接调用 generate_reply_suggestion。

## 响应格式 (JSON)
{{
  "thought": "分析逻辑",
  "steps": [{{ "step": 1, "tool": "工具名", "parameters": {{}} }}],
  "message": "执行前的初步告知"
}}
"""
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        # 调用 Deepseek 进行规划
        planner_res = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},  # 强制 JSON 输出
        )

        # 将模型回复加入历史 (Round 1 完成)
        planner_message_obj = planner_res.choices[0].message
        messages.append(planner_message_obj)

        intent = json.loads(planner_message_obj.content)
        steps = intent.get("steps", [])

        # ── 顺序执行工具流水线 ────────────────────────────
        last_action = None
        final_message = ""

        for step in steps:
            tool_name = step.get("tool")
            params = step.get("parameters", {})

            # 优化点：在生成报告请求中，直接注入格式要求
            if tool_name == "generate_report":
                params["format_instruction"] = (
                    "请直接生成专业分析段落，禁止使用 Markdown 标题、加粗或列表符号。"
                )

            res = self._call_tool(tool_name, params)

            if res["success"]:
                # 更新前端动作
                last_action = {
                    "type": _TOOL_MAP[tool_name]["action_type"],
                    "data": res["data"],
                    "tool": tool_name,
                }

                # 结果处理
                if tool_name == "generate_reply_suggestion":
                    # 本地模型直出，跳过后续
                    final_message = res["data"].get("reply")
                    break
                elif tool_name == "generate_report":
                    # 直接获取生成的段落报告
                    final_message = res["data"].get("report")

        # 如果没有通过 generate_report 获取到 message（例如仅执行了筛选）
        if not final_message:
            final_message = intent.get("message", "操作已完成。")

        return {
            "success": True,
            "message": final_message,
            "action": last_action,
            "thinking": intent.get("thought"),
            "history_count": len(messages),  # 追踪对话轮数
        }

    except Exception as e:
        logger.error(f"处理流程出错: {e}", exc_info=True)
        return {"success": False, "message": f"抱歉，处理失败: {str(e)}"}
