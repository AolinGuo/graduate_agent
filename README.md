
## Begin
快速开始
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

模型微调虚拟环境
```bash
cd LlamaFactory
source myven/bin/activate
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


## Server

安装虚拟环境

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