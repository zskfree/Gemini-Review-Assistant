import time
import os
from typing import Tuple, Optional, List
from google import genai  
from google.genai import types

try:
    from .config_loader import load_config  # 相对导入（模块使用时）
except ImportError:
    from config_loader import load_config   # 绝对导入（直接运行时）

# 错误检测函数
def is_quota_exceeded_error(error_message: str) -> bool:
    """
    检查错误信息是否表示配额超限
    """
    if not error_message:
        return False
    
    quota_keywords = [
        "quota exceeded", "quota_exceeded", "rate limit", "rate_limit",
        "too many requests", "resource exhausted", "usage limit",
        "billing", "quota", "limit exceeded", "429", "rate_limit_exceeded",
        "resource_exhausted", "quota_failure", "billing_not_active"
    ]
    error_lower = error_message.lower()
    return any(keyword in error_lower for keyword in quota_keywords)

def is_invalid_api_key_error(error_message: str) -> bool:
    """
    检查错误信息是否表示API Key无效
    """
    if not error_message:
        return False
    
    api_key_keywords = [
        "api key not valid", "invalid api key", "api_key_invalid",
        "invalid_api_key", "unauthorized", "authentication failed",
        "invalid key", "bad api key", "401", "403", "invalid_argument",
        "unauthenticated", "permission_denied", "invalid credentials"
    ]
    error_lower = error_message.lower()
    return any(keyword in error_lower for keyword in api_key_keywords)

def is_temporary_error(error_message: str) -> bool:
    """
    检查错误信息是否表示临时性错误
    """
    if not error_message:
        return False
    
    temporary_keywords = [
        "deadline exceeded", "service unavailable", "internal server error",
        "timeout", "503", "500", "502", "504", "connection reset",
        "connection refused", "network error", "temporary failure",
        "server overloaded", "try again later"
    ]
    error_lower = error_message.lower()
    return any(keyword in error_lower for keyword in temporary_keywords)

# 全局变量
global_clients = []
current_client_index = 0
failed_api_keys = set()  # 记录失败的 API Key
_clients_initialized = False  # 添加初始化标志

def initialize_global_clients() -> List[genai.Client]:
    """
    初始化全局 Gemini API 客户端列表
    """
    global global_clients, failed_api_keys, _clients_initialized
    
    # 如果已经初始化且有可用客户端，直接返回
    if _clients_initialized and global_clients:
        print(f"客户端已初始化，跳过重复初始化（共 {len(global_clients)} 个客户端）")
        return global_clients
    
    try:
        config = load_config()
        api_keys_str = config['llm']['api_key']
        
        print(f"正在初始化 API 客户端... 配置类型: {type(api_keys_str)}")
        
        # 更健壮的API Key解析
        if isinstance(api_keys_str, list):
            api_keys = [str(key).strip() for key in api_keys_str if str(key).strip()]
        elif isinstance(api_keys_str, str):
            if ',' in api_keys_str:
                # 处理逗号分隔的字符串
                api_keys = []
                for key in api_keys_str.split(','):
                    key = key.strip().strip('"').strip("'")
                    if key:  # 确保不是空字符串
                        api_keys.append(key)
            else:
                # 单个API Key
                key = api_keys_str.strip().strip('"').strip("'")
                api_keys = [key] if key else []
        else:
            print(f"不支持的API Key格式: {type(api_keys_str)}")
            return []
        
        if not api_keys:
            print("未找到有效的API Key")
            return []
            
        print(f"解析到 {len(api_keys)} 个 API Key，开始初始化...")
        
        global_clients = []
        failed_api_keys = set()
        successful_count = 0
        
        for i, api_key in enumerate(api_keys):
            try:
                client = genai.Client(api_key=api_key)
                global_clients.append(client)
                successful_count += 1
                print(f"API Key {i+1} 初始化成功")
                    
            except Exception as e:
                print(f"API Key {i+1} 初始化失败: {e}")
                failed_api_keys.add(api_key)
        
        if global_clients:
            print(f"成功初始化 {successful_count} 个 Gemini API 客户端")
            _clients_initialized = True  # 标记为已初始化
            return global_clients
        else:
            print("未能初始化任何有效的 API Key")
            return []
            
    except Exception as e:
        print(f"初始化 Gemini API 客户端失败: {e}")
        return []

def ensure_clients_initialized():
    """确保客户端已初始化"""
    global _clients_initialized
    if not _clients_initialized or not global_clients:
        initialize_global_clients()

def get_current_client() -> Optional[genai.Client]:
    """
    获取当前客户端（不轮换）
    
    Returns:
        Optional[genai.Client]: 当前客户端对象或 None
    """
    global global_clients, current_client_index
    
    ensure_clients_initialized()  # 确保已初始化
    
    if not global_clients:
        print("没有可用的客户端")
        return None
    
    # 返回当前客户端，不进行轮换
    client = global_clients[current_client_index]
    return client

def switch_to_next_client() -> Optional[genai.Client]:
    """
    切换到下一个客户端
    
    Returns:
        Optional[genai.Client]: 下一个客户端对象或 None
    """
    global global_clients, current_client_index
    
    if not global_clients:
        return None
    
    # 切换到下一个客户端
    current_client_index = (current_client_index + 1) % len(global_clients)
    print(f"切换到客户端 {current_client_index + 1}/{len(global_clients)}")
    
    return global_clients[current_client_index]

def call_llm_with_pdf(
    model_name: str,
    pdf_path: str,
    prompt_text: str,
    api_key: Optional[str] = None,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    temperature: float = 1.2,
) -> Tuple[Optional[str], Optional[str]]:
    """
    调用 Gemini API 处理单个 PDF 文件和提示词。
    智能API Key轮换：成功时继续使用当前API，失败时才切换。
    """
    global global_clients
    
    # 如果提供了特定的API Key，使用它
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            print(f"使用提供的API Key创建临时客户端")
        except Exception as e:
            return None, f"配置临时 API Key 失败: {e}"
        
        # 使用临时客户端处理
        return _process_with_single_client(client, model_name, pdf_path, prompt_text, 
                                         max_retries, initial_delay, temperature, 0)
    
    # 使用全局客户端列表
    ensure_clients_initialized()
    
    if not global_clients:
        return None, "没有可用的 Gemini API Key。"
    
    print(f"使用全局客户端，共 {len(global_clients)} 个可用")
    
    # 尝试所有客户端，从当前客户端开始
    clients_tried = 0
    max_clients_to_try = len(global_clients)
    
    while clients_tried < max_clients_to_try:
        current_client = get_current_client()
        if not current_client:
            return None, "无法获取可用客户端"
        
        client_index = current_client_index + 1
        print(f"尝试使用客户端 {client_index}/{len(global_clients)}")
        
        # 尝试当前客户端
        result, error = _process_with_single_client(
            current_client, model_name, pdf_path, prompt_text, 
            max_retries, initial_delay, temperature, client_index
        )
        
        if result is not None:
            # 成功，返回结果
            print(f"客户端 {client_index} 处理成功")
            return result, None
        
        # 失败，检查错误类型
        if error and (is_quota_exceeded_error(error) or is_invalid_api_key_error(error)):
            print(f"客户端 {client_index} 不可用: {error[:100]}...")
            # 切换到下一个客户端
            switch_to_next_client()
            clients_tried += 1
        else:
            # 其他错误，可能是临时性的，不切换客户端
            return None, error
    
    return None, "所有可用的 API Key 都无法完成请求"

def _process_with_single_client(
    client: genai.Client,
    model_name: str,
    pdf_path: str,
    prompt_text: str,
    max_retries: int,
    initial_delay: float,
    temperature: float,
    client_index: int
) -> Tuple[Optional[str], Optional[str]]:
    """
    使用单个客户端处理PDF
    """
    try:
        # 1. 上传 PDF 文件
        try:
            pdf_file = client.files.upload(file=pdf_path)
            print(f"PDF文件上传成功: {os.path.basename(pdf_path)}")
        except Exception as e:
            error_msg = str(e)
            print(f"客户端 {client_index} PDF上传失败: {error_msg}")
            return None, error_msg

        # 2. 准备API调用
        contents = [prompt_text, pdf_file]
        
        # 3. 调用 API 并处理重试
        for attempt in range(max_retries):
            try:
                print(f"  调用 LLM 总结文献... (客户端 {client_index}, 尝试 {attempt + 1}/{max_retries})")
                
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

                # 检查响应
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    if hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                        return None, f"Prompt 被阻止，原因: {response.prompt_feedback.block_reason}"
                
                if hasattr(response, 'candidates') and not response.candidates:
                    return None, "API 未返回任何候选内容。"
                
                if hasattr(response, 'candidates') and hasattr(response.candidates[0], 'finish_reason') and response.candidates[0].finish_reason != "STOP":
                    return None, f"内容生成未正常完成，原因: {response.candidates[0].finish_reason}"

                # 获取生成的文本
                if hasattr(response, 'text'):
                    return response.text.strip(), None
                else:
                    if hasattr(response, 'candidates') and response.candidates:
                        if hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts'):
                            text_parts = [part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')]
                            if text_parts:
                                return "\n".join(text_parts).strip(), None
                    return None, "API 响应中未找到预期的文本内容。"

            except Exception as e:
                error_message = str(e)
                print(f"  API调用异常 (客户端 {client_index}, 尝试 {attempt + 1}): {error_message}")
                
                # 检查是否为配额超限或API Key无效错误
                if is_quota_exceeded_error(error_message) or is_invalid_api_key_error(error_message):
                    return None, error_message
                
                # 检测暂时性错误
                temporary_error_keywords = [
                    "deadline exceeded", "service unavailable", 
                    "resource exhausted", "internal server error",
                    "timeout", "503", "500"
                ]
                
                is_temporary = any(keyword.lower() in error_message.lower() for keyword in temporary_error_keywords)
                
                if is_temporary and attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    print(f"  暂时性错误，等待 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
                else:
                    return None, f"API调用失败: {error_message}"

        return None, "达到最大重试次数"

    except FileNotFoundError:
        return None, f"PDF 文件未找到: {pdf_path}"
    except Exception as e:
        return None, f"处理PDF时出错: {e}"

def call_llm_text_only(
    model_name: str,
    prompt_text: str,
    api_key: Optional[str] = None,
    max_retries: int = 2,
    initial_delay: float = 2.0,
    temperature: float = 1.2,
) -> Tuple[Optional[str], Optional[str]]:
    """调用 Gemini API 处理纯文本输入。智能API Key轮换。"""
    global global_clients
    
    # 如果提供了特定的API Key，使用它
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            return None, f"配置临时 API Key 失败: {e}"
        
        # 使用临时客户端处理
        return _process_text_with_single_client(client, model_name, prompt_text, 
                                              max_retries, initial_delay, temperature, 0)
    
    # 使用全局客户端列表
    ensure_clients_initialized()
    
    if not global_clients:
        return None, "没有可用的 Gemini API Key。"
    
    # 尝试所有客户端，从当前客户端开始
    clients_tried = 0
    max_clients_to_try = len(global_clients)
    
    while clients_tried < max_clients_to_try:
        current_client = get_current_client()
        if not current_client:
            return None, "无法获取可用客户端"
        
        client_index = current_client_index + 1
        
        # 尝试当前客户端
        result, error = _process_text_with_single_client(
            current_client, model_name, prompt_text, 
            max_retries, initial_delay, temperature, client_index
        )
        
        if result is not None:
            # 成功，返回结果
            return result, None
        
        # 失败，检查错误类型
        if error and (is_quota_exceeded_error(error) or is_invalid_api_key_error(error)):
            print(f"客户端 {client_index} 不可用，切换下一个...")
            # 切换到下一个客户端
            switch_to_next_client()
            clients_tried += 1
        else:
            # 其他错误，可能是临时性的，不切换客户端
            return None, error
    
    return None, "所有可用的 API Key 都无法完成请求"

def _process_text_with_single_client(
    client: genai.Client,
    model_name: str,
    prompt_text: str,
    max_retries: int,
    initial_delay: float,
    temperature: float,
    client_index: int
) -> Tuple[Optional[str], Optional[str]]:
    """
    使用单个客户端处理纯文本
    """
    try:
        contents = prompt_text

        for attempt in range(max_retries):
            try:
                print(f"  调用 LLM 文本处理... (客户端 {client_index}, 尝试 {attempt + 1}/{max_retries})")
                
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
                    return response.text.strip(), None
                else:
                    # 尝试从其他结构中获取文本
                    if hasattr(response, 'candidates') and response.candidates:
                        if hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts'):
                            text_parts = [part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')]
                            if text_parts:
                                return "\n".join(text_parts).strip(), None
                    return None, "API 响应中未找到预期的文本内容。"

            except Exception as e:
                error_message = str(e)
                print(f"  API调用异常 (客户端 {client_index}, 尝试 {attempt + 1}): {error_message}")
                
                # 检查是否为配额超限或API Key无效错误
                if is_quota_exceeded_error(error_message) or is_invalid_api_key_error(error_message):
                    return None, error_message
                
                # 检测常见的暂时性错误
                if is_temporary_error(error_message) and attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    print(f"  暂时性错误，等待 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
                else:
                    return None, f"API调用失败: {error_message}"

        return None, "达到最大重试次数"

    except Exception as e:
        return None, f"处理文本时出错: {e}"


if __name__ == "__main__":
    # 测试代码
    config = load_config()  # 直接调用，不需要再次导入
    temperature = config['llm']['temperature']  # 从配置中获取温度参数
    model_name = config['llm']['model_name']  # 从配置中获取模型名称
    pdf_path = r"PDF_Files_zsk\股票市场与债券市场的风险联动与预测研究——基于机器学习的前沿视角.pdf" 
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