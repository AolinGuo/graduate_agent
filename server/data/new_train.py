import json
import sys
import os
import time
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()  # 这会寻找并加载同目录下的 .env 文件
# 导入你提供的本地 RAG 服务
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(SERVER_ROOT, "src")
sys.path.append(SRC_DIR)
from rag_service import LegalRAGService


# ================= 配置区域 =================
INPUT_FILE = "/mnt/disk2/aolin.guo/graduate_agent/server/data/qa_data.jsonl"         # 原始数据集路径
OUTPUT_FILE = "/mnt/disk2/aolin.guo/graduate_agent/server/data/finetune_data.jsonl"  # 输出的微调数据集路径
API_KEY = os.environ.get('DEEPSEEK_API_KEY')
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"


# 系统提示词 (System Prompt)，将写入最终数据集
SYSTEM_PROMPT = "你是一个专业的法律投诉处理助手。请根据用户的投诉内容和提供的法律条文，以第一人称（我/我们）的口吻，生成回复。回复需涵盖事件处理结果，并有理有据地引用法律条文解释原因，态度礼貌且专业。"

# 初始化 API 客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 初始化本地 RAG 服务 (假设使用默认 cuda:4，如果需要改可用 device="cuda:0")
# 注意：请确保显存足够同时运行 RAG 模型
print("正在初始化 RAG 服务...")
rag_service = LegalRAGService()

def call_llm(messages, retries=3):
    """通用 LLM 调用函数，带重试机制"""
    for i in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                stream=False,
                temperature=0.3, # 保持一定的确定性
                response_format={"type": "json_object"} # 强制返回 JSON 格式方便解析
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"   API 调用失败 (尝试 {i+1}/{retries}): {e}")
            time.sleep(2)
    return None

def step_1_clean_and_query(raw_q, raw_a):
    """
    步骤 1: 清洗数据并生成搜索 Query
    """
    prompt = f"""
    你是一个数据清洗专家。请处理以下投诉数据：
    
    【原始投诉】: {raw_q}
    【原始处理结果】: {raw_a}

    请执行以下任务并以 JSON 格式返回：
    1. "cleaned_question": 清洗原始投诉。去除具体地址、去除店铺具体门牌号、去除电话、订单号、姓名等隐私信息。概括为一个清晰的事件描述。
    2. "cleaned_answer": 清洗处理结果。去除具体执法人员姓名、具体时间点、去除内部流转细节。概括最终的处理结论和结果。
    3. "search_query": 将投诉核心转化为一个法律查询语句，用于检索相关法律条文（例如："购买到不合格商品如何索赔"）。

    返回格式示例:
    {{
        "cleaned_question": "...",
        "cleaned_answer": "...",
        "search_query": "..."
    }}
    """
    
    messages = [
        {"role": "system", "content": "你是一个辅助数据处理的JSON生成器。"},
        {"role": "user", "content": prompt}
    ]
    
    result = call_llm(messages)
    try:
        return json.loads(result)
    except:
        print("   ❌ JSON 解析失败，跳过此条")
        return None

def step_2_generate_final_response(cleaned_q, cleaned_a, rag_context_text):
    """
    步骤 2: 生成最终的有理有据的回复
    """
    prompt = f"""
    请根据以下信息生成一条直接回复给投诉人的内容。

    【用户投诉】: {cleaned_q}
    【实际处理结果】: {cleaned_a}
    【相关法律依据】: 
    {rag_context_text}

    要求：
    1. 使用第一人称（"我局"、"我们"或"经核查"）。
    2. 结合【实际处理结果】告知用户最终方案。
    3. 必须自然地引用【相关法律依据】中的条款来支持处理结果或解释原因，显得有理有据。
    4. 语气专业、客观、礼貌。
    5. 不要输出任何额外的解释，只输出回复内容。
    
    请以 JSON 格式返回，Key 为 "final_reply"。
    """
    
    messages = [
        {"role": "system", "content": "你是一个专业的政府热线回复专员。"},
        {"role": "user", "content": prompt}
    ]
    
    result = call_llm(messages)
    try:
        return json.loads(result).get("final_reply", "")
    except:
        return None

def process_dataset():
    if not os.path.exists(INPUT_FILE):
        print(f"找不到输入文件: {INPUT_FILE}")
        return

    print(f"开始处理数据，结果将写入: {OUTPUT_FILE}")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        
        lines = f_in.readlines()
        total = len(lines)
        
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            print(f"[{idx+1}/{total}] 正在处理...", end="", flush=True)
            
            try:
                data = json.loads(line)
                raw_q = data.get("question", "")
                raw_a = data.get("answer", "")
                
                # --- 阶段 1: 清洗与Query生成 (API) ---
                cleaned_data = step_1_clean_and_query(raw_q, raw_a)
                if not cleaned_data:
                    continue
                
                c_question = cleaned_data['cleaned_question']
                c_answer = cleaned_data['cleaned_answer']
                search_query = cleaned_data['search_query']
                
                # --- 阶段 2: RAG 检索 (本地) ---
                # 检索 Top 3 条法律
                rag_results = rag_service.search(search_query, top_k=3)
                
                # 格式化检索到的法律条文，准备喂给 LLM 和放入 Input 字段
                rag_texts = []
                for res in rag_results:
                    # 组合来源和内容，例如：《消费者权益保护法》第二十四条...
                    text = f"《{res['source']}》: {res['content']}"
                    rag_texts.append(text)
                
                rag_context_str = "\n".join(rag_texts)
                
                # --- 阶段 3: 生成最终回复 (API) ---
                final_reply = step_2_generate_final_response(c_question, c_answer, rag_context_str)
                
                if not final_reply:
                    print(" ❌ 生成回复失败")
                    continue

                # --- 阶段 4: 构造微调数据格式 ---
                # 格式：
                # instruction: 清洗后的投诉问题
                # input: RAG检索到的背景知识（法律条文）
                # output: 最终生成的有理有据的回复
                # system: 预设的系统提示词
                
                finetune_entry = {
                    
                    "instruction": c_question,
                    "input": rag_context_str,
                    "output": final_reply,
                    "system": SYSTEM_PROMPT
                }
                
                # 写入文件
                f_out.write(json.dumps(finetune_entry, ensure_ascii=False) + "\n")
                print(" ✅ 完成")
                
            except json.JSONDecodeError:
                print(" ❌ 原始数据格式错误")
            except Exception as e:
                print(f" ❌ 处理异常: {e}")

if __name__ == "__main__":
    process_dataset()