import os
import re
import json

# ================= 配置区域 =================
# 将路径修改为你的主文件夹名称
INPUT_FOLDER = "data/Office_law"
# ===========================================


class Document:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}

    def __repr__(self):
        # 简化打印：只显示来源和ID
        return f"<Doc source='{self.metadata.get('source')}' id='{self.metadata.get('id')}'> len={len(self.page_content)}"


def clean_noise_lines(text):
    """Step 1: 预清洗 - 去除网页噪音"""
    lines = text.split("\n")
    cleaned_lines = []

    noise_keywords = [
        "索引号：",
        "主题分类：",
        "文号：",
        "发布日期：",
        "公文生成日期：",
        "分享 |",
        "官方微信",
        "无障碍浏览",
        "版权所有",
        "ICP备",
        "网站地图",
        "当前位置：",
        "相关链接",
        "扫一扫",
        "PDF文件",
    ]

    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
        if line_strip.startswith("【") and "】" in line_strip:
            continue
        if any(kw in line_strip for kw in noise_keywords):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def is_chapter_header(line):
    """判断是否为章节标题（如：第一章 总则）"""
    pattern = r"^\s*第[零一二三四五六七八九十百]+[章节]"
    return bool(re.match(pattern, line.strip()))


def truncate_by_keywords(text):
    """
    遇到指定的结束词（如'中国政府网'），直接丢弃该词及其后面所有的内容。
    """
    stop_words = ["中国政府网", "www.gov.cn", "来源："]

    for word in stop_words:
        if word in text:
            text = text[: text.find(word)]

    return text.strip()


def split_standard_law(text, filename):
    """处理标准法律 (按'第X条'切分)"""
    chunks = []
    source_name = filename.replace(".txt", "")

    # 修复正则：使用 (?:...) 非捕获组，避免 split 产生多余空元素
    article_pattern = r"(?:^|\n)\s*(第[零一二三四五六七八九十百千万0-9]+条)"
    splits = re.split(article_pattern, text)

    # 步长为2遍历
    for i in range(1, len(splits) - 1, 2):
        title = splits[i].strip()
        raw_content = splits[i + 1]

        # 1. 剔除中间夹杂的章节标题
        content_lines = raw_content.split("\n")
        valid_lines = [
            line.strip()
            for line in content_lines
            if line.strip() and not is_chapter_header(line.strip())
        ]
        temp_content = "\n".join(valid_lines)

        # 2. 关键词截断清洗
        final_content = truncate_by_keywords(temp_content)

        if final_content:
            full_text = f"{title} {final_content}"
            chunks.append(
                Document(
                    page_content=full_text,
                    metadata={
                        "source": source_name,
                        "id": title,
                        # 已移除 'type' 和 'category'
                    },
                )
            )
    return chunks


def split_policy_doc(text, filename):
    """处理政策文件 (按'一、'切分)"""
    chunks = []
    source_name = filename.replace(".txt", "")
    item_pattern = r"(^[一二三四五六七八九十]+、)"
    splits = re.split(item_pattern, text, flags=re.MULTILINE)

    for i in range(1, len(splits) - 1, 2):
        title = splits[i].strip()
        raw_content = splits[i + 1]

        # 关键词截断清洗
        final_content = truncate_by_keywords(raw_content)

        if final_content:
            full_text = f"{title} {final_content}"
            chunks.append(
                Document(
                    page_content=full_text,
                    metadata={
                        "source": source_name,
                        "id": title,
                        # 已移除 'type' 和 'category'
                    },
                )
            )
    return chunks


def save_to_json(documents, output_file="legal_data_cleaned.json"):
    """
    将 Document 对象列表保存为 JSON 文件
    """
    print(f"💾 正在保存结果到 {output_file} ...")

    data_list = []
    for doc in documents:
        data_list.append({"page_content": doc.page_content, "metadata": doc.metadata})

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
        print(f"✅ 保存成功！文件位置: {os.path.abspath(output_file)}")
    except Exception as e:
        print(f"❌ 保存失败: {e}")


def process_legal_files():
    all_docs = []

    if not os.path.exists(INPUT_FOLDER):
        print(f"❌ 错误：找不到文件夹 {INPUT_FOLDER}")
        return []

    print(f"📂 开始遍历 {INPUT_FOLDER} ...\n" + "-" * 40)

    for root, dirs, files in os.walk(INPUT_FOLDER):
        for f in files:
            if f.endswith(".txt"):
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as f_obj:
                        raw_text = f_obj.read()

                    cleaned_text = clean_noise_lines(raw_text)

                    # 不再传递 category 参数
                    if re.search(r"第[0-9零一二]+条", cleaned_text):
                        docs = split_standard_law(cleaned_text, f)
                    else:
                        docs = split_policy_doc(cleaned_text, f)

                    all_docs.extend(docs)
                    print(f"✅ {f} -> 切分出 {len(docs)} 条")

                except Exception as e:
                    print(f"❌ 读取错误 {f}: {e}")

    return all_docs


if __name__ == "__main__":
    documents = process_legal_files()

    print("-" * 40)
    print(f"🎉 全部完成！总共获得 {len(documents)} 个结构化数据块。")

    if documents:
        save_to_json(documents, "legal_data_cleaned.json")

        print("\n🔍 数据预览 (Metadata 已简化):")
        # 预览前50个字符
        print(
            json.dumps(
                {
                    "content": documents[0].page_content[:50] + "...",
                    "meta": documents[0].metadata,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
