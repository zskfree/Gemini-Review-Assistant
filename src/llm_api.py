from google import genai  
from google.genai import types
import time
from typing import Tuple, Optional
try:
    from .config_loader import load_config  # 相对导入（模块使用时）
except ImportError:
    from config_loader import load_config   # 绝对导入（直接运行时）


# 全局变量
global_client = None

def initialize_global_client() -> Optional[genai.Client]:
    """
    初始化全局 Gemini API 客户端
    
    Returns:
        Optional[genai.Client]: 初始化成功返回客户端对象，否则返回 None
    """
    global global_client
    
    try:
        config = load_config()  # 加载配置文件
        api_key = config['llm']['api_key']  # 从配置中获取 API Key
        
        if api_key:
            global_client = genai.Client(api_key=api_key)
            print("Gemini API 已通过配置文件配置。")
            return global_client
        else:
            print("未找到 API Key 配置，请确保通过 config.yaml 或 .env 提供。")
            return None
            
    except Exception as e:
        print(f"初始化 Gemini API 客户端失败: {e}")
        return None

def get_global_client() -> Optional[genai.Client]:
    """
    获取全局客户端，如果未初始化则自动初始化
    
    Returns:
        Optional[genai.Client]: 客户端对象或 None
    """
    global global_client
    
    if global_client is None:
        global_client = initialize_global_client()
    
    return global_client

# 初始化全局客户端
initialize_global_client()

def call_llm_with_pdf(
    model_name: str,
    pdf_path: str,
    prompt_text: str,
    api_key: Optional[str] = None, # 允许传入 key，覆盖全局配置
    max_retries: int = 3,
    initial_delay: float = 1.0,
    temperature: float = 1.2,
) -> Tuple[Optional[str], Optional[str]]:
    """
    调用 Gemini API 处理单个 PDF 文件和提示词。
    假设 API (如此处的 Gemini SDK) 支持直接传入文件内容。

    返回: (生成的文本, 错误消息) 或 (None, 错误消息)
    """
    # 根据参数决定使用哪个客户端
    client = None
    if api_key:  # 如果传入了key，创建新客户端
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            return None, f"配置临时 API Key 失败: {e}"
    else:  # 使用全局客户端
        client = get_global_client()
        if client is None:
            return None, "Gemini API 未配置 API Key。"

    try:
        # 1. 上传 PDF 文件 (使用新的 files.upload 方法)
        try:
            pdf_file = client.files.upload(file=pdf_path)
        except Exception as e:
            return None, f"PDF 文件上传失败: {e}"

        # 2. 准备API调用
        contents = [prompt_text, pdf_file]  # 按照示例格式传入prompt和文件
        
        # 3. 调用 API 并处理重试
        for attempt in range(max_retries):
            try:
                print(f"  调用 LLM 总结文献... (尝试 {attempt + 1}/{max_retries})")
                
                generate_content_config = types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="text/plain",
                    thinking_config = types.ThinkingConfig(thinking_budget=-1,),
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=generate_content_config,
                )

                # 检查响应中的错误和阻止
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    if hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                        return None, f"Prompt 被阻止，原因: {response.prompt_feedback.block_reason}"
                
                # 检查内容生成状态
                if hasattr(response, 'candidates') and not response.candidates:
                     return None, "API 未返回任何候选内容。"
                
                if hasattr(response, 'candidates') and hasattr(response.candidates[0], 'finish_reason') and response.candidates[0].finish_reason != "STOP":
                     return None, f"内容生成未正常完成，原因: {response.candidates[0].finish_reason}"

                # 获取生成的文本
                if hasattr(response, 'text'):
                    return response.text.strip(), None  # 成功
                else:
                    # 尝试从其他结构中获取文本
                    if hasattr(response, 'candidates') and response.candidates:
                        if hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts'):
                            text_parts = [part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')]
                            if text_parts:
                                return "\n".join(text_parts).strip(), None
                    return None, "API 响应中未找到预期的文本内容。"

            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                
                # 检测常见的暂时性错误
                temporary_error_keywords = [
                    "deadline exceeded", "service unavailable", 
                    "resource exhausted", "internal server error",
                    "rate limit", "timeout", "503", "500", "429"
                ]
                
                is_temporary = any(keyword.lower() in error_message.lower() for keyword in temporary_error_keywords)
                
                if is_temporary:
                    print(f"  LLM API 调用暂时性错误 (尝试 {attempt + 1}): {error_type}: {error_message}")
                    if attempt == max_retries - 1:
                        return None, f"LLM API 暂时性错误，达到最大重试次数: {error_type}: {error_message}"
                    delay = initial_delay * (2 ** attempt) # 指数退避
                    print(f"  等待 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
                else:
                    # 处理其他API错误
                    print(f"  LLM API 调用失败 (尝试 {attempt + 1}): {error_type}: {error_message}")
                    return None, f"LLM API 错误: {error_type}: {error_message}"

    except FileNotFoundError:
        return None, f"PDF 文件未找到: {pdf_path}"
    except Exception as e:
        return None, f"准备调用 LLM 时出错: {e}"

    return None, "未知错误导致 LLM 调用失败" # Should not reach here normally

# --- 添加一个纯文本输入的版本 ---
def call_llm_text_only(
    model_name: str,
    prompt_text: str,
    api_key: Optional[str] = None,
    max_retries: int = 2,
    initial_delay: float = 2.0,
    temperature: float = 1.2,
) -> Tuple[Optional[str], Optional[str]]:
    """调用 Gemini API 处理纯文本输入。"""
    # 根据参数决定使用哪个客户端
    client = None
    if api_key:  # 如果传入了key，创建新客户端
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            return None, f"配置临时 API Key 失败: {e}"
    else:  # 使用全局客户端
        client = get_global_client()
        if client is None:
            return None, "Gemini API 未配置 API Key。"

    try:
        contents = prompt_text  # 纯文本输入

        for attempt in range(max_retries):
            try:
                print(f"  调用 LLM 进行最终文稿生成... (尝试 {attempt + 1}/{max_retries})")
                
                generate_content_config = types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="text/plain",
                    thinking_config=types.ThinkingConfig(thinking_budget=-1,),
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=generate_content_config,
                )

                # 检查响应中的错误和阻止
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    if hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                        return None, f"Prompt 被阻止，原因: {response.prompt_feedback.block_reason}"
                
                # 检查内容生成状态
                if hasattr(response, 'candidates') and not response.candidates:
                     return None, "API 未返回任何候选内容。"
                
                if hasattr(response, 'candidates') and hasattr(response.candidates[0], 'finish_reason') and response.candidates[0].finish_reason != "STOP":
                     return None, f"内容生成未正常完成，原因: {response.candidates[0].finish_reason}"

                # 获取生成的文本
                if hasattr(response, 'text'):
                    return response.text.strip(), None  # 成功
                else:
                    # 尝试从其他结构中获取文本
                    if hasattr(response, 'candidates') and response.candidates:
                        if hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts'):
                            text_parts = [part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')]
                            if text_parts:
                                return "\n".join(text_parts).strip(), None
                    return None, "API 响应中未找到预期的文本内容。"

            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                
                # 检测常见的暂时性错误
                temporary_error_keywords = [
                    "deadline exceeded", "service unavailable", 
                    "resource exhausted", "internal server error",
                    "rate limit", "timeout", "503", "500", "429"
                ]
                
                is_temporary = any(keyword.lower() in error_message.lower() for keyword in temporary_error_keywords)
                
                if is_temporary:
                    print(f"  LLM API 暂时性错误 (尝试 {attempt + 1}): {error_type}: {error_message}")
                    if attempt == max_retries - 1:
                        return None, f"LLM API 暂时性错误，达到最大重试次数: {error_type}: {error_message}"
                    delay = initial_delay * (2 ** attempt)
                    print(f"  等待 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
                else:
                    # 处理其他API错误
                    print(f"  LLM API 调用失败 (尝试 {attempt + 1}): {error_type}: {error_message}")
                    return None, f"LLM API 错误: {error_type}: {error_message}"

    except Exception as e:
        return None, f"准备调用 LLM (文本) 时出错: {e}"

    return None, "未知错误导致 LLM (文本) 调用失败"


if __name__ == "__main__":
    # 测试代码
    config = load_config()  # 直接调用，不需要再次导入
    temperature = config['llm']['temperature']  # 从配置中获取温度参数
    model_name = config['llm']['model_name']  # 从配置中获取模型名称
    pdf_path = r"PDF_Files\分离焦虑研究述评.pdf" 
    prompt_text = "请总结这篇文章的主要观点。"

    # PDF 文件处理测试
    result_pdf, error_pdf = call_llm_with_pdf(model_name, pdf_path, prompt_text, temperature=temperature)

    # 文本对话测试
    result_txt, error_txt = call_llm_text_only(model_name, prompt_text,temperature=temperature)

    if error_pdf or error_txt:
        print(f"错误: {error_pdf}")
        print(f"错误: {error_txt}")
    else:
        print(f"PDF 处理结果: {result_pdf} \n")
        print(f"文本对话结果: {result_txt}")