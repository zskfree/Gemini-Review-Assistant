# new_workflow/src/pdf_processor.py
"""PDF文件处理模块"""
import os
from typing import List

def get_pdf_files(pdf_folder_path: str) -> List[str]:
    """
    获取指定文件夹中的所有PDF文件
    
    Args:
        pdf_folder_path: PDF文件夹路径
        
    Returns:
        PDF文件路径列表
    """
    pdf_files = []
    if os.path.exists(pdf_folder_path):
        for file_name in os.listdir(pdf_folder_path):
            if file_name.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(pdf_folder_path, file_name))
    return pdf_files
