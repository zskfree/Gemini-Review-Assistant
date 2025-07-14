# Gemini 文献综述助手

基于 Google Gemini AI 的自动化文献综述生成工具，提供友好的 Web 界面，快速从 PDF 文献生成高质量学术文稿。

## 核心功能

- 🤖 **智能文献总结**：基于 Gemini AI 自动提取关键信息
- 📄 **多格式输出**：文献综述 / 定性研究论文
- 🌐 **Web 界面**：三步式操作流程，直观易用
- ⚡ **缓存机制**：避免重复处理，提升效率
- 📊 **实时进度**：处理状态可视化，时间预估

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/zskfree/Gemini-Review-Assistant
cd Gemini-Review-Assistant

# 安装依赖
pip install -r requirements.txt

# 配置 API 密钥
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入您的 Gemini API 密钥
```

### 准备文件

1. **PDF 文献**：放入 `PDF_Files/` 目录
2. **研究主题**：编辑 `TXT_Files/研究主题.txt`
3. **参考文献**：在 `TXT_Files/参考文献列表.txt` 中添加引用格式

**引用格式示例**：
```
[1] 张三, 李四. 人工智能在教育中的应用研究[J]. 教育学报, 2023(3): 15-25.
[2] Wang, L. AI-Powered Learning Systems[J]. Education Technology, 2023.
```

### 运行

```bash
python app.py
```

访问 `http://localhost:5000` 开始使用。

## 文件结构

```
Gemini-Review-Assistant/
├── app.py                     # Flask Web 应用
├── config.yaml                # 配置文件
├── requirements.txt
├── src/                       # 核心代码
│   ├── llm_api.py            # Gemini API 接口
│   ├── summarizer.py         # 文献总结模块
│   ├── final_generator.py    # 最终文稿生成
│   └── ...
├── templates/index.html       # Web 界面
├── PDF_Files/                 # PDF 文献目录
├── TXT_Files/                 # 配置文本文件
│   ├── 研究主题.txt
│   ├── 参考文献列表.txt
│   └── [提示词文件]
├── cache/                     # 缓存目录
└── Results_Files/             # 结果输出
```

## 使用流程

### 步骤1：选择文献
- 系统自动识别 PDF 文件
- 匹配引用信息
- 选择要处理的文献

### 步骤2：文献总结
- 自动调用 Gemini AI 生成总结
- 实时显示处理进度
- 查看总结质量

### 步骤3：生成文稿
- 选择输出类型（综述/论文）
- 一键生成最终文稿
- 下载结果文件

## 配置说明

`config.yaml` 主要配置项：

```yaml
llm:
  model_name: "gemini-2.5-flash"              # 文献总结模型
  final_draft_model_name: "gemini-2.5-pro"    # 最终生成模型（可选）
  api_key: "YOUR_API_KEY"                     # Gemini API 密钥
  temperature: 1.5                            # 创造性参数
  max_retries: 5                              # 重试次数

paths:
  pdf_dir: "PDF_Files/"
  txt_dir: "TXT_Files/"
  cache_file: "cache/summaries_cache.json"
  final_output_file: "Results_Files/最终结果.txt"

cache:
  enabled: true                               # 启用缓存
```

## 高级功能

### 缓存管理
```bash
# 重新处理所有文献（清除缓存）
rm cache/summaries_cache.json

# 或在配置中禁用缓存
cache.enabled: false
```

### 自定义提示词
编辑 `TXT_Files/` 中的提示词文件：
- `文献总结提示词.txt` - 控制单篇总结格式
- `文献综述撰写提示词.txt` - 控制综述生成
- `定性研究论文撰写提示词.txt` - 控制论文生成

### 命令行选项
```bash
python app.py --port 8080 --no-browser    # 自定义端口，不自动打开浏览器
```

## 常见问题

**Q: 文献总结质量不高怎么办？**
A: 删除 `cache/summaries_cache.json`，调整提示词后重新运行

**Q: PDF 文件无法匹配引用？**
A: 确保引用信息完全包含 PDF 文件名的关键部分

**Q: API 调用失败？**
A: 检查 API 密钥、网络连接，适当增加 `max_retries`

**Q: 最终文稿生成失败？**
A: 确保有足够的成功总结，尝试降低 `temperature` 值

## 技术栈

- **后端**：Python Flask
- **AI 模型**：Google Gemini 2.5
- **前端**：Bootstrap + JavaScript
- **文件处理**：PDF 解析 + 文本处理

## 注意事项

- 处理大量文献需要时间，请耐心等待
- API 调用可能产生费用，请关注使用额度
- 生成内容仅供参考，建议人工审核
- 确保 PDF 文件未加密且格式规范

---

**开始您的智能文献综述之旅！** 🚀