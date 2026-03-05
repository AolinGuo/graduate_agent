# 使用vllm生成回复
import json
import logging
from pathlib import Path
from datetime import datetime
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 路径配置
BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "server" / "model-dir"
LORA_DIR = BASE_DIR / "server" / "lora-dir"
TEST_DATA_PATH = BASE_DIR / "server" / "data" / "query_test.json"
GENERATED_DIR = BASE_DIR / "generated_responses"

GENERATED_DIR.mkdir(exist_ok=True)

class VLLMResponseGenerator:
    """使用 vLLM 的高性能模型回复生成器"""

    def __init__(self):
        self.test_data = []
        self.llm = None
        # 预设采样参数
        self.sampling_params = SamplingParams(
            temperature=0.7,
            top_p=0.9,
            max_tokens=2048,
            # stop=["<|endoftext|>", "<|im_end|>"] # 根据你的模型微调情况设置停止词
        )

    def load_test_data(self):
        """加载测试数据"""
        if not TEST_DATA_PATH.exists():
            logger.error(f"测试数据文件不存在: {TEST_DATA_PATH}")
            return False
        with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
            self.test_data = json.load(f)
        logger.info(f"测试数据加载完成，共 {len(self.test_data)} 条")
        return True

    def init_engine(self):
        """初始化 vLLM 引擎 (只初始化一次，后续切换 LoRA)"""
        if self.llm is not None:
            return True
        
        try:
            logger.info(f"正在初始化 vLLM 引擎，模型路径: {MODEL_DIR}")
            self.llm = LLM(
                model=str(MODEL_DIR),
                tensor_parallel_size=1, # 如果你有多个 GPU，可以增加此数值
                dtype="bfloat16",
                gpu_memory_utilization=0.85, # 留出一点显存给 LoRA 或其他操作
                trust_remote_code=True,
                enable_lora=True, # 必须开启才能支持 LoRA
                max_model_len=4096
            )
            return True
        except Exception as e:
            logger.error(f"vLLM 引擎初始化失败: {e}")
            return False

    def generate_all_versions(self):
        """顺序生成所有版本的回复"""
        if not self.load_test_data(): return
        if not self.init_engine(): return

        # 定义任务配置: (版本名, 是否使用LoRA, 是否使用RAG)
        configs = [
            ("base", False, False),
            ("base_rag", False, True),
            ("lora", True, False),
            ("lora_rag", True, True),
        ]

        for version_name, use_lora, use_rag in configs:
            self.process_version(version_name, use_lora, use_rag)

    def process_version(self, version_name: str, use_lora: bool, use_rag: bool):
        """处理具体某一个版本的批量生成"""
        logger.info(f"开始处理版本: {version_name}")
        
        prompts = []
        lora_request = None

        # 1. 如果使用 LoRA，构造请求
        if use_lora:
            if not LORA_DIR.exists():
                logger.warning(f"LoRA 路径不存在 {LORA_DIR}，跳过此版本")
                return
            lora_request = LoRARequest("complaint_lora", 1, str(LORA_DIR))

        # 2. 批量构造 Prompt
        for item in self.test_data:
            instruction = item.get("instruction", "")
            system_prompt = item.get("system", "你是一个专业的法律投诉处理助手。")
            input_text = item.get("input", "") if use_rag else ""

            # 构造格式化的对话内容
            if input_text:
                user_content = f"【投诉内容】：\n{instruction}\n\n【参考法律条文】：\n{input_text}"
            else:
                user_content = f"【投诉内容】：\n{instruction}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
            
            # 使用 vLLM 内部的 tokenizer 应用模板
            prompt = self.llm.get_tokenizer().apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            prompts.append(prompt)

        # 3. 调用 vLLM 批量生成
        logger.info(f"正在批量生成 {len(prompts)} 条回复...")
        outputs = self.llm.generate(
            prompts, 
            sampling_params=self.sampling_params,
            lora_request=lora_request
        )

        # 4. 整理结果并保存
        results = []
        for i, output in enumerate(outputs):
            generated_text = output.outputs[0].text.strip()
            
            # 如果模型输出了 <think> 标签且你不需要它，可以在这里清洗
            # clean_text = self._strip_thinking(generated_text)

            results.append({
                "index": i,
                "instruction": self.test_data[i].get("instruction"),
                "reference_output": self.test_data[i].get("output"),
                "generated_output": generated_text,
                "use_rag": use_rag,
                "use_lora": use_lora
            })

        output_path = GENERATED_DIR / f"{version_name}_generated.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "version": version_name,
                "generated_at": datetime.now().isoformat(),
                "results": results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ {version_name} 保存至 {output_path}")

    def _strip_thinking(self, text: str) -> str:
        """移除 <think> 标签内容（可选）"""
        import re
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

if __name__ == "__main__":
    generator = VLLMResponseGenerator()
    generator.generate_all_versions()