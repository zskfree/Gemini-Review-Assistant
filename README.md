# Gemini Review Assistant

一个基于 AI 的文献综述自动化工作流。

## 简介

本工具旨在利用大语言模型（LLM）的能力，自动化处理学术文献的综述流程。通过读取 PDF 文件，提取核心信息，生成摘要，并匹配参考文献，极大地提升了研究人员的工作效率。

当前项目的主要逻辑位于 `new_workflow` 目录中，这是一个基于脚本的简化工作流。

## 项目结构

```
new_workflow/
├── config example.yaml     # 配置文件模板
├── workflow.py             # 工作流主入口脚本
├── pdfs/                   # 存放待处理的 PDF 文件
├── src/                    # 核心源码模块
│   ├── config_loader.py
│   ├── pdf_processor.py
│   ├── summary_generator.py
│   ├── reference_matcher.py
│   └── results_exporter.py
└── txts/                   # 存放输入的文本文件
    ├── 研究主题.txt
    └── 参考文献列表.txt
```

## 快速开始

请遵循以下步骤来运行本项目：

**1. 安装依赖**

```bash
pip install -r requirements.txt
```

**2. 配置环境**

将 `config example.yaml` 复制为 `config.yaml`，并在其中填入您的 API 密钥等必要信息。

```bash
# 进入 new_workflow 目录
cd new_workflow

# 复制配置文件
cp "config example.yaml" config.yaml
```
然后使用文本编辑器打开 `config.yaml` 并完成配置。

**3. 准备输入文件**

- 将需要处理的 PDF 文件放入 `new_workflow/pdfs/` 目录。
- 在 `new_workflow/txts/研究主题.txt` 中定义您的研究主题。
- 在 `new_workflow/txts/参考文献列表.txt` 中提供参考文献列表。

**4. 运行工作流**

完成以上步骤后，运行主工作流脚本。

```bash
# 确保您在 new_workflow 目录下
python workflow.py
```

处理完成后，结果将根据您的配置导出。