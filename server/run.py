#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工商投诉数据分析系统 - 服务器启动脚本
基于Flask的后端API服务
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 工商投诉数据分析系统 - 后端服务启动")
    print("=" * 60)

    try:
        # 导入Flask应用
        from src import app

        # 确保数据目录存在
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)

        # 启动配置
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", 8888))
        debug = os.getenv("DEBUG", "True").lower() == "true"

        logger.info(f"服务器配置: {host}:{port}, Debug: {debug}")
        logger.info("API文档地址: http://localhost:8888/")
        logger.info("健康检查: http://localhost:8888/health")

        print(f"📍 服务器地址: http://{host}:{port}")
        print(f"🔍 API接口: http://{host}:{port}/")
        print(f"❤️  健康检查: http://{host}:{port}/health")
        print("-" * 60)

        # 启动Flask服务器
        app.run(host=host, port=port, debug=debug, threaded=True)

    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        print("❌ 启动失败：缺少必要的依赖包")
        print("请运行: pip install -r requirements.txt")
        sys.exit(1)

    except Exception as e:
        logger.error(f"启动服务器失败: {e}")
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
