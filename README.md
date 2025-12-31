# ScholarFlow - 文献综述自动化工具

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**基于大语言模型的智能文献综述系统**

一站式解决文献处理、内容提取、智能总结与引用匹配的学术工具

</div>

---

## 📚 项目简介

ScholarFlow 是一个强大的 AI 驱动文献综述自动化工具，专为学术研究人员、研究生和科研工作者设计。通过集成先进的大语言模型（LLM），该系统能够：

- 🔍 **智能解析**：自动处理 PDF 文献（包括扫描件 OCR 识别）
- 🤖 **AI 总结**：基于研究主题提取核心观点和关键信息
- 🔗 **引用匹配**：自动将文献与参考文献列表进行精准关联
- 📊 **结果导出**：生成结构化的 CSV/JSON 报告
- 🎯 **多模型支持**：灵活切换 Gemini、智谱AI、OpenAI 等主流模型
- 🌐 **Web 界面**：提供直观的可视化操作面板和实时进度显示

## 📂 项目结构

```text
ScholarFlow/
├── new_workflow/
│   ├── app.py                      # 🌐 Flask Web 应用入口
│   ├── workflow.py                 # 🖥️  命令行工作流入口
│   ├── config.yaml                 # ⚙️  用户配置文件（需从示例创建）
│   ├── config example.yaml         # 📋 配置文件模板
│   ├── src/                        # 📦 核心功能模块
│   │   ├── config_loader.py        #   配置加载器（支持缓存）
│   │   ├── pdf_processor.py        #   PDF 文件处理
│   │   ├── pdf_to_markdown.py      #   PDF 转 Markdown（OCR 支持）
│   │   ├── llm_client.py           #   统一 LLM 客户端（支持多提供商）
│   │   ├── summary_generator.py    #   文献总结生成器（并发处理）
│   │   ├── reference_matcher.py    #   参考文献智能匹配
│   │   ├── results_exporter.py     #   结果导出（CSV/JSON）
│   │   ├── task_manager.py         #   任务管理器（SSE 实时推送）
│   │   ├── logger.py               #   日志系统
│   │   ├── utils.py                #   工具函数
│   │   └── prompts.py              #   LLM 提示词模板
│   ├── templates/                  # 🎨 Web 界面模板
│   │   ├── index.html              #   主页面
│   │   └── settings.html           #   设置页面
│   ├── static/                     # 🎭 静态资源
│   │   ├── css/style.css           #   样式文件
│   │   └── js/main.js              #   前端脚本
│   ├── gemini_web/                 # 🔌 Gemini Web API 集成
│   ├── logs/                       # 📝 运行日志
│   ├── pdfs/                       # 📄 PDF 文件存储目录
│   └── txts/                       # 📂 输入输出文本
│       ├── 研究主题.txt
│       ├── 参考文献列表.txt
│       ├── literature_summary.json  # 总结结果（JSON）
│       ├── reference_mapping.json   # 映射关系
│       └── summary_sorted.csv       # 最终报告（CSV）
├── requirements.txt                # 📦 项目依赖
└── README.md                       # 📖 项目文档
```

## 🚀 快速开始

### 1️⃣ 安装依赖

**环境要求：** Python 3.12+

```bash
# 克隆项目
git clone https://github.com/yourusername/ScholarFlow.git
cd ScholarFlow

# 安装依赖包
pip install -r requirements.txt
```

> **提示：** 建议使用虚拟环境 `python -m venv venv`

---

### 2️⃣ 配置环境

**创建配置文件：**

```bash
# Windows
copy "new_workflow\config example.yaml" "new_workflow\config.yaml"

# Linux/macOS
cp "new_workflow/config example.yaml" "new_workflow/config.yaml"
```

**编辑 `config.yaml`，配置以下关键参数：**

```yaml
api:
  provider: gemini_web  # 选择提供商: gemini | gemini_web | openai | zhipu
  
  # 根据选择的提供商配置相应的密钥
  genai_key: "your-gemini-api-key"        # Gemini API
  zhipu_key: "your-zhipu-api-key"         # 智谱AI
  openai_key: "your-openai-api-key"       # OpenAI/OpenRouter

proxy:
  url: "http://127.0.0.1:7897"  # 代理设置（可选）

concurrency:
  max_workers: 3  # 并发处理数（建议 1-5）
```

---

### 3️⃣ 准备输入数据

**方式 A：通过 Web 界面上传**（推荐）  
启动应用后直接在页面上传 PDF 和输入信息

**方式 B：手动准备文件**

```bash
# 1. 放置 PDF 文件
cp your_papers/*.pdf new_workflow/pdfs/

# 2. 编辑研究主题
echo "您的研究主题" > new_workflow/txts/研究主题.txt

# 3. 添加参考文献列表（每行一条）
cat > new_workflow/txts/参考文献列表.txt << EOF
张三, 李四. 论文标题[J]. 期刊名, 2024, 10(2): 1-10.
Smith J, Doe J. Article Title[J]. Journal Name, 2024, 15(3): 20-30.
EOF
```

---

### 4️⃣ 运行应用

#### 🌐 方式 A：Web 界面（推荐）

```bash
cd new_workflow
python app.py
```

✅ 启动成功后访问：**<http://127.0.0.1:18690>**

**功能特点：**

- 📊 实时进度显示（SSE 推送）
- 🎨 可视化界面操作
- ⚙️ 在线配置管理
- 📥 一键下载结果

#### 🖥️ 方式 B：命令行脚本

适合自动化批处理和脚本集成

```bash
cd new_workflow
python workflow.py
```

**输出位置：**

- `txts/literature_summary.json` - 完整总结数据
- `txts/reference_mapping.json` - 文献映射关系
- `txts/summary_sorted.csv` - 最终报告（可用 Excel 打开）

## ✨ 核心特性

### 🧠 智能文献处理

- **全格式支持**：集成 `markitdown` + LLM 视觉能力，完美处理文本PDF和扫描件
- **OCR 识别**：自动识别图片型PDF内容
- **递归扫描**：支持子目录批量处理

### 🤖 多模型生态

| 提供商 | 模型示例 | 特点 |
|--------|---------|------|
| **Gemini** | `gemini-2.0-flash-exp` | 官方API，速度快 |
| **Gemini Web** | 免费使用 | 基于Cookie，支持图片生成 |
| **智谱AI** | `glm-4-flash` | 国内稳定，支持思维链 |
| **OpenAI** | `gpt-4o-mini` | 通过 OpenRouter 支持 |

### 📊 工作流程

```mermaid
graph LR
    A[上传PDF] --> B[智能解析]
    B --> C[AI总结]
    C --> D[引用匹配]
    D --> E[导出报告]
```

1. **文献映射**：AI 自动分析文件名和参考文献，建立对应关系
2. **并发处理**：多线程同时处理多篇文献（可配置并发数）
3. **实时反馈**：SSE 推送处理进度，掌握每一步状态
4. **结构化输出**：生成包含研究问题、方法、结论等要素的总结

### 🎯 高级功能

- ✅ **断点续传**：自动跳过已处理文献，支持增量更新
- ✅ **配置缓存**：优化性能，减少重复读取
- ✅ **健康检查**：`/health` 端点监控服务状态
- ✅ **日志系统**：详细记录每次运行情况
- ✅ **异常重试**：自动重试失败的请求（可配置次数）

---

## 📖 使用场景

- 📚 **文献综述撰写**：快速提取多篇论文的核心观点
- 🔬 **课题调研**：系统整理相关研究进展
- 📝 **论文写作**：自动生成参考文献总结
- 🎓 **研究生学习**：高效阅读和管理文献

---

## ⚙️ 配置说明

### LLM 提供商选择建议

**免费方案：**

- `gemini_web`（推荐）：免费但需要 Google 账号 Cookie

**付费方案：**

- `gemini`：速度最快，价格合理
- `zhipu`：国内访问稳定
- `openai`：通过 OpenRouter 访问多种模型

### 并发配置

```yaml
concurrency:
  max_workers: 3  # 并发数建议
```

**推荐设置：**

- API 限制较严格：`1-2`
- 一般情况：`3-5`
- 付费用户：`5-10`

---

## ⚠️ 注意事项

### API 密钥安全

- 🔒 不要将 `config.yaml` 提交到版本控制系统
- 🔒 使用 `.gitignore` 排除敏感文件
- 🔒 定期轮换 API 密钥

### 模型选择

- 📷 扫描件PDF需要支持视觉的模型：`gemini-2.0-flash-exp`、`glm-4v`
- 💰 注意 API 计费：建议先用小数据测试
- 🌍 国内访问建议配置代理或使用智谱AI

### 性能优化

- ⚡ 合理设置并发数，避免触发频率限制
- 💾 大批量处理建议分批执行
- 🔄 使用断点续传功能，避免重复处理

---

## 🐛 常见问题

<details>
<summary><b>Q: 智谱AI 初始化失败？</b></summary>

确保已正确安装依赖：

```bash
pip install zhipuai
```

</details>

<details>
<summary><b>Q: Gemini Web API 连接超时？</b></summary>

1. 检查 Cookie 是否过期（重新获取）
2. 配置代理：`proxy.url: "http://127.0.0.1:7890"`
3. 增加超时时间

</details>

<details>
<summary><b>Q: PDF 解析失败？</b></summary>

- 检查 PDF 是否损坏
- 扫描件需要支持视觉的模型
- 查看 `logs/` 目录下的详细日志

</details>

<details>
<summary><b>Q: 如何更改端口？</b></summary>

编辑 `app.py`：

```python
app.run(debug=False, port=你的端口)
```

</details>

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [MarkItDown](https://github.com/microsoft/markitdown) - PDF 转换
- [Gemini](https://ai.google.dev/) - Google AI
- [智谱AI](https://open.bigmodel.cn/) - 国产大模型

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给一个 Star！**

</div>
