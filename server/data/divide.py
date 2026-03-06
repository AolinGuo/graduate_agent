import json
import random
import os


def split_json_dataset(
    input_path, train_output_path, test_output_path, test_ratio=0.1, seed=42
):
    if not os.path.exists(input_path):
        print(f"错误: 找不到文件 {input_path}")
        return

    print(f"正在读取数据: {input_path} ...")

    data = []

    # --- 修改开始: 增加对 jsonl 的转换逻辑 ---
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            # 如果文件名以 .jsonl 结尾，或者里面是多行独立json
            if input_path.endswith(".jsonl"):
                data = [json.loads(line) for line in f if line.strip()]
            else:
                # 正常的 json 读取
                data = json.load(f)
    except json.JSONDecodeError:
        return
    # --- 修改结束 ---

    total_count = len(data)
    print(f"原始数据共 {total_count} 条")

    # 2. 打乱数据
    random.seed(seed)
    random.shuffle(data)

    # 3. 计算切分点
    test_count = int(total_count * test_ratio)
    split_index = total_count - test_count

    # 4. 切分数据
    train_data = data[:split_index]
    test_data = data[split_index:]

    print(f"划分完成 -> 训练集: {len(train_data)} 条, 测试集: {len(test_data)} 条")

    # 5. 保存文件 (这里我建议还是存为带缩进的 json，方便你看)
    print("正在保存文件...")

    with open(train_output_path, "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)
    print(f"已保存: {train_output_path}")

    with open(test_output_path, "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    print(f"已保存: {test_output_path}")

    print("处理完毕！")


if __name__ == "__main__":
    source_file = "data/finetune_data.jsonl"  # 你的 jsonl 文件

    split_json_dataset(
        input_path=source_file,
        train_output_path="data/query_train.json",
        test_output_path="data/query_test.json",
        test_ratio=0.1,
    )
