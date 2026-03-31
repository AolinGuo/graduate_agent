# 使用vllm生成回复
import json
import logging
from pathlib import Path
from datetime import datetime
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
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
        """显式指定非 V1 引擎初始化"""
        if self.llm is not None:
            return True

        try:
            logger.info(f"正在以兼容模式初始化 vLLM 引擎...")
            
            # 显式导入 V0 的引擎类，绕过 V1 的自动检测
            from vllm.engine.llm_engine import LLMEngine
            from vllm.entrypoints.llm import LLM
            
            self.llm = LLM(
                model=str(MODEL_DIR),
                tensor_parallel_size=1,
                dtype="bfloat16",
                gpu_memory_utilization=0.85,
                trust_remote_code=True,
                enable_lora=True,
                max_model_len=4096,
                # 关键：在异构环境/新驱动下建议开启 eager 模式，稳定性最高
                enforce_eager=True, 
            )
            return True
        except Exception as e:
            logger.error(f"vLLM 引擎初始化失败: {e}")
            return False

    def generate_all_versions(self):
        """顺序生成所有版本的回复"""
        if not self.load_test_data():
            return
        if not self.init_engine():
            return

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
            system_prompt = (
        "你是一名经验丰富的市场监督管理局公关专员，擅长撰写得体、专业、有温度的官方回复。\n"
        "你的回复需要兼顾法律的严肃性和服务的亲和力。\n"
        "核心原则：\n"
        "1. 严格根据实际处理情况来回复，如果没有请自行根据法律生成回复。\n"
        "2. 引用符合该案例的法律条文。\n"
        "3. 禁止使用Markdown格式，生成完整的一段话。"
            )
            input_text = item.get("input", "") if use_rag else ""

            # 构造格式化的对话内容
            if input_text:
                user_content = f"""请为以下市民诉求撰写一份正式答复。

        【市民诉求摘要】
        {instruction}

        【参考法律依据（RAG检索）】
        {input_text}


        【写作指令 - 请严格执行】
        请输出一段纯文本回复，包含以下逻辑结构：

        1. 首部（共情与确认）：
        - 使用尊称“尊敬的市民您好”。
        - 确认收到投诉，并使用“我局高度重视”、“已立即开展核查”等得体话术。

        2. 正文（事实与法律）：
        依据办理进度，简述调查经过和最终结果，结合参考法律依据说明处理合理性。

        3. 尾部（服务承诺）：
        - 感谢市民的监督与信任。

        请直接生成回复内容，字数控制在250字左右："""
            else:
                user_content = f"""请为以下市民诉求撰写一份正式答复。

        【市民诉求摘要】
        {instruction}

        【参考法律依据（RAG检索）】
        无

        【写作指令 - 请严格执行】
        请输出一段纯文本回复，包含以下逻辑结构：

        1. 首部（共情与确认）：
        - 使用尊称“尊敬的市民您好”。
        - 确认收到投诉，并使用“我局高度重视”、“已立即开展核查”等得体话术。

        2. 正文（事实与法律）：
        依据办理进度，简述调查经过和最终结果，结合参考法律依据说明处理合理性。

        3. 尾部（服务承诺）：
        - 感谢市民的监督与信任。

        请直接生成回复内容，字数控制在250字左右："""

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
        total = len(prompts)
        logger.info(f"正在批量生成 {total} 条回复...")
        
        # 核心修改：带进度条的生成方式
        results = []
        # 初始化进度条
        pbar = tqdm(total=total, desc=f"生成 {version_name}", unit="条")
        
        # 逐一生成（带进度）
        for prompt in prompts:
            output = self.llm.generate(
                prompt, sampling_params=self.sampling_params, lora_request=lora_request
            )
            generated_text = output[0].outputs[0].text.strip()
            results.append({
                "index": len(results),
                "instruction": self.test_data[len(results)].get("instruction"),
                "reference_output": self.test_data[len(results)].get("output"),
                "generated_output": generated_text,
                "use_rag": use_rag,
                "use_lora": use_lora,
            })
            pbar.update(1)  # 进度条+1
        
        pbar.close()


        output_path = GENERATED_DIR / f"{version_name}_generated.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": version_name,
                    "generated_at": datetime.now().isoformat(),
                    "results": results,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(f"✓ {version_name} 保存至 {output_path}")

    def _strip_thinking(self, text: str) -> str:
        """移除 <think> 标签内容（可选）"""
        import re

        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


if __name__ == "__main__":
    generator = VLLMResponseGenerator()
    generator.generate_all_versions()
