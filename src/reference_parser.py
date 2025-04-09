import os
import re
from typing import Dict, List, Tuple

def parse_references(ref_file_path: str, pdf_files_in_dir: List[str]) -> Tuple[Dict[str, str], List[str], List[str]]:
    """
    解析参考文献列表文件 (格式: 文件名.pdf: [GB/T 7714-2015 引用])。
    返回:
        - pdf_path_to_ref_map: PDF 绝对路径到引用字符串的映射字典。
        - missing_ref_entries: 在目录中找到但未在参考文献列表中提及的 PDF 文件名列表（去掉了文件夹前缀）。
        - missing_pdf_files: 在参考文献列表中提及但未在目录中找到的 PDF 文件名列表。
    """
    pdf_path_to_ref_map: Dict[str, str] = {}
    ref_filenames: set[str] = set()
    missing_pdf_files: List[str] = []

    if not os.path.exists(ref_file_path):
        print(f"错误: 参考文献列表文件 '{ref_file_path}' 未找到。")
        return {}, pdf_files_in_dir, []

    # 构建 PDF 文件名(去掉后缀)到完整路径的映射
    pdf_file_map = {os.path.splitext(os.path.basename(p))[0]: p for p in pdf_files_in_dir}

    try:
        with open(ref_file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                ref_filenames.add(line)
                # 遍历 PDF 文件名，检查是否被包含在参考文献条目中
                matched = False
                for pdf_name, pdf_path in pdf_file_map.items():
                    if pdf_name in line:  # 文件名是否被包含于参考文献条目
                        pdf_path_to_ref_map[pdf_path] = line
                        matched = True
                        break
                if not matched:
                    missing_pdf_files.append(line)
    except Exception as e:
        print(f"解析参考文献列表文件 '{ref_file_path}' 时出错: {e}")
        return {}, pdf_files_in_dir, list(ref_filenames)

    # 找出在目录中但不在参考文献列表中的 PDF，返回时只保留文件名(去掉.pdf后缀)
    missing_ref_entries = [os.path.splitext(os.path.basename(p))[0] for p in pdf_files_in_dir if p not in pdf_path_to_ref_map]

    print(f"\n成功匹配 {len(pdf_path_to_ref_map)} 个 PDF 文件与引用条目。")
    return pdf_path_to_ref_map, missing_ref_entries, missing_pdf_files

if __name__ == "__main__":
    # 示例用法
    from file_finder import find_pdf_files
    pdf_dir = r"PDF_Files"  # 替换为你的 PDF 目录
    ref_file_path = r"TXT_Files/参考文献列表.txt"  # 替换为你的参考文献列表文件路径

    pdf_files_in_dir = find_pdf_files(pdf_dir)
    pdf_path_to_ref_map, missing_ref_entries, missing_pdf_files = parse_references(ref_file_path, pdf_files_in_dir)
    print("\n ")
    print("PDF 文件到引用字符串的映射:")
    for pdf_path, ref in pdf_path_to_ref_map.items():
        print(f"{pdf_path}\n{ref}")

    print("\n ")
    print("在目录中找到但未在参考文献列表中提及的 PDF 文件名:")
    for entry in missing_ref_entries:
        print(entry)

    print("\n ")
    print("在参考文献列表中提及但未在目录中找到的 PDF 文件名:")
    for entry in missing_pdf_files:
        print(entry)