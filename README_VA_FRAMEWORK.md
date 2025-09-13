# 工商投诉数据分析系统 (基于va-framework重构版)

## 🎯 项目概述

本项目是基于va-framework架构重构的工商投诉数据分析系统，采用前后端分离的设计模式，提供投诉数据的时序分析、可视化展示和报告生成功能。

### 🏗️ 架构特点

- **前端**: 基于Vue 3 + Vite + Element Plus + Pinia的现代化前端框架
- **后端**: 基于Flask的轻量级API服务，提供数据处理和分析功能
- **数据分析**: 集成pandas、statsmodels等科学计算库，支持ACF、STL等时序分析方法
- **可视化**: 支持多种图表类型的数据可视化

## 📁 项目结构

```
graduate_agent/
├── va-framework/                    # 主要应用目录
│   ├── client/                      # 前端应用
│   │   ├── src/
│   │   │   ├── components/          # Vue组件
│   │   │   ├── pages/              # 页面组件
│   │   │   ├── stores/             # 状态管理
│   │   │   └── styles/             # 样式文件
│   │   ├── package.json            # 前端依赖配置
│   │   └── vite.config.ts          # Vite配置
│   │
│   └── server/                     # 后端API服务
│       ├── src/
│       │   ├── models.py          # 数据模型和业务逻辑
│       │   ├── views.py           # API路由和接口
│       │   └── __init__.py        # Flask应用初始化
│       ├── data/                  # 数据文件目录
│       ├── requirements.txt       # Python依赖
│       └── run.py                 # 服务器启动脚本
│
├── data/                          # 原始数据文件
├── run_va_system.py              # 系统统一启动脚本
├── config.yaml                   # 系统配置文件
└── README_VA_FRAMEWORK.md        # 本文档
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+
- **Node.js**: 16+ (可选，用于前端开发)
- **操作系统**: Windows/Linux/macOS

### 方式一：一键启动（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd graduate_agent

# 一键启动（自动安装依赖并启动前后端）
python run_va_system.py
```

### 方式二：分别启动

#### 启动后端服务

```bash
# 进入后端目录
cd va-framework/server

# 安装Python依赖
pip install -r requirements.txt

# 启动后端服务
python run.py
```

#### 启动前端服务

```bash
# 进入前端目录
cd va-framework/client

# 安装前端依赖
pnpm install  # 或 npm install

# 启动前端开发服务器
pnpm run dev  # 或 npm run dev
```

### 访问地址

- **前端界面**: http://localhost:3333
- **后端API**: http://localhost:5000
- **API健康检查**: http://localhost:5000/health

## 📊 核心功能

### 数据管理
- 支持CSV、JSON、Excel等格式的数据导入
- 数据预览和字段信息查看
- 基于时间和实体的数据筛选

### 时序分析
- **ACF分析**: 自相关函数分析，识别数据的时间依赖性
- **STL分解**: 季节性趋势分解，分离时间序列的趋势、季节性和残差成分
- **异常检测**: 基于Z-Score和孤立森林的异常值检测

### 报告生成
- 自动生成投诉数据分析报告
- 支持多种报告模板和风格
- 可导出分析结果和图表

### 可视化展示
- 交互式图表展示
- 支持时序图、散点图、柱状图等多种图表类型
- 响应式设计，适配不同屏幕尺寸

## 🔧 配置说明

### 系统配置 (`config.yaml`)

```yaml
data:
  dataset_file: 'data/processed_data.csv'  # 数据文件路径
  encoding: 'utf-8'                        # 文件编码
  
server:
  host: '0.0.0.0'                         # 服务器监听地址
  port: 5000                              # 服务器端口
  debug: true                             # 调试模式
```

### 环境变量

```bash
# 后端API基础URL（前端使用）
VITE_API_BASE_URL=http://localhost:5000

# Flask服务器配置
HOST=0.0.0.0
PORT=5000
DEBUG=True
```

## 📡 API接口

### 数据管理接口

- `GET /data/summary` - 获取数据摘要
- `GET /data/preview` - 获取数据预览
- `POST /data/filter` - 筛选数据

### 分析接口

- `POST /analysis/time-series` - 时序分析
- `POST /analysis/acf` - ACF分析
- `POST /analysis/stl` - STL分解
- `POST /analysis/report` - 生成报告

### 系统接口

- `GET /health` - 健康检查
- `GET /get_all_entities` - 获取实体信息（兼容接口）

## 🛠️ 开发指南

### 添加新的分析方法

1. 在 `va-framework/server/src/models.py` 中添加分析方法
2. 在 `va-framework/server/src/views.py` 中添加对应的API路由
3. 在前端 `complaint-store.ts` 中添加API调用方法
4. 创建前端组件来展示分析结果

### 自定义数据源

修改 `models.py` 中的 `_load_data()` 方法来支持新的数据格式或数据源。

### 扩展前端组件

在 `va-framework/client/src/components/` 目录下创建新的Vue组件，并在页面中引用。

## 🧪 测试

### 后端测试

```bash
cd va-framework/server

# 测试API接口
curl http://localhost:5000/health
curl http://localhost:5000/data/summary
```

### 前端测试

```bash
cd va-framework/client

# 运行单元测试
pnpm test

# 运行端到端测试
pnpm test:e2e
```

## 📚 技术栈

### 后端技术
- **Flask**: Web框架
- **pandas**: 数据处理
- **numpy**: 数值计算  
- **statsmodels**: 统计建模和时序分析
- **scikit-learn**: 机器学习
- **PyYAML**: 配置文件解析

### 前端技术
- **Vue 3**: 前端框架
- **Vite**: 构建工具
- **Element Plus**: UI组件库
- **Pinia**: 状态管理
- **axios**: HTTP客户端
- **D3.js**: 数据可视化（可选）

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详情请见 [LICENSE](LICENSE) 文件。

## 🔗 相关链接

- [va-framework 官方文档](https://github.com/antfu/vitesse-lite)
- [Flask 官方文档](https://flask.palletsprojects.com/)
- [Vue 3 官方文档](https://v3.vuejs.org/)
- [Element Plus 官方文档](https://element-plus.org/)

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件至 [your-email@example.com]

---

**注意**: 这是基于va-framework架构重构的版本，保持了原有的数据分析功能，但采用了更现代化和可维护的架构设计。

