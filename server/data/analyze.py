import json
import os

def find_max_length(file_path, target_key=None):
    """
    寻找数据集中最长的一条数据。
    
    Args:
        file_path: 文件路径 (.json 或 .jsonl)
        target_key: (可选) 如果指定，只计算该字段的长度；如果不指定，计算整条JSON字符串的长度。
    """
    if not os.path.exists(file_path):
        print(f"错误: 找不到文件 {file_path}")
        return

    print(f"正在分析文件: {file_path} ...")
    
    max_len = 0
    max_index = -1
    max_item = None
    
    # 读取数据的生成器（节省内存）
    def load_data_generator(path):
        with open(path, 'r', encoding='utf-8') as f:
            if path.endswith('.jsonl'):
                for i, line in enumerate(f):
                    if line.strip():
                        yield i, json.loads(line)
            else:
                # 针对标准 json，一次性读入后遍历
                try:
                    data = json.load(f)
                    for i, item in enumerate(data):
                        yield i, item
                except json.JSONDecodeError:
                    print("JSON 解析失败，请检查文件格式。")

    # 开始遍历
    count = 0
    for idx, item in load_data_generator(file_path):
        count += 1
        current_len = 0
        
        # 模式 1: 指定了字段 (例如只看 'instruction' 或 'content')
        if target_key:
            if target_key in item:
                # 转换为字符串计算长度
                content = str(item[target_key])
                current_len = len(content)
            else:
                # 如果该条数据没有这个字段，长度视为0，或者你可以选择跳过
                current_len = 0
        
        # 模式 2: 默认模式 (计算整条 JSON 数据的总字符数)
        else:
            # 将字典转回字符串来计算总长度 (模拟 Tokenizer 看到的原始文本)
            content = json.dumps(item, ensure_ascii=False)
            current_len = len(content)

        # 更新最大值
        if current_len > max_len:
            max_len = current_len
            max_index = idx
            max_item = item

    print("-" * 30)
    print(f"分析完毕！共扫描 {count} 条数据。")
    print("-" * 30)
    
    if max_item:
        print("【最长数据统计】")
        print(f"最大长度 (字符数): {max_len}")
        print(f"所在位置 (行号/索引): 第 {max_index + 1} 条") # +1 符合人类阅读习惯
        
        print("\n【最长数据内容预览 (前500字符)】:")
        # 打印内容，方便你定位
        preview_content = json.dumps(max_item, ensure_ascii=False, indent=2)
        print(preview_content[:500] + ("..." if len(preview_content) > 500 else ""))
    else:
        print("未找到有效数据。")

# --- 使用示例 ---
if __name__ == "__main__":
    # 你的文件路径
    source_file = "data/finetune_data.jsonl" 
    
    # 方式 A: 计算整条数据的长度 (最常用，推荐)
    find_max_length(source_file)
    
    # 方式 B: 只计算某个字段的长度 (例如只看 input 字段)
    # find_max_length(source_file, target_key="input")