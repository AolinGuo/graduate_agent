import json
import re


def remove_duplicate_content(user_content, assistant_content):
    """
    精确删除assistant回复中开头重复的user内容

    Args:
        user_content: 用户投诉内容
        assistant_content: 助理回复内容

    Returns:
        str: 清理后的回复内容
    """
    if not user_content or not assistant_content:
        return assistant_content

    user_clean = user_content.strip()
    assistant_clean = assistant_content.strip()

    # 提取user内容的主要部分（去掉最后的"注："部分）
    user_main_content = re.split(r"注：|备注：", user_clean)[0].strip()

    # 检查assistant是否以user主要内容开头
    if assistant_clean.startswith(user_main_content):
        remaining = assistant_clean[len(user_main_content) :].lstrip("，。.,;；")
        return remaining if remaining else assistant_clean

    return assistant_clean


def clean_structured_complaint_data(input_file, output_file):
    """
    专门处理结构化投诉数据的清理和转换
    """
    # 读取原始数据
    with open(input_file, "r", encoding="utf-8") as f:
        original_data = json.load(f)

    # 专业系统提示词
    system_prompt = """你是一名专业的政府投诉处理AI助手，专门负责生成标准化的投诉处理回复。

你的职责包括：
1. 准确理解市民的投诉内容
2. 严格按照政府工作流程和法律法规进行回复
3. 使用正式、规范的公务语言

请根据市民投诉内容，生成符合上述要求的专业回复。"""

    cleaned_data = []
    processed_count = 0
    cleaned_count = 0

    for item in original_data:
        try:
            # 提取字段
            instruction = item.get("instruction", "")
            user_input = item.get("input", "")
            original_output = item.get("output", "")

            # 将input内容合并到instruction中，因为原数据中instruction都是空的
            # 所以直接使用input作为instruction
            if user_input:
                user_query = user_input
            elif instruction:
                user_query = instruction
            else:
                user_query = ""

            # 清理重复内容
            cleaned_output = remove_duplicate_content(user_query, original_output)

            if cleaned_output != original_output:
                cleaned_count += 1
                print(f"✅ 已清理重复内容: {cleaned_output[:100]}...")

            # 构建标准格式 - 使用instruction/input/output/system格式
            training_example = {
                "instruction": user_query.strip(),
                "input": "",  # 用户输入（选填），这里设为空
                "output": cleaned_output.strip(),
                "system": system_prompt,
            }

            cleaned_data.append(training_example)
            processed_count += 1

        except Exception as e:
            print(f"处理数据时出错: {e}")
            continue

    # 保存清理后的数据 - 使用JSON数组格式
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print("\n📊 处理完成!")
    print(f"处理数据: {processed_count} 条")
    print(f"清理重复: {cleaned_count} 条")
    print(f"输出文件: {output_file}")


# 使用示例
if __name__ == "__main__":
    # 处理完整数据集
    print("\n🔄 处理完整数据集...")
    input_file = "server/data/train_dataset.json"
    output_file = "server/data/training_data_formatted.json"

    clean_structured_complaint_data(input_file, output_file)
