# ScholarFlow - 文献综述自动化工具

一个基于 AI 的文献综述自动化工具，旨在利用大语言模型（LLM）的能力，自动化处理学术文献的综述流程。

## 简介

ScholarFlow 通过读取 PDF 文件（支持普通文本 PDF 及扫描件 OCR），提取核心信息，生成结构化摘要，并自动匹配参考文献，极大地提升了研究人员的工作效率。项目支持多种 LLM 后端（如 Gemini, GLM-4, OpenAI 等），并提供 Web 界面和命令行两种操作方式。

## 项目结构

```text
ScholarFlow/
├── new_workflow/
│   ├── app.py              # Web UI 入口 (Flask)
│   ├── workflow.py         # 命令行工作流入口
│   ├── config.yaml         # 配置文件 (需从模板创建)
│   ├── config example.yaml  # 配置文件模板
│   ├── src/                # 核心源码模块
│   │   ├── config_loader.py     # 配置加载
│   │   ├── pdf_processor.py     # PDF 处理逻辑
│   │   ├── pdf_to_markdown.py   # PDF 转 Markdown (支持 OCR)
│   │   ├── llm_client.py        # 多模型客户端封装
│   │   ├── summary_generator.py # 摘要生成逻辑
│   │   ├── reference_matcher.py # 参考文献匹配
│   │   ├── results_exporter.py  # 结果导出 (CSV/JSON)
│   │   ├── file_uploader.py     # 临时文件托管服务
│   │   └── prompts.py           # LLM 提示词模板
│   ├── templates/          # Web 界面 HTML 模板
│   ├── pdfs/               # 默认 PDF 存放目录
│   └── txts/               # 默认输入/输出文本目录
│       ├── 研究主题.txt
│       └── 参考文献列表.txt
├── requirements.txt        # 项目依赖
└── README.md
```

## 快速开始

### 1. 安装依赖

确保您的环境中已安装 Python 3.12+，然后运行：

```bash
pip install -r requirements.txt
```

### 2. 配置环境

将 `new_workflow/config example.yaml` 复制为 config.yaml，并填入您的 API Key。

```bash
cp "new_workflow/config example.yaml" "new_workflow/config.yaml"
```

编辑 config.yaml：

- 配置 `api` 部分（支持 Gemini, ZhipuAI, OpenAI 等）。
- 根据需要修改 `paths` 中的文件路径。

### 3. 准备输入

- 将待处理的 PDF 文件放入 pdfs。
- 在 研究主题.txt 中写入您的研究方向。
- 在 参考文献列表.txt 中列出需要匹配的参考文献。

### 4. 运行工具

#### 方式 A：Web 界面（推荐）

提供可视化的进度展示和配置管理。

```bash
python new_workflow/app.py
```

启动后访问 `http://127.0.0.1:5000`。

#### 方式 B：命令行脚本

适合批量处理或自动化集成。

```bash
python new_workflow/workflow.py
```

## 主要特性

- **智能转换**：集成 `markitdown` 和 LLM 视觉能力，完美处理各类 PDF。
- **多模型支持**：灵活切换 Gemini, GLM-4, Claude 等主流模型。
- **自动化综述**：自动提取研究背景、方法、结论等关键要素。
- **引用匹配**：自动将 PDF 内容与提供的参考文献列表进行关联。
- **结果导出**：支持导出为 JSON 和 CSV 格式，方便后续分析。

## 注意事项

- 扫描件 PDF 处理依赖于 LLM 的视觉能力，请确保配置了支持视觉的模型（如 `gemini-1.5-flash` 或 `glm-4v`）。
- 建议使用代理（在 config.yaml 中配置）以确保 API 访问稳定性。
