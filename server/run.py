#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工商投诉数据分析系统 - 服务器启动脚本（集成模式）
"""

import os
import sys
import logging
from pathlib import Path

# ---------- 1. 统一管理 GPU 分配与环境设置 ----------
# 设置使用的 GPU 编号
gpu_id = "6"
os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id

# 自动计算显卡数量，供 ai_service_vllm.py 的 VLLM_CONFIG 使用
num_gpus = len(gpu_id.split(","))
os.environ["TENSOR_PARALLEL_SIZE"] = str(num_gpus)

# 显存预留：建议设为 0.8-0.85，给 Flask 和系统预留 15% 左右空间
os.environ["GPU_MEM_UTIL"] = "0.85"
# --------------------------------------------------

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 工商投诉数据分析系统 - 后端服务启动 (主进程加载模式)")
    print("=" * 60)

    # 打印环境变量信息
    print(f"📌 使用 GPU: {os.environ.get('CUDA_VISIBLE_DEVICES', '未设置')}")
    print(f"📌 并行规模 (TP): {num_gpus}")
    print(f"📌 基座模型: {os.environ.get('MODEL_PATH', 'server/model-dir')}")
    print(f"📌 LoRA权重: {os.environ.get('LORA_PATH', 'server/lora-dir')}")

    try:
        # ---------- 2. 在内部延迟导入并加载模型 ----------
        # 必须先设置环境变量，再导入 src（防止模型被默认配置抢先初始化）
        from src import app
        from src.ai_service_vllm import get_vllm_ai_service

        # 直接在主进程中初始化并加载 vLLM
        logger.info(f"正在主进程中初始化 vLLM 模型 (TP={num_gpus})...")
        ai_service = get_vllm_ai_service()
        ai_service.load_model()  # 显式触发加载

        # 确保数据目录存在
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)

        # 3. 启动配置
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", 8888))

        # 【重要】集成模式下 debug 必须为 False
        # 否则 Flask 会启动重载子进程，导致模型被加载两次而显存溢出
        debug_mode = False

        print(f"📍 服务器地址: http://{host}:{port}")
        print(f"🔍 API接口: http://{host}:{port}/")
        print(f"❤️  健康检查: http://{host}:{port}/health")
        print("-" * 60)

        # 4. 启动 Flask 服务器
        app.run(host=host, port=port, debug=debug_mode, threaded=True)

    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        print("❌ 启动失败：请检查依赖库是否安装完整")
        sys.exit(1)
    except Exception as e:
        logger.error(f"服务器运行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
