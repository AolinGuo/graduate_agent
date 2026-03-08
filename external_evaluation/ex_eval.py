import json
from typing import Dict, List


def calculate_average_scores(json_data: List[Dict]) -> Dict[str, Dict[str, float]]:
    """
    计算测评结果中每种回答的四个维度的平均值

    参数:
        json_data: 包含多个测评案例的JSON数据列表

    返回:
        每种回答的各维度平均值字典
    """
    # 初始化统计字典，用于累加各维度分数和计数
    score_stats = {
        "base_output": {
            "accuracy": 0,
            "legal_Compliance": 0,
            "completeness": 0,
            "professionalism": 0,
            "count": 0,
        },
        "lora_output": {
            "accuracy": 0,
            "legal_Compliance": 0,
            "completeness": 0,
            "professionalism": 0,
            "count": 0,
        },
        "rag_output": {
            "accuracy": 0,
            "legal_Compliance": 0,
            "completeness": 0,
            "professionalism": 0,
            "count": 0,
        },
        "lora_rag_output": {
            "accuracy": 0,
            "legal_Compliance": 0,
            "completeness": 0,
            "professionalism": 0,
            "count": 0,
        },
    }

    # 遍历每个测评案例，累加分数
    for case in json_data:
        results = case.get("results", {})

        # 遍历每种回答类型
        for output_type, scores in results.items():
            if output_type in score_stats:
                # 累加各维度分数
                score_stats[output_type]["accuracy"] += scores.get("accuracy", 0)
                score_stats[output_type]["legal_Compliance"] += scores.get(
                    "legal_Compliance", 0
                )
                score_stats[output_type]["completeness"] += scores.get(
                    "completeness", 0
                )
                score_stats[output_type]["professionalism"] += scores.get(
                    "professionalism", 0
                )
                # 计数+1
                score_stats[output_type]["count"] += 1

    # 计算平均值
    averages = {}
    for output_type, stats in score_stats.items():
        if stats["count"] > 0:
            averages[output_type] = {
                "accuracy": round(stats["accuracy"] / stats["count"], 2),
                "legal_Compliance": round(
                    stats["legal_Compliance"] / stats["count"], 2
                ),
                "completeness": round(stats["completeness"] / stats["count"], 2),
                "professionalism": round(stats["professionalism"] / stats["count"], 2),
            }
        else:
            averages[output_type] = {
                "accuracy": 0.0,
                "legal_Compliance": 0.0,
                "completeness": 0.0,
                "professionalism": 0.0,
            }

    return averages


# 示例使用
if __name__ == "__main__":
    with open("comparison_api_evaluation.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    # 确保数据是列表格式（单个案例也转为列表）
    if not isinstance(data, list):
        data = [data]
    # 计算平均值
    average_scores = calculate_average_scores(data)

    with open("average_result.json", "w", encoding="utf-8") as f:
        json.dump(average_scores, f, ensure_ascii=False, indent=4)
    # 打印结果
    print("各类型回答的维度平均值：")
    for output_type, scores in average_scores.items():
        print(f"\n{output_type}:")
        for dimension, avg_score in scores.items():
            print(f"  {dimension}: {avg_score}")
