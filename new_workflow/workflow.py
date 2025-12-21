# new_workflow/workflow.py
"""
文献综述助手 - 主工作流
负责协调各个模块完成文献处理任务
"""
import os
import json
from src.config_loader import get_config, load_text_file
from src.pdf_processor import get_pdf_files
from src.reference_matcher import load_or_create_mapping
from src.summary_generator import batch_process_pdfs, save_summary_results
from src.prompts import get_summary_prompt
from src.results_exporter import export_from_json


def get_mapping_step():
    """第一步：获取文献映射关系"""
    pdf_folder_path = get_config("paths.pdf_folder")
    reference_file_path = get_config("paths.reference_file")
    reference_mapping_path = get_config("paths.reference_mapping")
    
    pdf_files = get_pdf_files(pdf_folder_path)
    if not pdf_files:
        return None, "未找到任何PDF文件"
    
    reference_mapping = load_or_create_mapping(
        reference_mapping_path, 
        pdf_files, 
        reference_file_path
    )
    return reference_mapping, None

def run_summary_step(reference_mapping=None, progress_callback=None): # 添加 progress_callback 参数
    """第二步：执行文献总结"""
    pdf_folder_path = get_config("paths.pdf_folder")
    research_topic_path = get_config("paths.research_topic_file")
    summary_save_path = get_config("paths.summary_save_path")
    reference_mapping_path = get_config("paths.reference_mapping")
    
    research_topic = load_text_file(research_topic_path)
    prompt_text = get_summary_prompt(research_topic)
    pdf_files = get_pdf_files(pdf_folder_path)
    
    # 如果没传 mapping，尝试从本地 JSON 文件加载
    if not reference_mapping:
        if os.path.exists(reference_mapping_path):
            try:
                with open(reference_mapping_path, "r", encoding="utf-8") as f:
                    reference_mapping = json.load(f)
            except Exception as e:
                print(f"加载映射文件失败: {e}")
        
        # 如果还是没有，则尝试重新生成（兜底逻辑）
        if not reference_mapping:
            reference_mapping, err = get_mapping_step()
            if err:
                return False, err
    
    if not reference_mapping:
        return False, "缺少文献映射关系，请先执行映射步骤"

    summary_results = batch_process_pdfs(
        pdf_files, 
        prompt_text, 
        reference_mapping,
        summary_save_path,
        progress_callback=progress_callback # 传递回调
    )
    
    # 注意：batch_process_pdfs 只返回本次新处理的结果
    # 如果所有文件都已处理过，summary_results 为空，但我们仍希望告知用户完成
    if summary_results or os.path.exists(summary_save_path):
        csv_path = r"new_workflow/txts_zsk/summary_sorted.csv"
        export_from_json(summary_save_path, csv_path)
        return True, "处理完成"
    
    return False, "没有找到需要处理的文件"

def run_workflow():
    """保留原有的完整工作流供命令行使用"""
    mapping, err = get_mapping_step()
    if err:
        print(err)
        return
    success, msg = run_summary_step(mapping)
    print(msg)

if __name__ == "__main__":
    run_workflow()
