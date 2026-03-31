import json
import logging
import torch
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

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
GENERATED_DIR = BASE_DIR / "generated_responses_new"

GENERATED_DIR.mkdir(exist_ok=True)


class HFResponseGenerator:
    """使用 Transformers (Hugging Face) 的普通推理生成器"""

    def __init__(self):
        self.test_data = []
        self.model = None
        self.tokenizer = None
        self.base_model = None  # 保存基座模型引用，方便切换LoRA
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

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
        """初始化基座模型和分词器"""
        if self.model is not None:
            return True

        try:
            logger.info(f"正在加载基座模型: {MODEL_DIR}")
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(MODEL_DIR), trust_remote_code=True
            )
            
            # 使用 bfloat16 加载以节省内存并保持精度
            self.base_model = AutoModelForCausalLM.from_pretrained(
                str(MODEL_DIR),
                device_map="auto",
                torch_dtype=torch.bfloat16,
                trust_remote_code=True
            )
            self.model = self.base_model
            return True
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
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

        # 1. 动态加载/卸载 LoRA
        if use_lora:
            if not LORA_DIR.exists():
                logger.warning(f"LoRA 路径不存在 {LORA_DIR}，跳过此版本")
                return
            logger.info(f"正在加载 LoRA 权重: {LORA_DIR}")
            current_model = PeftModel.from_pretrained(self.base_model, str(LORA_DIR))
        else:
            # 如果不使用 LoRA，确保使用的是原始基座模型
            current_model = self.base_model

        current_model.eval() # 设置为推理模式

        results = []
        pbar = tqdm(total=len(self.test_data), desc=f"生成 {version_name}", unit="条")

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

            # 构造 Prompt
            user_content = self._build_prompt(instruction, input_text)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]

            # 应用对话模板
            input_ids = self.tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
            ).to(self.device)

            # 生成回复
            with torch.no_grad():
                output_ids = current_model.generate(
                    input_ids,
                    max_new_tokens=2048,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            
            # 解码结果（只截取新生成的文本）
            response_ids = output_ids[0][len(input_ids[0]):]
            generated_text = self.tokenizer.decode(response_ids, skip_special_tokens=True).strip()

            results.append({
                "index": len(results),
                "instruction": instruction,
                "reference_output": item.get("output"),
                "generated_output": generated_text,
                "use_rag": use_rag,
                "use_lora": use_lora,
            })
            pbar.update(1)

        pbar.close()

        # 保存结果
        output_path = GENERATED_DIR / f"{version_name}_generated.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "version": version_name,
                "generated_at": datetime.now().isoformat(),
                "results": results,
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ {version_name} 保存至 {output_path}")

        # 如果刚才用了 LoRA，手动删掉 current_model 释放显存，以便后续版本使用基座
        if use_lora:
            del current_model
            torch.cuda.empty_cache()

    def _build_prompt(self, instruction, input_text):
        rag_section = input_text if input_text else "无"
        return f"""请为以下市民诉求撰写一份正式答复。

【市民诉求摘要】
{instruction}

【参考法律依据（RAG检索）】
{rag_section}

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

if __name__ == "__main__":
    generator = HFResponseGenerator()
    generator.generate_all_versions()