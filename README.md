# 🚀 自动独立站生成平台

输入一句话，AI 自动生成 Google SEO 优化的完整独立站。

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 🤖 一句话生成 | 输入自然语言，自动提取品牌名、行业，生成完整网站 |
| 📄 SEO 着陆页 | 谷歌优化的单页着陆页，含 Hero/Features/FAQ/CTA |
| 🌐 完整网站 | 多页网站（首页+关于+产品+博客+联系），支持 ZIP 下载 |
| 💰 定价页 | 三档定价方案展示，含 FAQ 模块 |
| 🎨 AI 生成 | 对接 DeepSeek/GLM API，自动生成专业营销文案 |
| 🛡 零成本兜底 | 无 API Key 也能用——内置 Mock 后端提供模板内容 |

---

## 📦 安装 & 启动

### 前置要求

- **Python 3.10+**
  - [官方下载](https://www.python.org/downloads/)
  - 安装时勾选 ✅ **Add Python to PATH**

### 启动（Windows）

```
双击 start.bat
```

### 启动（Mac / Linux）

```bash
chmod +x start.sh
./start.sh
```

### 手动启动

```bash
pip install -r requirements.txt
python -m uvicorn apis.app:app --host 0.0.0.0 --port 8866
```

启动后打开浏览器访问 → **http://127.0.0.1:8866**

---

## 🚀 部署到公网

### 方案一：Railway（推荐，免费额度够用）

1. 注册 [Railway](https://railway.app/)
2. Fork 本项目到 GitHub
3. 在 Railway 中导入 GitHub 仓库
4. 设置启动命令: `uvicorn apis.app:app --host 0.0.0.0 --port ${PORT:-8866}`
5. 自动部署完成！

### 方案二：Render（免费）

1. 注册 [Render](https://render.com/)
2. 创建 Web Service，连接到 GitHub 仓库
3. Start Command: `uvicorn apis.app:app --host 0.0.0.0 --port $PORT`
4. 部署完成

### 方案三：PythonAnywhere

1. 注册 [PythonAnywhere](https://www.pythonanywhere.com/)
2. 上传项目到 Files
3. 创建 Web App → 选择 Manual Configuration → Python 3.10
4. 修改 WSGI 文件指向 `apis.app:app`

---

## 🔑 配置 AI Key（可选，解锁真 AI 生成）

不配 Key 也能用，内置模板兜底。配了 AI Key 后会生成更个性化的内容：

### DeepSeek（推荐，便宜）

```bash
# Windows PowerShell
$env:DEEPSEEK_API_KEY = "sk-xxxxxxxx"

# Mac / Linux
export DEEPSEEK_API_KEY="sk-xxxxxxxx"
```

注册获取: https://platform.deepseek.com/

### 智谱 GLM

```bash
$env:GLM_API_KEY = "xxxxxxxx"
```

注册获取: https://open.bigmodel.cn/

---

## 📡 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端界面 |
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/backends` | GET | 后端状态 |
| `/api/v1/generate` | POST | 生成站点（表单） |
| `/api/v1/generate-from-text` | POST | 一句话生成 |
| `/api/v1/preview/{id}` | GET | 预览生成页 |
| `/api/v1/download/{id}` | GET | 下载 HTML |
| `/api/v1/download-zip/{id}` | GET | 下载 ZIP |
| `/docs` | GET | Swagger API 文档 |

---

## 🏗 项目结构

```
auto_site_builder/
├── apis/              # FastAPI 入口和路由
│   ├── app.py          # 应用入口
│   └── routes/
│       └── generate.py # 所有 API 端点
├── core/              # 核心引擎
│   ├── engine.py       # 编排器
│   ├── loaders.py      # 动态后端加载
│   └── backends/       # AI 和模板后端
│       ├── ai/          # DeepSeek / GLM / Mock
│       └── template/    # Jinja2 / Simple
├── builders/          # 业务逻辑层
│   └── site_planner.py # 自然语言解析
├── static/
│   └── index.html     # 前端界面
├── outputs/           # 生成的文件
│   ├── *.html          # 单页 HTML
│   └── *.zip           # 完整网站包
├── start.bat          # Windows 一键启动
├── start.sh           # Mac/Linux 一键启动
├── requirements.txt   # Python 依赖
└── config.yaml        # 配置文件
```

---

## ⚙ 配置

详见 `config.yaml`，主要配置项：

- `app.port` — 服务端口（默认 8866）
- `ai.deepseek` — DeepSeek API 配置
- `ai.glm` — GLM API 配置
- `ai.mock` — 兜底模式（始终启用）
- `output.dir` — 生成文件目录
- `security.cors_origins` — 跨域配置

---

## 🛠 技术栈

- **后端**: FastAPI + Uvicorn
- **AI**: DeepSeek / GLM / Mock
- **模板**: Jinja2 / Python Simple
- **设计**: 仿 asyncio/passlib 架构模式

---

Made with ❤️ by QClaw