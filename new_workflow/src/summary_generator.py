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
    加载已有的JSON结果文件，返回已处理成功的文献文件名集合和有效结果列表
    
    Args:
        output_file_path: 输出JSON文件路径
        
    Returns:
        (已成功处理的文件名集合, 已有的有效结果列表)
    """
    processed_files = set()
    valid_results = []
    
    if os.path.exists(output_file_path):
        try:
            with open(output_file_path, "r", encoding="utf-8") as json_file:
                existing_results = json.load(json_file)
                for entry in existing_results:
                    # 只有当没有错误信息且存在摘要内容时，才视为处理成功
                    if "error" not in entry and entry.get("summary"):
                        processed_files.add(entry.get("file_name"))
                        valid_results.append(entry)
        except Exception as e:
            print(f"加载已有结果文件失败: {e}")
    
    return processed_files, valid_results

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
    保存摘要结果到JSON文件，支持与已有结果合并（仅保存无错误的结果）
    """
    try:
        # 过滤掉包含错误的结果
        valid_new_results = [r for r in summary_results if "error" not in r]
        final_results = valid_new_results
        
        if merge_with_existing and os.path.exists(output_file_path):
            _, existing_valid_results = load_existing_results(output_file_path)
            final_results = existing_valid_results + valid_new_results
            print(f"合并结果：已有有效记录 {len(existing_valid_results)} 条，新增有效记录 {len(valid_new_results)} 条")
        
        with open(output_file_path, "w", encoding="utf-8") as json_file:
            json.dump(final_results, json_file, ensure_ascii=False, indent=4)
        print(f"摘要结果已保存到 {output_file_path}")
    except Exception as e:
        print(f"保存摘要结果失败: {e}")

def batch_process_pdfs(pdf_files: List[str], prompt_text: str, 
                      reference_mapping: Dict[str, str],
                      output_file_path: str,
                      progress_callback=None) -> List[Dict]:
    """
    批量处理PDF文件生成摘要，确保仅保存成功的结果以便断点续传
    """
    # 筛选有对应参考文献的文件
    matched_files = [f for f in pdf_files 
                    if reference_mapping.get(os.path.basename(f)) is not None]
    
    # 排除已成功处理的文件
    processed_files, valid_results = load_existing_results(output_file_path)
    matched_files = [f for f in matched_files 
                    if os.path.basename(f) not in processed_files]
    
    print(f"待处理的PDF文件数量: {len(matched_files)} (总文件数: {len(pdf_files)}, 已成功: {len(processed_files)})")
    
    total_to_process = len(matched_files)
    if progress_callback:
        progress_callback(0, total_to_process, "准备开始...")

    new_summary_results = []
    current_all_valid = valid_results.copy()

    for i, pdf_file_path in enumerate(tqdm(matched_files, desc="处理PDF文件", unit="个")):
        file_name = os.path.basename(pdf_file_path)
        if progress_callback:
            progress_callback(i, total_to_process, file_name)
        
        result = process_single_pdf(pdf_file_path, prompt_text, reference_mapping)
        
        # 核心优化：只有成功生成摘要且无错误时才保存
        if result and "error" not in result:
            result["file_index"] = len(current_all_valid) + 1
            new_summary_results.append(result)
            current_all_valid.append(result)
            
            # 边处理边保存有效结果，确保程序中断后已成功的不会丢失
            try:
                with open(output_file_path, "w", encoding="utf-8") as json_file:
                    json.dump(current_all_valid, json_file, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"实时保存结果失败 ({file_name}): {e}")
        else:
            error_msg = result.get("error") if result else "未知错误"
            print(f"\n[跳过] 文件 {file_name} 处理失败: {error_msg}")
    
    if progress_callback:
        progress_callback(total_to_process, total_to_process, "全部处理完成")
    return new_summary_results
