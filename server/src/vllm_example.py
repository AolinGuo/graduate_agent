from openai import OpenAI

# 初始化客户端
client = OpenAI(
    api_key="EMPTY",
    base_url="http://localhost:8000/v1",
)

# 场景 1: 使用基座模型 (通用能力)
# model 名称对应启动脚本中的 --served-model-name
print("--- 调用基座模型 ---")
resp_base = client.chat.completions.create(
    model="Qwen3-Base",
    messages=[
        {"role": "system", "content": "你是一个通用助手。"},
        {"role": "user", "content": "怎么处理客户投诉？"}
    ],
    temperature=0.7
)
print(f"基座回答: {resp_base.choices[0].message.content}\n")

# 场景 2: 使用 LoRA 模型 (微调后的专业能力)
# model 名称对应启动脚本中 --lora-modules 的 name 部分 (即 complaint-v1)
# 只要 LoRA 文件存在且服务启动时加载了，这里就能直接调用
try:
    print("--- 调用微调模型 (LoRA) ---")
    resp_lora = client.chat.completions.create(
        model="complaint-v1", 
        messages=[
            {"role": "system", "content": "你是一个专业的投诉分析专员。"},
            {"role": "user", "content": "怎么处理客户投诉？"}
        ],
        temperature=0.7
    )
    print(f"LoRA回答: {resp_lora.choices[0].message.content}")
except Exception as e:
    print(f"LoRA 调用失败 (可能是服务未加载该 LoRA): {e}")