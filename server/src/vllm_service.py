import os
import subprocess
import sys


def main():
    # --- 1. 路径定义 ---
    # 获取当前脚本所在目录 (server/src)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取项目根目录 (server/)
    server_root = os.path.dirname(current_dir)

    # 基座模型路径
    base_model_path = os.path.join(server_root, "model-dir")

    # LoRA 权重根目录
    lora_root_dir = os.path.join(server_root, "lora-dir")

    # 假设你有一个名为 'complaint-lora' 的微调权重在 lora-dir 下
    # 如果文件夹不存在，脚本也会正常启动，只是不加载该 LoRA
    lora_name = "complaint-v1"  # 在 API 调用中使用的名称
    lora_path = lora_root_dir  # 实际物理路径

    if not os.path.exists(base_model_path):
        print(f"Error: 基座模型未找到: {base_model_path}")
        return

    print(f"Base Model: {base_model_path}")

    # --- 2. 构建 vLLM 启动命令 ---
    cmd = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        base_model_path,
        "--served-model-name",
        "Qwen3-Base",  # 基座模型的 API 名称
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--trust-remote-code",
        # --- LoRA 核心配置 ---
        "--enable-lora",  # 开启 LoRA 支持
        # 设置 LoRA 的最大秩 (Rank)。
        # 如果你训练时设置的 lora_rank 是 64，这里必须 >= 64
        "--max-lora-rank",
        "64",
        # 设置同时能服务的最大 LoRA 数量 (显存允许的情况下可以设大)
        "--max-loras",
        "4",
        # 显存利用率 (加载 LoRA 需要额外显存，建议适当调低给 LoRA 留空间)
        "--gpu-memory-utilization",
        "0.9",
    ]

    # --- 3. 动态挂载 LoRA 模块 ---
    # 如果检测到该 LoRA 目录存在，则挂载它
    # 格式: name=path
    if os.path.exists(lora_path):
        print(f"检测到 LoRA 权重，正在挂载: {lora_name} -> {lora_path}")
        cmd.extend(["--lora-modules", f"{lora_name}={lora_path}"])
    else:
        print(f"提示: 未找到 LoRA 路径 {lora_path}，将仅启动基座模型。")

    # --- 4. 启动服务 ---
    print("正在启动系统服务...")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n服务已停止。")
    except subprocess.CalledProcessError as e:
        print(f"启动失败: {e}")


if __name__ == "__main__":
    main()
