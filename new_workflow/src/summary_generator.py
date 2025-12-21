# new_workflow/src/summary_generator.py
"""文献摘要生成模块"""
import json
import os
from typing import Dict, List, Optional, Set, Tuple
from tqdm import tqdm
from .llm_client import LLMClient
from .config_loader import get_config

def load_existing_results(output_file_path: str) -> Tuple[Set[str], List[Dict]]:
    """
    加载已有的JSON结果文件，返回已处理的文件名集合和完整结果列表
    
    Args:
        output_file_path: 输出JSON文件路径
        
    Returns:
        (已处理的文件名集合, 已有的完整结果列表)
    """
    processed_files = set()
    existing_results = []
    
    if os.path.exists(output_file_path):
        try:
            with open(output_file_path, "r", encoding="utf-8") as json_file:
                existing_results = json.load(json_file)
                for entry in existing_results:
                    processed_files.add(entry.get("file_name"))
        except Exception as e:
            print(f"加载已有结果文件失败: {e}")
    
    return processed_files, existing_results

def process_single_pdf(pdf_file_path: str, prompt_text: str, 
                      reference_mapping: Dict[str, str]) -> Optional[Dict]:
    """
    处理单个PDF文件并生成摘要
    
    Args:
        pdf_file_path: PDF文件路径
        prompt_text: 用于总结的提示词文本
        reference_mapping: 文件名到参考文献的映射
        
    Returns:
        包含处理结果的字典，如果没有对应参考文献则返回None
    """
    llm = LLMClient(provider=get_config("model.literature_summary.provider"), 
                    model=get_config("model.literature_summary.model_name"),
                    temperature=get_config("model.literature_summary.temperature"))
    file_name = os.path.basename(pdf_file_path)
    
    # 检查是否有对应的参考文献
    if reference_mapping.get(file_name) is None:
        return None
    
    # 生成摘要
    summary_text = llm.generate(prompt=prompt_text, file_path=pdf_file_path)
    
    result_entry = {
        "file_path": pdf_file_path,
        "file_name": file_name,
        "reference": reference_mapping.get(file_name),
        "summary": summary_text
    }
    
    # 错误检查
    if summary_text.startswith("Error") or summary_text.startswith("LLM Generation Error"):
        result_entry["error"] = summary_text
    
    return result_entry

def save_summary_results(summary_results: List[Dict], output_file_path: str, 
                        merge_with_existing: bool = True):
    """
    保存摘要结果到JSON文件，支持与已有结果合并
    
    Args:
        summary_results: 新的摘要结果列表
        output_file_path: 输出文件路径
        merge_with_existing: 是否与已有结果合并（默认True）
    """
    try:
        final_results = summary_results
        
        # 如果需要合并，先加载已有结果
        if merge_with_existing and os.path.exists(output_file_path):
            try:
                with open(output_file_path, "r", encoding="utf-8") as json_file:
                    existing_results = json.load(json_file)
                
                # 合并：已有结果 + 新结果
                final_results = existing_results + summary_results
                print(f"合并结果：已有 {len(existing_results)} 条，新增 {len(summary_results)} 条，总计 {len(final_results)} 条")
            except Exception as e:
                print(f"加载已有结果失败，将仅保存新结果: {e}")
        
        # 保存合并后的结果
        with open(output_file_path, "w", encoding="utf-8") as json_file:
            json.dump(final_results, json_file, ensure_ascii=False, indent=4)
        print(f"摘要结果已保存到 {output_file_path}")
    except Exception as e:
        print(f"保存摘要结果失败: {e}")

def batch_process_pdfs(pdf_files: List[str], prompt_text: str, 
                      reference_mapping: Dict[str, str],
                      output_file_path: str,
                      progress_callback=None) -> List[Dict]: # 添加 progress_callback 参数
    """
    批量处理PDF文件生成摘要
    
    Args:
        pdf_files: PDF文件路径列表
        prompt_text: 提示词文本
        reference_mapping: 参考文献映射
        output_file_path: 输出文件路径
        
    Returns:
        新生成的摘要结果列表（不包含已有结果）
    """
    # 筛选有对应参考文献的文件
    matched_files = [f for f in pdf_files 
                    if reference_mapping.get(os.path.basename(f)) is not None]
    
    # 排除已处理的文件
    processed_files, existing_results = load_existing_results(output_file_path)
    matched_files = [f for f in matched_files 
                    if os.path.basename(f) not in processed_files]
    
    print(f"待处理的PDF文件数量: {len(matched_files)} (总文件数: {len(pdf_files)}, 已处理: {len(processed_files)})")
    
    total_to_process = len(matched_files)
    if progress_callback:
        progress_callback(0, total_to_process, "准备开始...")

    summary_results = []
    for i, pdf_file_path in enumerate(tqdm(matched_files, desc="处理PDF文件", unit="个")):
        file_name = os.path.basename(pdf_file_path)
        # 在处理每个文件前调用回调
        if progress_callback:
            progress_callback(i, total_to_process, file_name)
        
        result = process_single_pdf(pdf_file_path, prompt_text, reference_mapping)
        if result:
            result["file_index"] = len(processed_files) + i + 1  # 基于总数的索引
            summary_results.append(result)
            
            # 边处理边保存
            try:
                # 直接将当前结果追加到文件中
                if os.path.exists(output_file_path):
                    with open(output_file_path, "r", encoding="utf-8") as json_file:
                        file_data = json.load(json_file)
                else:
                    file_data = existing_results
                
                file_data.append(result)
                
                with open(output_file_path, "w", encoding="utf-8") as json_file:
                    json.dump(file_data, json_file, ensure_ascii=False, indent=4)
                    
            except Exception as e:
                print(f"保存单个结果失败 ({pdf_file_path}): {e}")
    
    if progress_callback:
        progress_callback(total_to_process, total_to_process, "全部处理完成")
    return summary_results
