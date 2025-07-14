import os
from typing import List, Dict

SummaryResult = Dict[str, str | float | None] # Assuming definition

def display_welcome():
    print("=" * 40)
    print("   欢迎使用文献综述/定性研究辅助工具")
    print("=" * 40)

def select_pdfs_to_process(all_pdf_paths: List[str], ref_map: Dict[str, str]) -> List[str]:
    """让用户选择要处理的 PDF 文件"""
    print("\n发现以下 PDF 文件:")
    valid_options = {}
    for i, pdf_path in enumerate(all_pdf_paths):
        filename = os.path.basename(pdf_path)
        ref_status = "✓" if pdf_path in ref_map else "✗ (无引用)"
        print(f"  {i + 1}: {filename} [{ref_status}]")
        valid_options[str(i + 1)] = pdf_path

    while True:
        choice = input(f"\n请输入要处理的文件编号 (用逗号分隔, e.g., 1,3,5) 或输入 'all' 处理全部匹配引用的文件, 'q' 退出: ").strip().lower()
        if choice == 'q':
            print("用户选择退出。")
            return []
        if choice == 'all':
            selected_paths = [p for p in all_pdf_paths if p in ref_map]
            print(f"已选择全部 {len(selected_paths)} 个具有引用信息的 PDF 文件。")
            return selected_paths

        selected_indices = choice.split(',')
        selected_paths = []
        valid_choice = True
        for index_str in selected_indices:
            index_str = index_str.strip()
            if index_str in valid_options:
                 # 只有在引用存在时才加入选择列表（除非用户强制要求）
                pdf_path_chosen = valid_options[index_str]
                if pdf_path_chosen in ref_map:
                    selected_paths.append(pdf_path_chosen)
                else:
                    print(f"警告: 文件 '{os.path.basename(pdf_path_chosen)}' 缺少引用信息，将不会被处理。")
            else:
                print(f"错误: 无效的编号 '{index_str}'。")
                valid_choice = False
                break
        if valid_choice and selected_paths:
            print(f"\n已选择以下文件进行处理:")
            for p in selected_paths:
                print(f"- {os.path.basename(p)}")
            return selected_paths
        elif valid_choice and not selected_paths:
             print("没有选择任何包含引用信息的文件。")
             # Loop again
        else:
            print("请重新输入。")


def display_summaries(summaries: List[SummaryResult]):
    """向用户展示已生成的文献总结"""
    print("\n--- 文献总结结果 ---")
    successful_count = 0
    failed_count = 0
    skipped_count = 0
    for i, result in enumerate(summaries):
        status = result.get('status', 'Unknown')
        filename = os.path.basename(result.get('source_pdf_path', '未知文件'))
        print(f"\n{i + 1}. 文件: {filename}")
        print(f"   状态: {status}")
        if status == 'Success':
            successful_count += 1
            print(f"   引用: {result.get('reference_string', 'N/A')}")
            summary_preview = result.get('summary_markdown', '无总结内容')
            print(f"   总结预览:\n     {summary_preview[:200]}...") # 显示部分预览
        elif status == 'Failure':
            failed_count += 1
            print(f"   错误: {result.get('error_message', '未知错误')}")
        elif status == 'Skipped':
             skipped_count += 1
             print(f"   原因: {result.get('error_message', '被跳过')}")

    print("\n--- 总结统计 ---")
    print(f"成功: {successful_count}")
    print(f"失败: {failed_count}")
    print(f"跳过: {skipped_count}")
    print("-" * 20)


def confirm_final_generation(summaries: List[SummaryResult]) -> bool:
    """询问用户是否继续生成最终文稿"""
    successful_summaries = [s for s in summaries if s.get('status') == 'Success']
    if not successful_summaries:
        print("\n没有成功的文献总结，无法生成最终文稿。")
        return False

    while True:
        choice = input(f"\n基于 {len(successful_summaries)} 篇成功的总结，是否继续生成最终文稿? (yes/no): ").strip().lower()
        if choice == 'yes':
            return True
        elif choice == 'no':
            print("用户选择不生成最终文稿。")
            return False
        else:
            print("请输入 'yes' 或 'no'。")


def select_final_output_type() -> str:
    """让用户选择最终输出类型"""
    while True:
        print("\n请选择最终输出类型:")
        print("  1: 文献综述 (Literature Review)")
        print("  2: 定性研究论文")
        choice = input("请输入选项编号 (1 或 2): ").strip()
        if choice == '1':
            return 'review'
        elif choice == '2':
            return 'qualitative'
        else:
            print("无效选项，请输入 1 或 2。")

def save_results(output_path: str, content: str):
    """保存最终结果到文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n结果已成功保存到: {output_path}")
    except Exception as e:
        print(f"\n错误: 保存结果到 '{output_path}' 失败: {e}")