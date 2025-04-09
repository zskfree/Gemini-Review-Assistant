import os
from typing import List

def find_pdf_files(pdf_dir: str) -> List[str]:
    """递归扫描指定目录及其子目录下的所有 .pdf 文件"""
    pdf_files = []
    if not os.path.isdir(pdf_dir):
        print(f"错误: PDF 目录 '{pdf_dir}' 不存在或不是一个目录。")
        return []
    for root, _, files in os.walk(pdf_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))
    print(f"在 '{pdf_dir}' 中找到 {len(pdf_files)} 个 PDF 文件。")
    return pdf_files

if __name__ == "__main__":
    # 示例用法
    pdf_directory = r"PDF_Files"  # 替换为你的 PDF 目录
    pdf_files = find_pdf_files(pdf_directory)
    for pdf_file in pdf_files:
        print(pdf_file)