import os
import sys


# 获取当前脚本所在目录 (server/data)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (server)
SERVER_ROOT = os.path.dirname(CURRENT_DIR)
# 获取源代码目录 (server/src)
SRC_DIR = os.path.join(SERVER_ROOT, "src")

# 将 src 目录加入 Python 搜索路径，这样才能 import ai_service_vllm
sys.path.append(SRC_DIR)
import json
import logging
import gc
import torch
from typing import List

# 添加项目根目录到路径，确保绝对导入能工作
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 文件路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "test.jsonl")            # 原始数据
FILE_STEP_1 = os.path.join(BASE_DIR, "intermediate_1_query.jsonl")   # 第一步结果
FILE_STEP_2 = os.path.join(BASE_DIR, "intermediate_2_context.jsonl") # 第二步结果
FILE_STEP_3 = os.path.join(BASE_DIR, "final_result.jsonl")           # 最终结果

# 批处理大小 (vLLM一次处理多少条，根据显存调整)
BATCH_SIZE = 50 

def load_jsonl(filepath):
    data = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip(): data.append(json.loads(line))
    return data

def save_batch(filepath, data_list):
    """追加写入模式，防止内存积压"""
    with open(filepath, 'a', encoding='utf-8') as f:
        for item in data_list:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

# ==========================================
# 阶段 1: 批量生成查询语句 (需要 vLLM)
# ==========================================
def run_step_1_rewrite():
    logger.info(">>> 开始阶段 1: 生成查询语句")
    
    # 检查是否已经处理过部分数据
    existing_data = load_jsonl(FILE_STEP_1)
    processed_ids = {x['id'] for x in existing_data if 'id' in x}
    start_idx = len(existing_data)
    
    # 加载原始数据
    raw_data = load_jsonl(INPUT_FILE)
    # 给数据加上ID如果不存在
    for i, d in enumerate(raw_data):
        if 'id' not in d: d['id'] = i
            
    # 过滤掉已处理的
    to_process = [d for d in raw_data if d['id'] not in processed_ids]
    
    if not to_process:
        logger.info("所有数据已完成改写，跳过阶段 1")
        return

    # --- 初始化 vLLM ---
    # 此时显存全部分配给 vLLM
    try:
        from server.src.ai_service_vllm import get_vllm_ai_service
        # 强制 TP=1 或 TP=2 (根据你的卡数)
        ai_service = get_vllm_ai_service() 
        ai_service.load_model()
    except Exception as e:
        logger.error(f"vLLM 加载失败: {e}")
        return

    # 分批处理
    total = len(to_process)
    for i in range(0, total, BATCH_SIZE):
        batch = to_process[i : i + BATCH_SIZE]
        logger.info(f"正在改写批次: {i}/{total}")
        
        prompts = []
        for item in batch:
            # 构建 Prompt
            p = f"任务：将以下市民投诉转化为标准的法律查询语句。\n【投诉】{item['question']}\n【要求】去隐私，提取核心法律问题，只输出查询语句。\n请输出查询语句："
            msgs = [{"role": "system", "content": "你是一个法律检索专家。"}, {"role": "user", "content": p}]
            full_prompt = ai_service.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            prompts.append(full_prompt)
            
        # vLLM 批量生成
        outputs = ai_service.llm.generate(prompts, ai_service.default_sampling_params)
        
        # 结果存盘
        results = []
        for idx, out in enumerate(outputs):
            txt = out.outputs[0].text.strip().replace("输出：", "").replace("查询语句：", "").strip('"')
            # 继承原始数据，增加 search_query 字段
            res_item = batch[idx].copy()
            res_item['search_query'] = txt
            results.append(res_item)
            
        save_batch(FILE_STEP_1, results)

    # 释放显存 (虽然 Python GC 不一定立即释放，但尽力而为)
    ai_service.unload_model()
    del ai_service
    gc.collect()
    torch.cuda.empty_cache()
    logger.info("阶段 1 完成，结果已保存。")

# ==========================================
# 阶段 2: 批量 RAG 检索 (不需要 vLLM，需要 Embedding 模型)
# ==========================================
def run_step_2_rag():
    logger.info(">>> 开始阶段 2: RAG 检索")
    
    # 读取上一步的结果
    input_data = load_jsonl(FILE_STEP_1)
    
    # 检查进度
    existing_data = load_jsonl(FILE_STEP_2)
    processed_ids = {x['id'] for x in existing_data}
    to_process = [d for d in input_data if d['id'] not in processed_ids]
    
    if not to_process:
        logger.info("所有数据已完成检索，跳过阶段 2")
        return

    # --- 初始化 RAG ---
    # 此时 vLLM 已卸载，显存充足
    try:
        from server.src.rag_service import LegalRAGService
        # 指定 GPU 0，因为 vLLM 已经不在了
        rag = LegalRAGService(device="cuda:0") 
    except Exception as e:
        logger.error(f"RAG 初始化失败: {e}")
        return

    results = []
    # RAG 通常是 CPU/IO 密集型或轻量级 GPU，不需要太复杂的 batch
    # 但为了防止 IO 太频繁，还是攒一波写一次
    buffer = []
    
    for idx, item in enumerate(to_process):
        query = item.get('search_query', '')
        
        try:
            # 执行检索
            docs = rag.search(query, top_k=3) # 增加 top_k 保证召回
            if docs:
                # 拼接法条，注意这里可能会很长
                ctx = "\n".join([f"【依据{k+1}】《{d['source']}》: {d['content']}" for k, d in enumerate(docs)])
            else:
                ctx = "（未检索到相关法律条文）"
        except Exception:
            ctx = "（检索服务异常）"
            
        new_item = item.copy()
        new_item['legal_context'] = ctx
        buffer.append(new_item)
        
        if len(buffer) >= 50:
            save_batch(FILE_STEP_2, buffer)
            buffer = []
            logger.info(f"已检索 {idx+1}/{len(to_process)}")
            
    # 保存剩余的
    if buffer:
        save_batch(FILE_STEP_2, buffer)
        
    logger.info("阶段 2 完成，结果已保存。")

# ==========================================
# 阶段 3: 批量生成最终回复 (需要 vLLM)
# ==========================================
def run_step_3_final():
    logger.info(">>> 开始阶段 3: 生成最终回复")
    
    input_data = load_jsonl(FILE_STEP_2)
    
    existing_data = load_jsonl(FILE_STEP_3)
    processed_ids = {x['id'] for x in existing_data if 'id' in x} # 假设最终结果保留id
    to_process = [d for d in input_data if d['id'] not in processed_ids]
    
    if not to_process:
        logger.info("所有数据已完成处理")
        return

    # --- 再次初始化 vLLM ---
    try:
        from server.src.ai_service_vllm import get_vllm_ai_service
        # 注意：这里可能需要更大的 max_model_len，因为 input 包含了法条
        ai_service = get_vllm_ai_service()
        # 如果配置文件里的 max_model_len 太小(比如4096)，这里可能会报错
        # 建议在 ai_service_vllm.py 里把 max_model_len 设为 8192 或 16384
        ai_service.load_model()
    except Exception as e:
        logger.error(f"vLLM 加载失败: {e}")
        return

    total = len(to_process)
    for i in range(0, total, BATCH_SIZE):
        batch = to_process[i : i + BATCH_SIZE]
        logger.info(f"正在生成回复批次: {i}/{total}")
        
        prompts = []
        for item in batch:
            # 构建最终 Prompt
            user_msg = f"""请根据法律依据和事件的结果撰写正式答复。
【诉求】{item['search_query']}
【法律依据】
{item['legal_context']}
【事件结果】
{item.get('answer', '已受理')}"""
            
            # 【修正】这里应该使用上面定义的变量 user_msg
            msgs = [{"role": "system", "content": "你是一名专业的政府投诉处理专员。"}, 
                    {"role": "user", "content": user_msg}] 
            
            full_prompt = ai_service.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            prompts.append(full_prompt)
            
        # 批量生成
        # 建议设置较大的 max_tokens (e.g., 512 or 1024)
        outputs = ai_service.llm.generate(prompts, ai_service.default_sampling_params)
        
        final_results = []
        for idx, out in enumerate(outputs):
            reply = out.outputs[0].text
            # 清洗
            if "<think>" in reply: reply = reply.split("</think>")[-1].strip()
            
            save_item = {
                "instruction": batch[idx]['question'],
                "input": f"【法条】\n{batch[idx]['legal_context']}\n\n【记录】\n{batch[idx].get('answer')}",
                "output": reply,
                "id": batch[idx]['id']
            }
            final_results.append(save_item)
            
        save_batch(FILE_STEP_3, final_results)
        
    logger.info("阶段 3 完成，所有任务结束！")

if __name__ == "__main__":
    # 为了保证显存彻底释放，建议每次只取消下面一行的注释运行
    
    # 步骤 1: 
    run_step_1_rewrite()
    
    # 步骤 2: (运行前确保步骤1完成)
    # run_step_2_rag()
    
    # 步骤 3: (运行前确保步骤2完成)
    # run_step_3_final()