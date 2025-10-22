#!/bin/bash
# AI引擎切换脚本

echo "========================================="
echo "   AI推理引擎切换工具"
echo "========================================="
echo ""

# 检测当前引擎
if [ -n "$AI_ENGINE" ]; then
    echo "当前引擎: $AI_ENGINE"
else
    echo "当前引擎: transformers (默认)"
fi

echo ""
echo "请选择要使用的引擎:"
echo "1) transformers - 传统方式（稳定）"
echo "2) vllm - 高性能方式（快3-5倍）"
echo "3) 使用统一接口（推荐）"
echo "4) 查看当前状态"
echo "0) 退出"
echo ""
read -p "请输入选项 [0-4]: " choice

case $choice in
    1)
        echo ""
        echo "✓ 设置为 transformers 引擎"
        export AI_ENGINE=transformers
        echo "export AI_ENGINE=transformers" >> ~/.bashrc
        echo ""
        echo "已设置环境变量，请重启服务生效："
        echo "  python run.py"
        ;;
    2)
        echo ""
        echo "检查 vLLM 是否已安装..."
        python -c "import vllm" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✓ vLLM 已安装"
            export AI_ENGINE=vllm
            echo "export AI_ENGINE=vllm" >> ~/.bashrc
            echo ""
            echo "已设置为 vLLM 引擎，请重启服务生效："
            echo "  python run.py"
        else
            echo "✗ vLLM 未安装"
            echo ""
            echo "请先安装 vLLM："
            echo "  pip install vllm"
            echo ""
            read -p "是否现在安装？[y/N] " install_choice
            if [ "$install_choice" = "y" ] || [ "$install_choice" = "Y" ]; then
                pip install vllm
                if [ $? -eq 0 ]; then
                    echo "✓ vLLM 安装成功"
                    export AI_ENGINE=vllm
                    echo "export AI_ENGINE=vllm" >> ~/.bashrc
                else
                    echo "✗ vLLM 安装失败"
                fi
            fi
        fi
        ;;
    3)
        echo ""
        echo "配置统一接口..."
        echo ""
        echo "需要修改 src/views.py："
        echo "  from src.ai_service import get_ai_service"
        echo "改为："
        echo "  from src.ai_service_unified import get_unified_ai_service as get_ai_service"
        echo ""
        read -p "是否自动修改？[y/N] " modify_choice
        if [ "$modify_choice" = "y" ] || [ "$modify_choice" = "Y" ]; then
            # 备份
            cp src/views.py src/views.py.backup
            # 修改
            sed -i 's/from src\.ai_service import get_ai_service/from src.ai_service_unified import get_unified_ai_service as get_ai_service/g' src/views.py
            echo "✓ 已修改并备份原文件到 src/views.py.backup"
            echo ""
            echo "现在可以通过环境变量切换引擎："
            echo "  export AI_ENGINE=transformers  # 使用transformers"
            echo "  export AI_ENGINE=vllm          # 使用vLLM"
        fi
        ;;
    4)
        echo ""
        echo "当前系统状态："
        echo "----------------------------------------"
        echo "环境变量 AI_ENGINE: ${AI_ENGINE:-未设置（默认transformers）}"
        echo ""
        
        echo "已安装的引擎："
        python -c "import torch; print('  ✓ PyTorch:', torch.__version__)" 2>/dev/null || echo "  ✗ PyTorch 未安装"
        python -c "import transformers; print('  ✓ Transformers:', transformers.__version__)" 2>/dev/null || echo "  ✗ Transformers 未安装"
        python -c "import vllm; print('  ✓ vLLM:', vllm.__version__)" 2>/dev/null || echo "  ✗ vLLM 未安装"
        echo ""
        
        echo "可用的AI服务文件："
        [ -f "src/ai_service.py" ] && echo "  ✓ ai_service.py (transformers)" || echo "  ✗ ai_service.py"
        [ -f "src/ai_service_vllm.py" ] && echo "  ✓ ai_service_vllm.py (vllm)" || echo "  ✗ ai_service_vllm.py"
        [ -f "src/ai_service_unified.py" ] && echo "  ✓ ai_service_unified.py (统一接口)" || echo "  ✗ ai_service_unified.py"
        echo ""
        
        echo "当前 views.py 使用的服务："
        grep "from src.ai_service" src/views.py | head -1 || echo "  未找到导入语句"
        ;;
    0)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "完成！"
echo "========================================="

