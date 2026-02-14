@echo off
REM 模型测试运行脚本（Windows批处理）

echo ========================================
echo 模型测试脚本
echo ========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

echo 步骤1: 检查并安装依赖
echo ----------------------------------------
pip list | findstr "rouge-chinese" >nul 2>&1
if errorlevel 1 (
    echo 安装测试依赖...
    pip install -r requirements_test.txt
) else (
    echo 依赖已安装
)
echo.

echo 步骤2: 运行基本测试（ROUGE + Embedding）
echo ----------------------------------------
echo 这将测试四个版本: base, base+RAG, lora, lora+RAG
echo 评估指标: ROUGE-1, ROUGE-2, ROUGE-L, Embedding相似度
echo.
set /p run_basic="是否运行基本测试? (y/n): "
if /i "%run_basic%"=="y" (
    python test_model.py
    echo.
    echo 基本测试完成！结果已保存到 test_results/ 目录
)
echo.

echo 步骤3: 运行外部模型评估（可选）
echo ----------------------------------------
echo 这需要OpenAI API密钥或其他大模型API
echo.
set /p run_external="是否运行外部模型评估? (y/n): "
if /i "%run_external%"=="y" (
    set /p api_key="请输入OpenAI API密钥: "
    if not "%api_key%"=="" (
        python test_with_external_model.py %api_key%
        echo.
        echo 外部模型评估完成！结果已保存到 test_results/ 目录
    ) else (
        echo API密钥为空，跳过外部模型评估
    )
)
echo.

echo ========================================
echo 测试完成！
echo ========================================
echo.
echo 查看结果:
echo   - 基本测试结果: test_results/summary_report.json
echo   - 外部评估结果: test_results/external_evaluation_summary.json
echo   - 详细结果: test_results/*_results.json
echo.
pause
