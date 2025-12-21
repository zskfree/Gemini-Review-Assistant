# new_workflow/src/pdf_processor.py
"""PDF文件处理模块"""
import os
import glob
from typing import List

def get_pdf_files(pdf_folder_path: str) -> List[str]:
    """
    获取指定文件夹及其子目录中的所有PDF文件
    
    Args:
        pdf_folder_path: PDF文件夹路径
        
    Returns:
        PDF文件路径列表
    """
    pdf_files = []
    if os.path.exists(pdf_folder_path):
        # 使用glob递归查找所有.pdf文件
        pattern = os.path.join(pdf_folder_path, "**", "*.pdf")
        pdf_files = glob.glob(pattern, recursive=True)
    return pdf_files

if __name__ == "__main__":
    # 测试代码
    test_folder = "new_workflow/pdfs_zsk"
    pdfs = get_pdf_files(test_folder)
    print(f"Found {len(pdfs)} PDF files:")
    for pdf in pdfs:
        print(pdf)