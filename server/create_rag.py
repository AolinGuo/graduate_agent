import os
import json
import math
import time
import torch
import gc
import shutil
import multiprocessing
from langchain_core.documents import Document

# ================= 配置区域 =================
GPU_IDS = ["0", "2", "3", "6"]

DATA_PATH = os.path.join("data", "legal_data.json")
MODEL_PATH = os.path.join("embedding_model")
FINAL_DB_PATH = os.path.join("rag_vector")
TEMP_DB_DIR = os.path.join("temp_vectors_multi")

BATCH_SIZE = 8
SAVE_INTERVAL = 1000

# 🔥 [新增配置] 合并时的批处理大小
# 建议设置为 5-10。意思是一次只将 5 个小文件合并成一个中文件，防止内存撑爆
MERGE_GROUP_SIZE = 5
# ===========================================


# ... (worker_process 函数保持不变，此处省略以节省篇幅，直接复用原代码) ...
def worker_process(gpu_id, subset_docs, worker_id):
    # 此处代码与你原始内容完全一致，无需修改
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    print(
        f"👷 [Worker {worker_id}] 启动: 使用物理 GPU {gpu_id}, 需处理 {len(subset_docs)} 条文档"
    )
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS

    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=MODEL_PATH,
            model_kwargs={"device": "cuda", "trust_remote_code": True},
            encode_kwargs={"normalize_embeddings": True, "batch_size": BATCH_SIZE},
        )
    except Exception as e:
        print(f"❌ [Worker {worker_id}] 模型加载失败: {e}")
        return []

    saved_paths = []
    total = len(subset_docs)
    for i in range(0, total, SAVE_INTERVAL):
        batch = subset_docs[i : i + SAVE_INTERVAL]
        step_str = f"{worker_id}_{i // SAVE_INTERVAL}"
        try:
            temp_db = FAISS.from_documents(batch, embeddings)
            save_path = os.path.join(TEMP_DB_DIR, f"part_{step_str}")
            temp_db.save_local(save_path)
            saved_paths.append(save_path)
            print(f"   🚀 [Worker {worker_id}] 进度: {i + len(batch)}/{total} 已保存")
            del temp_db
            torch.cuda.empty_cache()
            gc.collect()
        except Exception as e:
            print(f"❌ [Worker {worker_id}] 处理出错: {e}")
    print(f"✅ [Worker {worker_id}] 任务完成！")
    return saved_paths


# 🔥 [新增函数] 递归分批合并逻辑
def recursive_merge(paths, embeddings, level=0):
    """
    将 paths 列表中的索引分批合并。
    如果 paths 数量 > MERGE_GROUP_SIZE，则先归并成中间文件，再递归合并。
    """
    from langchain_community.vectorstores import FAISS

    # 递归终止条件：只剩 1 个文件时，它就是当前层级的结果
    if len(paths) == 1:
        return paths[0]

    print(
        f"\n🔄 [合并层级 {level}] 当前待合并文件数: {len(paths)}，每组合并 {MERGE_GROUP_SIZE} 个..."
    )

    next_level_paths = []

    # 将路径列表切分成小块 (chunking)
    for i in range(0, len(paths), MERGE_GROUP_SIZE):
        group = paths[i : i + MERGE_GROUP_SIZE]
        group_id = f"L{level}_G{i // MERGE_GROUP_SIZE}"

        # 1. 加载组内第一个作为基座
        print(f"  👉 正在处理组 {group_id} (包含 {len(group)} 个分块)...")
        try:
            base_db = FAISS.load_local(
                group[0], embeddings, allow_dangerous_deserialization=True
            )

            # 2. 依次合并组内剩余的
            for sub_path in group[1:]:
                next_db = FAISS.load_local(
                    sub_path, embeddings, allow_dangerous_deserialization=True
                )
                base_db.merge_from(next_db)
                # 及时清理被合并的对象
                del next_db
                gc.collect()

            # 3. 保存这一组的合并结果到磁盘 (中间文件)
            # 创建专门的中间目录，避免混乱
            intermediate_dir = os.path.join(TEMP_DB_DIR, "intermediate")
            if not os.path.exists(intermediate_dir):
                os.makedirs(intermediate_dir)

            save_path = os.path.join(intermediate_dir, f"merged_{group_id}")
            base_db.save_local(save_path)
            next_level_paths.append(save_path)

            print(f"  ✅ 组 {group_id} 合并完成 -> {save_path}")

            # 4. 释放基座内存 (至关重要)
            del base_db
            gc.collect()

        except Exception as e:
            print(f"❌ 合并组 {group_id} 失败: {e}")
            # 简单容错：如果失败，跳过该组（实际生产中可能需要重试）
            continue

    # 递归调用下一层
    return recursive_merge(next_level_paths, embeddings, level=level + 1)


def main():
    # 0. 初始化
    start_time = time.time()
    if os.path.exists(TEMP_DB_DIR):
        shutil.rmtree(TEMP_DB_DIR)
    os.makedirs(TEMP_DB_DIR)

    # 1. 加载数据
    print(f"📂 主进程: 加载数据 {DATA_PATH} ...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    all_docs = []
    for item in raw_data:
        if "page_content" in item:
            all_docs.append(
                Document(
                    page_content=item["page_content"], metadata=item.get("metadata", {})
                )
            )

    total_docs = len(all_docs)
    print(f"📊 总文档数: {total_docs}")

    # 2. 数据切分
    num_gpus = len(GPU_IDS)
    if num_gpus == 0:
        print("❌ 未配置 GPU_IDS")
        return

    chunk_size = math.ceil(total_docs / num_gpus)

    tasks = []
    for i in range(num_gpus):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, total_docs)
        subset = all_docs[start_idx:end_idx]
        if subset:  # 避免空切片
            tasks.append((GPU_IDS[i], subset, i))

    # 3. 多进程并行启动
    ctx = multiprocessing.get_context("spawn")
    print(f"🔥 正在启动 {len(tasks)} 个进程并行处理...")

    with ctx.Pool(processes=num_gpus) as pool:
        results = pool.starmap(worker_process, tasks)

    all_temp_paths = [path for worker_paths in results for path in worker_paths]

    # 4. 🔥 优化后的分级合并逻辑
    print(f"🔗 所有 GPU 任务结束。开始分级合并 {len(all_temp_paths)} 个索引分块...")

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings

    # 仅用于加载索引结构的 dummy embeddings (CPU 模式)
    dummy_embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_PATH, model_kwargs={"device": "cpu", "trust_remote_code": True}
    )

    if all_temp_paths:
        # 使用递归合并代替原来的直接循环
        final_temp_path = recursive_merge(all_temp_paths, dummy_embeddings)

        # 此时 final_temp_path 是最后一个合并完成的文件夹路径
        # 将其移动/重命名为最终目标路径
        print(f"🚚 正在将最终结果移动到 {FINAL_DB_PATH} ...")

        if os.path.exists(FINAL_DB_PATH):
            shutil.rmtree(FINAL_DB_PATH)

        # 直接移动文件夹比 load 再 save 快得多且不占内存
        shutil.move(final_temp_path, FINAL_DB_PATH)

        print(f"🎉🎉 全部完成！总耗时: {time.time() - start_time:.2f} 秒")
        print(f"💾 最终保存路径: {os.path.abspath(FINAL_DB_PATH)}")

        # 清理临时目录
        # shutil.rmtree(TEMP_DB_DIR) # 确认无误后再取消注释
    else:
        print("❌ 未生成任何索引文件")


if __name__ == "__main__":
    main()
