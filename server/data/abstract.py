import csv
import json
import os
import re  # 导入正则表达式模块

def clean_content(text: str) -> str:
    """
    清洗文本内容的函数：
    1. 删除日期和时间
    2. 删除订单号（格式如：订单号：123456 或 纯数字长串）
    """
    if not text:
        return ""

    # --- 1. 定义正则表达式模式 ---
    
    # 匹配各类常见日期和时间
    # 例如: 2023-01-01, 2023年1月1日, 12:30:00, 2023/01/01
    date_pattern = r"(\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}([日\s]*)?)|(\d{1,2}[:：]\d{1,2}([:：]\d{1,2})?)"
    
    # 匹配订单号
    # 匹配 "订单号：xxxx" 或 "单号: xxxx"，兼容中英文冒号，允许后面跟字母或数字
    order_id_pattern = r"(订单号|单号|编号)\s*[:：]?\s*[a-zA-Z0-9_-]+"

    # --- 2. 执行替换删除 ---
    
    # 将匹配到的内容替换为空字符串
    text = re.sub(order_id_pattern, "", text) # 先删订单号
    text = re.sub(date_pattern, "", text)     # 再删时间
    
    # --- 3. 清理多余的空格 ---
    # 删除因为替换产生的连续空格，或者标点前的空格
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

def remove_question_overlap(question: str, answer: str) -> str:
    """
    如果 answer 的开头包含了 question 的内容，将其删除
    """
    if not question or not answer:
        return answer
    
    # 简单的开头匹配
    if answer.startswith(question):
        return answer[len(question):].strip()
    
    return answer

def csv_to_jsonl(
    csv_path: str,
    jsonl_path: str,
    question_col: str = "问题详细描述",
    answer_col: str = "回复内容"
):
    if not os.path.exists(csv_path):
        print(f"错误: 找不到文件 {csv_path}")
        return

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        
        count = 0
        skipped = 0
        
        with open(jsonl_path, "w", encoding="utf-8") as out:
            for row in reader:
                # 1. 获取原始文本
                q_raw = row.get(question_col, "").strip()
                a_raw = row.get(answer_col, "").strip()

                # 如果两个都为空，直接跳过
                if not q_raw and not a_raw:
                    continue

                # 2. 【核心修改】先处理 overlap (去重)
                # 逻辑：先去除 answer 开头与 question 重复的部分，再进行内容清洗
                # 理由：如果先清洗内容，可能会导致 question 和 answer 不匹配，从而无法去重
                a_processed = remove_question_overlap(q_raw, a_raw)

                # 3. 【核心修改】进行正则清洗（删时间、删订单号）
                # 这里我们主要清洗 Answer，Question 是否清洗看你需求，一般也建议清洗一下隐私
                q_final = clean_content(q_raw)
                a_final = clean_content(a_processed)

                # 4. 最终空值检查 (清洗后可能变为空)
                if not q_final or not a_final:
                    skipped += 1
                    continue

                record = {
                    "question": q_final,
                    "answer": a_final
                }

                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
                
        print(f"转换完成! 有效数据: {count} 条, 因清洗后为空跳过: {skipped} 条")

if __name__ == "__main__":
    csv_to_jsonl(
        csv_path="processed_data.csv",
        jsonl_path="qa_data.jsonl"
    )