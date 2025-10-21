
# va-framework

source /etc/profile.d/clash.sh
proxy_on
## Begin
```bash
cd server
source .venv/bin/activate
python run.py
```

```bash
cd client
pnpm i
pnpm run dev
```


## Client

```bash

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

\. "$HOME/.nvm/nvm.sh"

nvm install 22

npm install -g pnpm

node -v 

npm -v 

```


[vitesse-lite](https://github.com/antfu/vitesse-lite)

```bash

cd client

pnpm i

pnpm run dev

```

## Server

```bash
cd server
source .venv/bin/activate
python run.py
```

```bash
cd server



# Creating a Virtual Environment
python3 -m venv .venv

# Activating the virtual environment (Mac/Linux)
source .venv/bin/activate

# Activating the virtual environment (Windows)
.venv\Scripts\activate

# Install Dependencies
pip3 install -r requirements.txt

# Run
python run.py
```
下载模型

```bash
modelscope download --model="Qwen/Qwen3-8B" --local_dir ./model-dir
```
查看显存占用
```bash
nvidia-smi

```



使用modelscope来下载模型
参考文档
使用如下命令安装ModelScope SDK：
```bash
pip install modelscope
```


使用ModelScope Python SDK下载模型，该方法支持断点续传和模型高速下载：
```python
from modelscope import snapshot_download
model_dir = snapshot_download("Qwen/Qwen2.5-0.5B-Instruct")
```

pipeline推理
使用AutoModel加载模型
```bash
pip install transformers
```
```python
from modelscope import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen2.5-0.5B-Instruct"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)
使用ModelScope pipeline加载模型
from modelscope.pipelines import pipeline
word_segmentation = pipeline('word-segmentation',model='damo/nlp_structbert_word-segmentation_chinese-base')
模型推理
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

inference_pipeline = pipeline(
    task=Tasks.auto_speech_recognition,
    model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
    model_revision="v2.0.4")

rec_result = inference_pipeline('https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/test_audio/asr_vad_punc_example.wav')
print(rec_result)
未与ModelScope SDK做原生集成的模型
from modelscope import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen2.5-0.5B-Instruct"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

prompt = "Give me a short introduction to large language model."
messages = [
    {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
    {"role": "user", "content": prompt}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=512
)
generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
]

response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
```
模型微调
ms-swift是魔搭社区提供的大模型与多模态大模型微调部署框架
```bash
pip install ms-swift -U
```
微调脚本
# 22GB
```python
CUDA_VISIBLE_DEVICES=0 \
swift sft \
    --model Qwen/Qwen2.5-7B-Instruct \
    --train_type lora \
    --dataset 'AI-ModelScope/alpaca-gpt4-data-zh#500' \
              'AI-ModelScope/alpaca-gpt4-data-en#500' \
              'swift/self-cognition#500' \
    --torch_dtype bfloat16 \
    --num_train_epochs 1 \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 1 \
    --learning_rate 1e-4 \
    --lora_rank 8 \
    --lora_alpha 32 \
    --target_modules all-linear \
    --gradient_accumulation_steps 16 \
    --eval_steps 50 \
    --save_steps 50 \
    --save_total_limit 2 \
    --logging_steps 5 \
    --max_length 2048 \
    --output_dir output \
    --system 'You are a helpful assistant.' \
    --warmup_ratio 0.05 \
    --dataloader_num_workers 4 \
    --model_author swift \
    --model_name swift-robot
```
使用训练好的权重进行推理
```python
CUDA_VISIBLE_DEVICES=0 \
swift infer \
    --adapters output/vx-xxx/checkpoint-xxx \
    --stream true \
    --temperature 0 \
    --max_new_tokens 2048
```