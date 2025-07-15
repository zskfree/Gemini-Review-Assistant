import os
import time
import json
from typing import List, Dict, Callable, Optional, Tuple, Any, Union

# 定义总结结果的类型
SummaryResult = Dict[str, Any]

def load_successful_summaries(cache_path: str) -> List[SummaryResult]:
    """
    从缓存文件中加载成功的文献总结
    
    Args:
        cache_path: 缓存文件路径
        
    Returns:
        List[SummaryResult]: 成功的文献总结列表
    """
    successful_summaries = []
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                successful_summaries = [
                    entry for entry in cache_data.values()
                    if entry.get('status') == 'Success' and entry.get('summary_markdown')
                ]
            print(f"已从缓存加载 {len(successful_summaries)} 篇成功的文献总结")
    except Exception as e:
        print(f"从缓存加载文献总结时出错: {e}")
    return successful_summaries

def prepare_final_prompt(
    successful_summaries: List[SummaryResult],
    research_theme: str,
    final_prompt_template: str,
) -> str:
    """
    构建用于生成最终文稿的提示词
    
    Args:
        successful_summaries: 成功生成的文献总结列表
        research_theme: 研究主题
        final_prompt_template: 最终提示词模板
        
    Returns:
        str: 格式化后的完整提示词
    """
    # 1. 检查是否有成功的总结
    if not successful_summaries:
        print("警告: 没有成功的文献总结可用于生成最终文稿")
        all_summaries_text = "未能成功获取任何文献的总结。"
    else:
        # 2. 格式化所有成功的总结
        formatted_summaries = []
        for i, summary_entry in enumerate(successful_summaries):
            ref = summary_entry.get("reference_string", "未知引用")
            summary_md = summary_entry.get("summary_markdown", "总结内容缺失")
            
            formatted_summaries.append(
                f"### 文献 {i+1}: {ref}\n\n**总结:**\n{summary_md}\n\n---\n"
            )
        
        all_summaries_text = "\n".join(formatted_summaries)

    # 4. 合并提示词
    try:
        final_prompt = all_summaries_text + "\n\n" + research_theme + "\n\n" + final_prompt_template
        return final_prompt
    except KeyError as e:
        print(f"错误: 提示词模板中缺少必要的占位符 {e}")
        # 提供一个后备模板
        return f"""
        # 研究综述：{research_theme}
        
        请基于以下文献总结，生成一份研究综述。
        
        ## 文献总结
        {all_summaries_text}
        """

def generate_final_draft(
    successful_summaries: List[SummaryResult],
    research_theme: str, 
    final_prompt_template: str,
    llm_api_func_text: Callable,
    model_name: str,
    api_key: Optional[str] = None,  # 保持参数，但默认为None
    output_file: Optional[str] = None,
    temperature: float = 1.2,
    max_retries: int = 3,
    **llm_kwargs
) -> Tuple[Optional[str], Optional[str]]:
    """
    生成最终研究综述文稿
    
    Args:
        successful_summaries: 成功生成的文献总结列表
        research_theme: 研究主题
        final_prompt_template: 最终提示词模板
        llm_api_func_text: 处理纯文本的LLM API函数 (llm_api.call_llm_text_only)
        model_name: LLM模型名称
        api_key: API密钥（可选，为None时使用全局客户端轮换）
        output_file: 输出文件路径（可选）
        temperature: LLM温度参数
        max_retries: 最大重试次数
        **llm_kwargs: 传递给LLM API的其他参数
        
    Returns:
        Tuple[Optional[str], Optional[str]]: (生成的文稿, 错误消息)
    """
    print("\n正在准备生成最终文稿...")
    print(f"API Key模式: {'指定API Key' if api_key else '全局客户端轮换'}")
    
    # 1. 构建最终提示词
    start_time = time.time()
    final_prompt = prepare_final_prompt(
        successful_summaries=successful_summaries,
        research_theme=research_theme,
        final_prompt_template=final_prompt_template,
    )
    
    # 2. 调用LLM API生成最终文稿
    print(f"提示词准备完成, 长度: {len(final_prompt)} 字符")
    print(f"\n模型{model_name}, 正在生成最终研究综述...")
    # print("最终提示词内容：", final_prompt)

    final_draft_text, error_msg = llm_api_func_text(
        model_name=model_name,
        prompt_text=final_prompt,
        api_key=api_key,  # 传递api_key，可能为None使用全局客户端
        max_retries=max_retries,
        temperature=temperature,
        **llm_kwargs
    )
    
    # 3. 处理生成结果
    if final_draft_text:
        process_time = time.time() - start_time
        print(f"最终文稿生成成功, 长度: {len(final_draft_text)} 字符, 耗时: {round(process_time, 2)}秒")
        
        # 4. 如果提供了输出文件路径，保存文稿
        if output_file:
            try:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(final_draft_text)
                print(f"最终文稿已保存到: {output_file}")
            except Exception as e:
                print(f"保存最终文稿时出错: {e}")
        
        return final_draft_text, None
    else:
        print(f"最终文稿生成失败: {error_msg}")
        return None, error_msg or "未知 LLM API 错误"

if __name__ == "__main__":
    # 示例用法
    from config_loader import load_config, load_all_prompts
    from llm_api import call_llm_text_only
    
    # 加载配置和提示词
    config = load_config()
    prompts = load_all_prompts(config)
    
    # 设置参数
    model_name = config['llm']['final_draft_model_name'] 
    # 使用None来启用全局客户端轮换，而不是直接从配置获取
    api_key = None  # 修改这里：使用None而不是从配置获取
    research_theme = prompts['research_theme']
    review_final_prompt = prompts['review_final_prompt']
    
    # 从缓存加载已生成的文献总结
    cache_path = config.get('paths', {}).get('cache_file', "cache/summaries.json")
    successful_summaries = load_successful_summaries(cache_path)

    # 设置输出文件
    output_file = config.get('paths', {}).get('final_output_file', "Results_Files/最终结果.txt")
    
    # 生成最终文稿
    final_draft, error = generate_final_draft(
        successful_summaries=successful_summaries,
        research_theme=research_theme,
        final_prompt_template=review_final_prompt,
        llm_api_func_text=call_llm_text_only,
        model_name=model_name,
        api_key=api_key,  # 传递None使用全局客户端
        output_file=output_file,
        temperature=config.get('llm', {}).get('temperature', 1.2),
        max_retries=config.get('llm', {}).get('max_retries', 3)
    )
    
    if final_draft:
        print("最终文稿生成完成!")
    else:
        print(f"最终文稿生成失败: {error}")
        