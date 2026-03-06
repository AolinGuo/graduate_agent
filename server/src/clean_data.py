import os
import json
import logging

# ================= 配置区域 =================

# 1. 指定显卡ID (例如使用 0,1,2,3 四张卡)
# 如果你的机器有8张卡，想用后四张，这里填 "4,5,6,7"
TARGET_GPU_IDS = "1,4,5,6"

# 2. 关键：在导入 vllm 之前设置环境变量
os.environ["CUDA_VISIBLE_DEVICES"] = TARGET_GPU_IDS

# 3. vLLM 并行度 (必须与上面的显卡数量一致)
TENSOR_PARALLEL_SIZE = 4

# 模型与数据路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # server/
MODEL_PATH = os.path.join(BASE_DIR, "model-dir")
INPUT_FILE = os.path.join(BASE_DIR, "data", "qa_data.jsonl")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "qa_data_cleaned.jsonl")

# ===========================================

# 在设置完环境变量后，再导入 vllm 和 torch
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataCleaningJob:
    def __init__(self, model_path: str):
        self.model_path = model_path

        # 打印当前使用的设备配置
        logger.info("正在初始化多卡清洗任务...")
        logger.info(
            f"使用显卡 (CUDA_VISIBLE_DEVICES): {os.environ.get('CUDA_VISIBLE_DEVICES')}"
        )
        logger.info(f"并行度 (Tensor Parallel): {TENSOR_PARALLEL_SIZE}")

        # 1. 初始化 Tokenizer
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path, trust_remote_code=True
            )
        except Exception as e:
            logger.error(f"Tokenizer加载失败: {e}")
            raise

        # 2. 初始化 vLLM 引擎 (多卡模式)
        try:
            self.llm = LLM(
                model=model_path,
                trust_remote_code=True,
                gpu_memory_utilization=0.85,
                max_model_len=4096,
                # 关键：这里设置为 4，启用模型并行
                tensor_parallel_size=TENSOR_PARALLEL_SIZE,
                dtype="bfloat16",
                # 分布式推理依赖 Ray，vLLM 会自动处理，但建议显式指定
                distributed_executor_backend="ray",
            )
        except Exception as e:
            logger.error(f"vLLM引擎加载失败 (请检查显存是否足够): {e}")
            raise

    def build_prompt(self, content: str) -> str:
        """构建清洗数据的 Prompt"""
        system_content = (
            "你是一个专业的数据清洗助手。你的任务是处理市民投诉文本。"
            "请严格遵循以下规则对文本进行重写："
            "1. 【保留】商店名称、企业名称。"
            "2. 【保留】涉及的金额数值。"
            "3. 【保留】事件的核心经过和冲突点。"
            "4. 【删除】具体的订单号、运单号。"
            "5. 【删除】具体的日期（如X月X日）、时间（如XX:XX）。"
            "6. 【删除】具体的门牌号、街道地址（只保留大略位置如'丰台区'或直接保留店名）。"
            "7. 输出要求：直接输出清洗后的文本，不要包含任何前缀或解释。"
        )

        user_content = f"待处理文本：\n{content}"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        return prompt

    def run(self, input_path: str, output_path: str):
        # 1. 读取数据
        if not os.path.exists(input_path):
            logger.error(f"输入文件不存在: {input_path}")
            return

        logger.info(f"正在读取数据: {input_path}")
        raw_data = []
        prompts = []
        valid_indices = []

        with open(input_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for idx, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    raw_data.append(item)
                    if "question" in item:
                        prompts.append(self.build_prompt(item["question"]))
                        valid_indices.append(idx)
                except json.JSONDecodeError:
                    pass

        if not prompts:
            logger.warning("没有提取到有效数据。")
            return

        logger.info(f"准备处理 {len(prompts)} 条数据。")

        # 2. 设置采样参数 (低温度保证清洗准确性)
        sampling_params = SamplingParams(temperature=0.1, top_p=0.9, max_tokens=1024)

        # 3. vLLM 批量推理 (自动利用 4 张卡并行计算)
        logger.info(f"开始在 {TENSOR_PARALLEL_SIZE} 张 GPU 上进行批量推理...")
        outputs = self.llm.generate(prompts, sampling_params)
        logger.info("推理完成，正在处理结果...")

        # 4. 结果回填
        for i, output_obj in enumerate(outputs):
            original_idx = valid_indices[i]
            generated_text = output_obj.outputs[0].text.strip()

            # 过滤可能的思维链标签
            if "<think>" in generated_text:
                parts = generated_text.split("</think>")
                if len(parts) > 1:
                    generated_text = parts[-1].strip()

            raw_data[original_idx]["question"] = generated_text

        # 5. 保存
        logger.info(f"写入结果: {output_path}")
        with open(output_path, "w", encoding="utf-8") as f_out:
            for item in raw_data:
                f_out.write(json.dumps(item, ensure_ascii=False) + "\n")

        logger.info("任务完成。")


if __name__ == "__main__":
    # 简单的环境检查
    import torch

    if torch.cuda.device_count() < TENSOR_PARALLEL_SIZE:
        logger.warning(
            f"警告：检测到的 GPU 数量 ({torch.cuda.device_count()}) 少于配置的并行度 ({TENSOR_PARALLEL_SIZE})，程序可能会报错。"
        )

    # 确保目录存在
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # 模拟数据生成 (如果文件不存在)
    if not os.path.exists(INPUT_FILE):
        logger.info("生成测试数据...")
        test_data = [
            {
                "question": "测试数据：我在丰台区使用了200元购买商品，订单号123456",
                "answer": "已处理",
            }
        ] * 10
        with open(INPUT_FILE, "w", encoding="utf-8") as f:
            for item in test_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 启动
    job = DataCleaningJob(MODEL_PATH)
    job.run(INPUT_FILE, OUTPUT_FILE)
