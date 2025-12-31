# new_workflow/src/summary_generator.py
"""文献摘要生成模块"""
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set, Tuple
from tqdm import tqdm
from .llm_client import LLMClient
from .config_loader import get_config
from .logger import logger

# 用于保护文件写入的锁
file_lock = threading.Lock()

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
                logger.info(f"正在加载已有结果文件: {output_file_path}, 共 {len(existing_results)} 条记录")
                for entry in existing_results:
                    # 只有当没有错误信息且存在摘要内容时，才视为处理成功
                    if "error" not in entry and entry.get("summary"):
                        processed_files.add(entry.get("file_name"))
                        valid_results.append(entry)
                logger.info(f"有效已完成记录: {len(processed_files)} 条")
        except Exception as e:
            logger.error(f"加载已有结果文件失败 ({output_file_path}): {e}")
    else:
        logger.info(f"已有结果文件不存在: {output_file_path}，将创建新文件")
    
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
    import time
    start_time = time.time()
    
    # 每个线程需要独立的 LLMClient 实例（如果是基于 requests 的可能是线程安全的，但为了安全起见）
    # 大多数 HTTP 客户端实现都是线程安全的，这里假设 LLMClient 是安全的。
    # 实际上，requests Session 是线程安全的。
    llm = LLMClient(provider=get_config("model.literature_summary.provider"), 
                    model=get_config("model.literature_summary.model_name"),
                    temperature=get_config("model.literature_summary.temperature"))
    file_name = os.path.basename(pdf_file_path)
    
    # 检查是否有对应的参考文献
    if reference_mapping.get(file_name) is None:
        return None
    
    result_entry = {
        "file_path": pdf_file_path,
        "file_name": file_name,
        "reference": reference_mapping.get(file_name),
        "summary": ""
    }
    
    # 生成摘要
    try:
        summary_text = llm.generate(prompt=prompt_text, file_path=pdf_file_path)
        result_entry["summary"] = summary_text
        
        # 错误检查
        if summary_text.startswith("Error") or summary_text.startswith("LLM Generation Error"):
            result_entry["error"] = summary_text
            
    except Exception as e:
        result_entry["error"] = str(e)
        logger.error(f"处理文件 {file_name} 时发生异常: {e}")

    elapsed = time.time() - start_time
    result_entry["elapsed_time"] = elapsed
    logger.debug(f"文件 {file_name} 处理耗时: {elapsed:.2f}s")
    
    return result_entry

def save_summary_results(summary_results: List[Dict], output_file_path: str, 
                        merge_with_existing: bool = True):
    """
    保存摘要结果到JSON文件，支持与已有结果合并（仅保存无错误的结果）
    """
    with file_lock:
        try:
            # 过滤掉包含错误的结果
            valid_new_results = [r for r in summary_results if "error" not in r]
            final_results = valid_new_results
            
            if merge_with_existing and os.path.exists(output_file_path):
                # 这里不能直接调用 public 的 load_existing_results，因为它没有锁保护读
                # 但由于我们就在锁内，所以直接读写是安全的（假设其他地方也遵守锁）
                # 为了复用逻辑，我们临时在这里做
                try:
                    with open(output_file_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                        # 简单的合并：过滤掉 error 的
                        existing_valid = [r for r in existing if "error" not in r and r.get("summary")]
                        final_results = existing_valid + valid_new_results
                        logger.info(f"合并结果：已有有效记录 {len(existing_valid)} 条，新增有效记录 {len(valid_new_results)} 条")
                except Exception as e:
                    logger.error(f"合并读取时出错: {e}")
                    # 如果读取失败，可能文件坏了，那就只保存新的（或者抛出）
                    # 这里选择继续保存新的，避免丢失
            
            with open(output_file_path, "w", encoding="utf-8") as json_file:
                json.dump(final_results, json_file, ensure_ascii=False, indent=4)
            logger.info(f"摘要结果已保存到 {output_file_path}")
        except Exception as e:
            logger.error(f"保存摘要结果失败: {e}")

def batch_process_pdfs(pdf_files: List[str], prompt_text: str, 
                      reference_mapping: Dict[str, str],
                      output_file_path: str,
                      progress_callback=None) -> List[Dict]:
    """
    批量处理PDF文件生成摘要，使用线程池并发处理
    """
    # 筛选有对应参考文献的文件
    matched_files = [f for f in pdf_files 
                    if reference_mapping.get(os.path.basename(f)) is not None]
    
    # 排除已成功处理的文件
    processed_files, valid_results = load_existing_results(output_file_path)
    matched_files = [f for f in matched_files 
                    if os.path.basename(f) not in processed_files]
    
    logger.info(f"待处理的PDF文件数量: {len(matched_files)} (总文件数: {len(pdf_files)}, 已成功: {len(processed_files)})")
    
    total_to_process = len(matched_files)
    if progress_callback:
        progress_callback(0, total_to_process, "准备开始并发处理...")

    new_summary_results = []
    current_all_valid = valid_results.copy()
    
    # 从配置读取并发数，默认为 3
    max_workers = get_config("concurrency.max_workers", 3)
    logger.info(f"启动并发处理，最大线程数: {max_workers}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_file = {
            executor.submit(process_single_pdf, pdf_path, prompt_text, reference_mapping): pdf_path 
            for pdf_path in matched_files
        }
        
        completed_count = 0
        
        for future in as_completed(future_to_file):
            pdf_path = future_to_file[future]
            file_name = os.path.basename(pdf_path)
            completed_count += 1
            
            if progress_callback:
                progress_callback(completed_count, total_to_process, f"完成: {file_name}")
            
            try:
                result = future.result()
                
                # 线程安全地处理结果保存
                if result and "error" not in result:
                    with file_lock:
                        result["file_index"] = len(current_all_valid) + 1
                        new_summary_results.append(result)
                        current_all_valid.append(result)
                        
                        # 边处理边保存有效结果
                        try:
                            with open(output_file_path, "w", encoding="utf-8") as json_file:
                                json.dump(current_all_valid, json_file, ensure_ascii=False, indent=4)
                        except Exception as e:
                            logger.error(f"实时保存结果失败 ({file_name}): {e}")
                    
                    logger.info(f"[✓] {file_name} 处理成功")
                else:
                    error_msg = result.get("error") if result else "未知错误"
                    logger.warning(f"[✗] {file_name} 处理失败: {error_msg}")
                    
            except Exception as e:
                logger.error(f"任务执行异常 ({file_name}): {e}")

    if progress_callback:
        progress_callback(total_to_process, total_to_process, "全部处理完成")
    
    return new_summary_results
