# new_workflow/workflow.py
"""
文献综述助手 - 主工作流
负责协调各个模块完成文献处理任务
"""
from src.config_loader import get_config, load_text_file
from src.pdf_processor import get_pdf_files
from src.reference_matcher import load_or_create_mapping
from src.summary_generator import batch_process_pdfs, save_summary_results
from src.prompts import get_summary_prompt

def run_workflow():
    """
    主工作流：处理所有PDF文件，生成文献总结并保存为JSON
    """
    # 加载配置
    pdf_folder_path = get_config("paths.pdf_folder")
    research_topic_path = get_config("paths.research_topic_file")
    reference_file_path = get_config("paths.reference_file")
    reference_mapping_path = get_config("paths.reference_mapping")
    summary_save_path = get_config("paths.summary_save_path")
    
    # 读取研究主题
    research_topic = load_text_file(research_topic_path)
    
    # 生成提示词
    prompt_text = get_summary_prompt(research_topic)
    
    # 获取PDF文件列表
    pdf_files = get_pdf_files(pdf_folder_path)
    if not pdf_files:
        print("未找到任何PDF文件")
        return
    
    print(f"找到 {len(pdf_files)} 个PDF文件")
    
    # 加载或创建参考文献映射
    reference_mapping = load_or_create_mapping(
        reference_mapping_path, 
        pdf_files, 
        reference_file_path
    )
    
    if not reference_mapping:
        print("无法创建参考文献映射，工作流终止")
        return
    
    # 批量处理PDF文件
    summary_results = batch_process_pdfs(
        pdf_files, 
        prompt_text, 
        reference_mapping,
        summary_save_path
    )
    
    # 保存结果
    if summary_results:
        save_summary_results(summary_results, summary_save_path)
        print(f"工作流完成！共处理 {len(summary_results)} 个文件")
    else:
        print("没有新的文件需要处理")

if __name__ == "__main__":
    run_workflow()
    