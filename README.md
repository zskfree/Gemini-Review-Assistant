# Gemini 文献综述助手

基于 Google Gemini AI 的智能文献综述生成工具，提供完整的 Web 界面和高级功能，帮助研究者快速从 PDF 文献生成高质量学术文稿。

## ✨ 核心功能

- 🤖 **智能文献总结**：基于 Gemini AI 自动提取关键信息，支持多种模型选择
- 📄 **多格式输出**：支持文献综述和定性研究论文两种专业格式
- 🌐 **现代化 Web 界面**：响应式设计，三步式操作流程，直观易用
- ⚡ **智能缓存机制**：避免重复处理，大幅提升效率
- 📊 **实时进度监控**：处理状态可视化，时间预估和错误处理
- 🔧 **在线配置管理**：Web 界面直接编辑配置和提示词
- 📋 **参考文献核对**：智能匹配 PDF 文件与引用信息
- 🔄 **API 密钥轮换**：支持多个 API 密钥自动轮换，提高稳定性
- 📝 **总结内容编辑**：支持在线编辑和优化文献总结内容

## 🚀 快速开始

### 📦 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/zskfree/Gemini-Review-Assistant
cd Gemini-Review-Assistant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API 密钥
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入您的 Gemini API 密钥
```

### 📁 准备文件

1. **PDF 文献**：将要分析的 PDF 文件放入 `PDF_Files/` 目录
2. **研究主题**：编辑 `TXT_Files/研究主题.txt` 设置研究主题
3. **参考文献**：在 `TXT_Files/参考文献列表.txt` 中添加引用信息

**引用格式示例**：

```text
[1] 张三, 李四. 人工智能在教育中的应用研究[J]. 教育学报, 2023(3): 15-25.
[2] Wang, L. AI-Powered Learning Systems[J]. Education Technology, 2023.
```

### 🎯 启动应用

```bash
# 启动 Web 应用
python app.py

# 自定义端口和选项
python app.py --port 8080 --no-browser
```

访问 `http://localhost:5000` 开始使用。

## 📂 项目结构

```text
Gemini-Review-Assistant/
├── app.py                     # Flask Web 应用主文件
├── index.html                 # 项目介绍页面
├── config.yaml                # 配置文件
├── config.example.yaml        # 配置文件模板
├── requirements.txt           # Python 依赖
├── src/                       # 核心代码模块
│   ├── __init__.py
│   ├── config_loader.py       # 配置加载器
│   ├── file_finder.py         # 文件扫描器
│   ├── reference_parser.py    # 参考文献解析器
│   ├── llm_api.py            # Gemini API 接口
│   ├── summarizer.py         # 文献总结模块
│   ├── final_generator.py    # 最终文稿生成器
│   ├── user_interface.py     # 用户界面工具
│   └── main.py               # 命令行入口
├── templates/                 # Web 模板文件
│   ├── index.html            # 主界面模板
│   ├── config.html           # 配置管理页面
│   └── reference_check.html  # 参考文献核对页面
├── static/                    # 静态资源
│   ├── common.css            # 通用样式
│   └── css/                  # 其他样式文件
├── PDF_Files/                 # PDF 文献目录
├── TXT_Files/                 # 配置文本文件
│   ├── 研究主题.txt
│   ├── 参考文献列表.txt
│   ├── 文献总结提示词.txt
│   ├── 文献综述撰写提示词.txt
│   └── 定性研究论文撰写提示词.txt
├── cache/                     # 缓存目录
│   └── summaries_cache.json  # 文献总结缓存
└── Results_Files/             # 结果输出目录
    ├── 文献总结.json         # 总结结果
    ├── 最终结果.txt          # 文献综述
    └── 定性研究论文.txt      # 定性研究论文
```

## 📋 使用流程

### 🔍 步骤1：文献准备与核对

- 将 PDF 文献放入 `PDF_Files/` 目录
- 在 `TXT_Files/参考文献列表.txt` 中添加引用信息
- 使用 **参考文献核对** 功能检查文件匹配情况
- 可在线重命名文件以改善匹配效果

### ⚙️ 步骤2：配置管理

- 访问 **配置管理** 页面设置 API 密钥和模型参数
- 编辑研究主题和提示词模板
- 测试 API 连接确保配置正确

### 📖 步骤3：文献总结

- 在主界面选择要处理的 PDF 文件
- 系统自动调用 Gemini AI 生成文献总结
- 实时监控处理进度和状态
- 可在线编辑和优化总结内容

### 📝 步骤4：生成最终文稿

- 选择输出类型（文献综述/定性研究论文）
- 一键整合所有总结生成最终文稿
- 下载生成的学术文档

## ⚙️ 配置说明

### 主要配置项

`config.yaml` 核心配置：

```yaml
llm:
  model_name: "gemini-2.5-flash"              # 文献总结模型
  final_draft_model_name: "gemini-2.5-pro"    # 最终生成模型（可选）
  api_key: "YOUR_API_KEY"                     # Gemini API 密钥（支持多个，逗号分隔）
  temperature: 1.5                            # 创造性参数 (0.0-2.0)
  max_retries: 5                              # API 调用重试次数

paths:
  pdf_dir: "PDF_Files/"                       # PDF 文件目录
  txt_dir: "TXT_Files/"                       # 文本配置目录
  cache_file: "cache/summaries_cache.json"    # 缓存文件路径
  summary_output_file: "Results_Files/文献总结.json"  # 总结输出文件
  final_output_file: "Results_Files/最终结果.txt"     # 最终文稿输出

prompts:                                      # 提示词文件配置
  research_theme: "研究主题.txt"
  summary_prompt: "文献总结提示词.txt"
  review_final_prompt: "文献综述撰写提示词.txt"
  qualitative_final_prompt: "定性研究论文撰写提示词.txt"
  references_list_file: "参考文献列表.txt"

cache:
  enabled: true                               # 启用缓存机制
```

### 支持的 Gemini 模型

- `gemini-2.5-flash` - 快速处理，适合文献总结
- `gemini-2.5-pro` - 高质量输出，适合最终文稿生成
- `gemini-2.0-flash-thinking-exp` - 实验性思维模型
- 其他 Gemini 系列模型

## 🔧 高级功能

### 📊 Web 界面功能

- **主界面** (`/`) - 文献选择、总结生成、文稿输出
- **配置管理** (`/config`) - 在线编辑配置和提示词
- **参考文献核对** (`/reference-check`) - 检查文件匹配情况
- **API 测试** - 验证 Gemini API 连接状态

### 🔄 API 密钥轮换

支持配置多个 API 密钥实现自动轮换：

```yaml
llm:
  api_key: "key1,key2,key3"  # 多个密钥用逗号分隔
```

系统会智能轮换使用，提高稳定性和处理速度。

### 💾 缓存管理

```bash
# 清除缓存重新处理所有文献
rm cache/summaries_cache.json

# 或在配置中禁用缓存
cache.enabled: false
```

### ✏️ 自定义提示词

可通过 Web 界面或直接编辑 `TXT_Files/` 中的文件：

- `文献总结提示词.txt` - 控制单篇文献总结的格式和内容
- `文献综述撰写提示词.txt` - 控制文献综述的结构和风格
- `定性研究论文撰写提示词.txt` - 控制定性研究论文的框架

### 🖥️ 命令行选项

```bash
# 基本启动
python app.py

# 自定义端口和选项
python app.py --port 8080 --no-browser --host 0.0.0.0

# 命令行模式（无 Web 界面）
python src/main.py
```

## ❓ 常见问题

### 文献处理相关

**Q: 文献总结质量不高怎么办？**
A: 可以通过以下方式改善：

- 在配置管理页面调整提示词模板
- 删除 `cache/summaries_cache.json` 重新处理
- 调整 `temperature` 参数（降低值获得更稳定输出）
- 在总结完成后使用在线编辑功能优化内容

**Q: PDF 文件无法匹配引用信息？**
A: 使用参考文献核对功能：

- 访问 `/reference-check` 页面查看匹配状态
- 确保引用信息包含 PDF 文件名的关键部分
- 可以在线重命名 PDF 文件改善匹配效果

### 技术问题

**Q: API 调用失败或连接超时？**
A: 检查以下配置：

- 在配置管理页面测试 API 连接
- 确认 API 密钥正确且有效
- 适当增加 `max_retries` 重试次数
- 配置多个 API 密钥实现轮换

**Q: 最终文稿生成失败？**
A: 确保以下条件：

- 至少有一篇成功的文献总结
- 检查模型配置是否正确
- 尝试降低 `temperature` 值
- 查看错误日志获取详细信息

## 🛠️ 技术栈

- **后端框架**：Python Flask
- **AI 模型**：Google Gemini 2.5 系列
- **前端技术**：Bootstrap 5 + JavaScript + 响应式设计
- **文件处理**：PDF 解析 + 文本处理
- **数据存储**：JSON 缓存 + YAML 配置
- **部署方式**：本地部署 + Web 服务

## ⚠️ 注意事项

- **处理时间**：大量文献处理需要时间，请耐心等待
- **API 费用**：Gemini API 调用可能产生费用，请关注使用额度
- **内容审核**：生成内容仅供参考，建议人工审核和编辑
- **文件格式**：确保 PDF 文件未加密且格式规范
- **网络连接**：需要稳定的网络连接访问 Gemini API
- **数据安全**：本地处理，文献内容不会上传到第三方服务器

## 🤝 贡献与支持

欢迎提交 Issue 和 Pull Request 来改进项目！

- **GitHub 仓库**：[Gemini-Review-Assistant](https://github.com/zskfree/Gemini-Review-Assistant)
- **问题反馈**：通过 GitHub Issues 报告问题
- **功能建议**：欢迎提出新功能建议

---

**🚀 开始您的智能文献综述之旅！**

让 AI 助力您的学术研究，提高文献综述的效率和质量。
