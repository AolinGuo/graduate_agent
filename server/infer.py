#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型推理脚本 - Python版本
使用微调后的模型进行推理
"""

from modelscope import AutoModelForCausalLM, AutoTokenizer
import torch

# 配置参数
MODEL_PATH = "/mnt/disk2/aolin.guo/graduate_agent/server/model-dir"  # 基础模型路径
ADAPTER_PATH = None  # 如果有LoRA权重，设置为 "output/v0-xxx/checkpoint-xxx"


def load_model():
    """加载模型和tokenizer"""
    print(f"正在加载模型: {MODEL_PATH}")

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)

    # 如果有微调的LoRA权重，加载它
    if ADAPTER_PATH:
        print(f"正在加载LoRA权重: {ADAPTER_PATH}")
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, ADAPTER_PATH)
        model = model.merge_and_unload()  # 合并LoRA权重到基础模型

    print("模型加载完成！")
    return model, tokenizer


def chat(model, tokenizer, user_input, system_prompt="You are a helpful assistant."):
    """进行对话推理"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    # 应用对话模板
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    # 编码输入
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    # 生成回复
    print("正在生成回复...")
    generated_ids = model.generate(
        **model_inputs, max_new_tokens=2048, temperature=0.7, top_p=0.9, do_sample=True
    )

    # 解码输出
    generated_ids = [
        output_ids[len(input_ids) :]
        for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return response


def main():
    """主函数 - 交互式对话"""
    # 加载模型
    model, tokenizer = load_model()

    print("\n" + "=" * 50)
    print("欢迎使用Qwen3-8B模型！")
    print("输入 'exit' 或 'quit' 退出程序")
    print("=" * 50 + "\n")

    # 交互式对话循环
    while True:
        try:
            user_input = input("用户: ").strip()

            if user_input.lower() in ["exit", "quit", "退出"]:
                print("再见！")
                break

            if not user_input:
                continue

            # 获取模型回复
            response = chat(model, tokenizer, user_input)
            print(f"\n助手: {response}\n")

        except KeyboardInterrupt:
            print("\n\n程序被中断，再见！")
            break
        except Exception as e:
            print(f"\n发生错误: {e}\n")


if __name__ == "__main__":
    main()
