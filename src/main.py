import os
import sys
import json

# 确保 src 目录在 Python 路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src import config_loader, file_finder, reference_parser, llm_api, summarizer, final_generator, user_interface

def main():
    """主程序入口"""
    user_interface.display_welcome()

    # --- 1. 加载配置与检查 ---
    try:
        config = config_loader.load_config("config.yaml")
        prompts = config_loader.load_all_prompts(config)
        api_key = config.get('llm', {}).get('api_key') or os.getenv("GEMINI_API_KEY")
        if not api_key or not all([prompts.get('research_theme'), prompts.get('summary_prompt')]):
            raise ValueError("配置文件或环境变量缺失必要信息")
    except Exception as e:
        print(f"初始化配置失败: {e}")
        return 1

    # --- 2. 文献扫描与用户选择 ---
    pdf_dir = config['paths']['pdf_dir']
    all_pdf_files = file_finder.find_pdf_files(pdf_dir)
    if not all_pdf_files:
        print(f"在 '{pdf_dir}' 中未找到任何 PDF 文件。程序退出。")
        return 1

    ref_list_path = os.path.join(config['paths']['txt_dir'], config['prompts']['references_list_file'])
    pdf_to_ref_map, _, _ = reference_parser.parse_references(ref_list_path, all_pdf_files)
    if not pdf_to_ref_map:
        print("未能成功匹配任何 PDF 文件和引用条目。程序退出。")
        return 1

    selected_pdf_paths = user_interface.select_pdfs_to_process(list(pdf_to_ref_map.keys()), pdf_to_ref_map)
    if not selected_pdf_paths:
        print("未选择任何文件。程序退出。")
        return 0

    # --- 3. 文献总结 ---
    all_summaries = summarizer.process_all_pdfs(
        pdfs_to_process=selected_pdf_paths,
        ref_map=pdf_to_ref_map,
        research_theme=prompts['research_theme'],
        summary_prompt_template=prompts['summary_prompt'],
        llm_api_func=llm_api.call_llm_with_pdf,
        api_key=api_key,
        model_name=config['llm'].get('model_name', 'gemini-2.0-flash-thinking-exp-01-21'),
        cache_path=config['paths']['cache_file'],
        cache_enabled=config.get('cache', {}).get('enabled', True),
        **{k: v for k, v in config['llm'].items() if k not in ['model_name', 'api_key', 'request_timeout']}
    )

    summary_output_path = config['paths']['summary_output_file']
    os.makedirs(os.path.dirname(summary_output_path), exist_ok=True)
    with open(summary_output_path, 'w', encoding='utf-8') as f:
        json.dump(all_summaries, f, ensure_ascii=False, indent=4)
    print(f"\n文献总结结果已保存到: {summary_output_path}")

    # user_interface.display_summaries(all_summaries)   # 显示总结结果
    if not user_interface.confirm_final_generation(all_summaries):
        print("\n程序结束。")
        return 0

    # --- 4. 最终文稿生成 ---
    final_output_type = user_interface.select_final_output_type()
    final_prompt_template = prompts.get(f"{final_output_type}_final_prompt")
    if not final_prompt_template:
        print(f"错误：未找到类型 '{final_output_type}' 对应的最终生成提示词。程序退出。")
        return 1

    final_draft, error_msg = final_generator.generate_final_draft(
        successful_summaries=[s for s in all_summaries if s.get('status') == 'Success'],
        research_theme=prompts['research_theme'],
        final_prompt_template=final_prompt_template,
        llm_api_func_text=llm_api.call_llm_text_only,
        model_name=config['llm'].get('final_draft_model_name', config['llm'].get('model_name')),
        api_key=api_key,
        output_file=config['paths']['final_output_file'],
        temperature=config['llm'].get('temperature', 1.2),  # 添加明确的参数
        max_retries=config['llm'].get('max_retries', 3)    # 添加明确的参数
    )

    if final_draft:
        print("\n所有任务完成！")
    else:
        print(f"\n最终文稿生成失败。错误信息: {error_msg}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())