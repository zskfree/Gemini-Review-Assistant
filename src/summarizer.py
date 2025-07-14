import json
import os
import time
from typing import Dict, List, Optional, Any, Callable
from tqdm import tqdm # type: ignore

# 定义总结结果的类型
SummaryResult = Dict[str, Any]

def load_cache(cache_path: str) -> Dict[str, SummaryResult]:
    """加载缓存文件"""
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载缓存文件 '{cache_path}' 时出错: {e}")
    return {}

def save_cache(cache_path: str, cache_data: Dict[str, SummaryResult]):
    """保存缓存数据"""
    if not cache_path:  # 避免空路径
        print("警告: 缓存路径为空，跳过保存")
        return
        
    try:
        # 确保目录存在
        cache_dir = os.path.dirname(cache_path)
        if cache_dir:  # 只在非空目录时创建
            os.makedirs(cache_dir, exist_ok=True)
            
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存缓存文件 '{cache_path}' 时出错: {e}")

def process_all_pdfs(
    pdfs_to_process: List[str],
    ref_map: Dict[str, str],
    research_theme: str,
    summary_prompt_template: str,
    llm_api_func: Callable,
    model_name: str,
    api_key: Optional[str] = None,
    cache_path: str = "cache/summaries_cache.json",
    cache_enabled: bool = True,
    save_interval: int = 2,
    temperature: float = 1.2,
    max_retries: int = 3,
    progress_callback=None,
    **llm_kwargs
) -> List[SummaryResult]:
    """处理所有PDF文件并生成总结"""
    # 初始化变量
    all_summaries = []
    cache_data = load_cache(cache_path) if cache_enabled else {}
    total_files = len(pdfs_to_process)
    success_count = fail_count = skip_count = 0
    total_time = 0
    
    print(f"\n模型{model_name}, 开始处理文献总结...\n")
    with tqdm(total=total_files, desc="文献总结进度", unit="file") as pbar:
        for i, pdf_path in enumerate(pdfs_to_process):
            filename = os.path.basename(pdf_path)
            
            # 在这里调用进度回调
            if progress_callback:
                progress_callback(i, total_files, f"正在处理: {filename}")
            
            # 1. 检查引用信息
            if pdf_path not in ref_map:
                all_summaries.append({
                    "source_pdf_path": pdf_path,
                    "reference_string": "N/A",
                    "summary_markdown": None,
                    "status": "Skipped",
                    "error_message": "缺少引用信息",
                    "mtime": None,
                    "process_time": None
                })
                skip_count += 1
                pbar.update(1)
                continue
            
            # 2. 准备结果数据结构
            reference_string = ref_map[pdf_path]
            result_entry = {
                "source_pdf_path": pdf_path,
                "reference_string": reference_string,
                "summary_markdown": None,
                "status": "Pending",
                "error_message": None,
                "mtime": None,
                "process_time": None
            }
            
            # 3. 获取文件修改时间
            try:
                result_entry["mtime"] = os.path.getmtime(pdf_path)
            except Exception as e:
                result_entry["status"] = "Failure"
                result_entry["error_message"] = f"无法获取文件修改时间: {e}"
                all_summaries.append(result_entry)
                fail_count += 1
                pbar.update(1)
                continue
            
            # 4. 检查缓存 - 改为使用reference_string作为主键
            if cache_enabled and reference_string in cache_data:
                cached = cache_data[reference_string]
                # 检查文件是否存在且未修改
                cached_path = cached.get("source_pdf_path")
                if (cached_path and os.path.exists(cached_path) and 
                    cached.get("mtime") == result_entry["mtime"] and 
                    cached.get("status") == "Success"):
                    print(f"  命中缓存: '{filename}' (引用匹配且文件未修改)")
                    # 更新当前文件路径信息
                    cached["source_pdf_path"] = pdf_path
                    all_summaries.append(cached)
                    success_count += 1
                    if cached.get("process_time"):
                        total_time += cached["process_time"]
                    pbar.update(1)
                    continue
                elif (cached.get("status") == "Success" and 
                      cached.get("summary_markdown")):
                    # 文件可能已重命名，但总结仍然有效
                    print(f"  命中缓存: '{filename}' (引用匹配，使用已有总结)")
                    cached["source_pdf_path"] = pdf_path  # 更新文件路径
                    cached["mtime"] = result_entry["mtime"]  # 更新修改时间
                    all_summaries.append(cached)
                    success_count += 1
                    if cached.get("process_time"):
                        total_time += cached["process_time"]
                    pbar.update(1)
                    continue
            
            # 5. 准备LLM请求
            prompt = research_theme + "\n" + summary_prompt_template

            # 6. 调用LLM API
            start_time = time.time()
            summary_text, error_msg = llm_api_func(
                model_name=model_name,
                pdf_path=pdf_path,
                prompt_text=prompt,
                api_key=api_key,
                max_retries=max_retries,
                temperature=temperature,
                **llm_kwargs
            )
            
            # 7. 记录结果
            process_time = time.time() - start_time
            result_entry["process_time"] = round(process_time, 2)
            
            if summary_text:
                result_entry["summary_markdown"] = summary_text
                result_entry["status"] = "Success"
                success_count += 1
                total_time += result_entry["process_time"]
                print(f"  处理成功: '{filename}' (耗时: {result_entry['process_time']}秒)")
            else:
                result_entry["status"] = "Failure"
                result_entry["error_message"] = error_msg or "未知错误"
                fail_count += 1
                print(f"  处理失败: '{filename}' - {result_entry['error_message']}")
            
            all_summaries.append(result_entry)
            
            # 8. 更新缓存 - 改为使用reference_string作为主键
            if cache_enabled:
                cache_data[reference_string] = result_entry.copy()
                if (i + 1) % save_interval == 0:
                    save_cache(cache_path, cache_data)
                    pbar.set_description(f"文献总结进度 [成功:{success_count} 失败:{fail_count} 跳过:{skip_count}]")
            
            pbar.update(1)
    
    # 9. 最后保存一次缓存
    if cache_enabled:
        save_cache(cache_path, cache_data)
    
    # 10. 输出统计信息
    avg_time = round(total_time / max(success_count, 1), 2)
    print(f"\n文献总结处理完成。总计: {total_files} 篇, 成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}")
    print(f"平均处理时间: {avg_time} 秒/篇")

    # 确保最后调用一次回调，表示所有处理已完成
    if progress_callback:
        progress_callback(total_files-1, total_files, "所有文献处理完成") 
    
    return all_summaries


if __name__ == "__main__":
    # 示例用法
    from file_finder import find_pdf_files
    from reference_parser import parse_references
    from llm_api import call_llm_with_pdf
    from config_loader import load_config, load_all_prompts
    
    # 加载配置和提示词
    config = load_config()
    prompts = load_all_prompts(config)
    
    # 设置参数
    pdf_dir = config.get('paths', {}).get('pdf_dir', "PDF_Files")
    ref_file_path = config.get('paths', {}).get('ref_file', "TXT_Files/参考文献列表.txt")
    api_key = config['llm']['api_key']
    model_name = config['llm']['model_name']
    cache_path = config.get('paths', {}).get('cache_file', "cache/summaries.json")
    cache_enabled = config.get('cache', {}).get('enabled', True)
    research_theme = prompts['research_theme']
    summary_prompt_template = prompts['summary_prompt']
    
    # 获取PDF文件和引用信息
    pdf_files = find_pdf_files(pdf_dir)
    pdf_ref_map, missing_refs, missing_pdfs = parse_references(
        ref_file_path, pdf_files
    )
    
    # 处理PDF文献总结
    all_summaries = process_all_pdfs(
        pdfs_to_process=pdf_files,                                          # 要处理的PDF文件列表
        ref_map=pdf_ref_map,                                                # 引用映射
        research_theme=research_theme,                                      # 研究主题          
        summary_prompt_template=summary_prompt_template,                    # 文献总结提示词    
        llm_api_func=call_llm_with_pdf,                                     # LLM API调用函数
        model_name=model_name,                                              # LLM模型名称
        api_key=api_key,                                                    # API密钥
        cache_path=cache_path,                                              # 缓存文件路径              
        cache_enabled=cache_enabled,                                        # 是否启用缓存
        temperature=config.get('llm', {}).get('temperature', 1.2),          # 温度设置
        max_retries=config.get('llm', {}).get('max_retries', 3),            # # 重试次数
        save_interval=5                                                     # 每5篇保存一次缓存
    )