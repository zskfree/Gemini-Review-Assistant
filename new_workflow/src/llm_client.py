# llm_client.py
import base64
import os
from google import genai
from google.genai import types
import time
from typing import Optional, Union, List
from .config_loader import get_config

PROXY_URL = get_config("proxy.url", "")
if PROXY_URL:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL

class LLMClient:
    """
    统一的大模型交互客户端，支持 Google GenAI、OpenAI 和智谱AI接口。
    设计用于方便扩展其他模型接口。
    """
    def __init__(self, provider=None, api_key=None, model=None, temperature=None):
        """
        初始化 LLM 客户端
        
        Args:
            api_key (str, optional): API 密钥
            model (str, optional): 模型名称
            temperature (float, optional): 温度参数
            provider (str): 提供商类型，支持 "gemini"、"openai" 或 "zhipu"
        """
        if provider is None:
            provider = "zhipu"
        self.provider = provider.lower()
        
        # 获取配置
        if self.provider == "gemini":
            self.api_key = api_key or get_config("api.genai_key")
            self.base_url = get_config("api.genai_base_url", None)
            self.model = model or get_config("api.genai_model", "gemini-flash-lite-latest")

        elif self.provider == "openai":
            self.api_key = api_key or get_config("api.openai_key")
            self.base_url = get_config("api.openai_base_url", "https://openrouter.ai/api/v1/")
            self.model = model or get_config("api.openai_model", "gemini-flash-lite-latest")
        
        elif self.provider == "zhipu":
            self.api_key = api_key or get_config("api.zhipu_key")
            self.model = model or get_config("api.zhipu_model", "glm-4.5-flash")
            self.enable_thinking = get_config("api.zhipu_enable_thinking", True)
        
        else:
            raise ValueError(f"不支持的提供商: {self.provider}")
        
        self.temperature = temperature if temperature is not None else get_config("api.default_temperature", 0.2)
        self.max_retries = get_config("api.max_retries", 3)
        
        # 初始化客户端
        if self.provider == "gemini":
            if not self.api_key:
                raise ValueError("未找到 Gemini API 密钥，请检查配置文件")
            if self.base_url:
                self.client = genai.Client(api_key=self.api_key, http_options={"base_url": self.base_url})
            else:
                self.client = genai.Client(api_key=self.api_key)

        elif self.provider == "openai":
            if not self.api_key or self.api_key == "your-openai-key":
                raise ValueError("未找到 OpenAI API 密钥，请检查配置文件")
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise ImportError("请安装 openai 库: pip install openai")
        
        elif self.provider == "zhipu":
            if not self.api_key or self.api_key == "your-zhipu-key":
                raise ValueError("未找到智谱AI API 密钥，请检查配置文件")
            try:
                from zai import ZhipuAiClient
                self.client = ZhipuAiClient(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 zai 库: pip install zai")
        
        else:
            raise ValueError(f"不支持的提供商: {self.provider}")

    def _normalize_file_paths(self, file_path: Union[str, List[str], None]) -> List[str]:
        """
        统一处理文件路径参数，转换为列表形式
        
        Args:
            file_path: 单个文件路径(str)、多个文件路径(list)或None
            
        Returns:
            List[str]: 文件路径列表
        """
        if file_path is None:
            return []
        if isinstance(file_path, str):
            return [file_path]
        return file_path

    def generate(self, prompt: str, file_path: Union[str, List[str], None] = None) -> str:
        """
        统一生成接口，自动根据 provider 调用对应方法
        
        Args:
            prompt (str): 提示词文本
            file_path (Union[str, List[str], None]): 单个文件路径或多个文件路径列表
            
        Returns:
            str: 模型生成的文本内容
        """
        if self.provider == "gemini":
            return self.generate_with_gemini(prompt, file_path)
        elif self.provider == "openai":
            return self.generate_with_openai(prompt, file_path)
        elif self.provider == "zhipu":
            return self.generate_with_zhipu(prompt, file_path)

    def generate_with_gemini(self, prompt: str, file_path: Union[str, List[str], None] = None) -> str:
        """
        使用 Gemini API 生成内容。
        
        Args:
            prompt (str): 提示词文本。
            file_path (Union[str, List[str], None]): 单个文件路径或多个文件路径列表。支持PDF、图片、视频等格式。
            
        Returns:
            str: 模型生成的文本内容。
        """
        file_paths = self._normalize_file_paths(file_path)
        
        for attempt in range(self.max_retries):
            try:
                parts = []
                
                # 处理多个文件
                for fp in file_paths:
                    if not os.path.exists(fp):
                        return f"Error: File not found: {fp}"
                    
                    # 根据文件扩展名确定MIME类型
                    ext_to_mime = {
                        '.pdf': 'application/pdf',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.webp': 'image/webp',
                        '.heic': 'image/heic',
                        '.heif': 'image/heif',
                        '.mp4': 'video/mp4',
                        '.mpeg': 'video/mpeg',
                        '.mov': 'video/mov',
                        '.avi': 'video/avi',
                        '.flv': 'video/x-flv',
                        '.mpg': 'video/mpg',
                        '.webm': 'video/webm',
                        '.wmv': 'video/wmv',
                        '.3gpp': 'video/3gpp',
                    }
                    
                    file_ext = os.path.splitext(fp)[1].lower()
                    mime_type = ext_to_mime.get(file_ext)
                    
                    if not mime_type:
                        return f"Error: Unsupported file type: {file_ext}"
                    
                    try:
                        with open(fp, "rb") as f:
                            file_data = f.read()
                        parts.append(types.Part.from_bytes(
                            mime_type=mime_type,
                            data=base64.b64decode(base64.b64encode(file_data).decode())
                        ))
                    except PermissionError:
                        return f"Error: Permission denied: {fp}"
                    except Exception as e:
                        return f"Error reading file {fp}: {e}"

                # 添加提示词
                parts.append(types.Part.from_text(text=prompt))

                contents = [types.Content(role="user", parts=parts)]
                
                config = types.GenerateContentConfig(
                    temperature=self.temperature,
                    thinking_config=types.ThinkingConfig(thinking_budget=-1),
                )

                try:
                    response_text = ""
                    # 统一使用流式生成，体验更好，也可以改为非流式
                    for chunk in self.client.models.generate_content_stream(
                        model=self.model,
                        contents=contents,
                        config=config,
                    ):
                        response_text += chunk.text
                    return response_text
                except Exception as e:
                    return f"LLM Generation Error: {e}"
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                return f"LLM Generation Error after {self.max_retries} attempts: {e}"

    def generate_with_openai(self, prompt: str, file_path: Union[str, List[str], None] = None) -> str:
            """
            使用标准 OpenAI 聊天接口生成内容，支持 OpenRouter。
            图片文件将转换为 Base64 嵌入到消息中。
            """
            # 延迟导入，避免循环依赖
            from .pdf_to_markdown import convert_pdf_to_markdown

            file_paths = self._normalize_file_paths(file_path)
            
            # 1. 准备多模态内容
            content = [{"type": "text", "text": prompt}]
            
            for fp in file_paths:
                if not os.path.exists(fp):
                    return f"Error: File not found: {fp}"
                
                file_ext = os.path.splitext(fp)[1].lower()
                
                # 处理图片 (Base64 方式)
                if file_ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                    try:
                        with open(fp, "rb") as image_file:
                            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                        
                        # 确定 MIME 类型
                        mime_map = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png', '.webp': 'webp', '.gif': 'gif'}
                        mime_type = f"image/{mime_map.get(file_ext, 'jpeg')}"
                        
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        })
                    except Exception as e:
                        return f"Error encoding image {fp}: {e}"
                
                elif file_ext == '.pdf':
                    try:
                        markdown_text = convert_pdf_to_markdown(fp)
                        content[0]["text"] += f"\n\n--- [File: {os.path.basename(fp)} 内容开始] ---\n{markdown_text}\n--- [内容结束] ---"
                    except Exception as e:
                        return f"Error parsing PDF {fp}: {e}"
                else:
                    return f"Error: OpenAI 接口暂不支持直接上传 {file_ext} 类型文件。"

            # 2. 调用 API
            for attempt in range(self.max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": content}],
                        temperature=self.temperature,
                    )
                    return response.choices[0].message.content
                
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return f"OpenAI Generation Error after {self.max_retries} attempts: {e}"
                
    def generate_with_zhipu(self, prompt: str, file_path: Union[str, List[str], None] = None) -> str:
        """
        使用智谱AI API 生成内容,支持多模态输入。
        
        Args:
            prompt (str): 提示词文本
            file_path (Union[str, List[str], None]): 单个文件路径或多个文件路径列表 (仅支持jpg/png/webp/gif)
            
        Returns:
            str: 模型生成的文本内容
            
        Note:
            智谱AI限制:
            - ✅ 本地图片: 完美支持 (base64)，支持多图片
            - ✅ 在线PDF: 仅支持官方域名
            - ❌ 本地PDF: 不支持 , 使用 convert_pdf_to_markdown 预处理
            - ✅ 在线视频: 支持
        """
        # 延迟导入，避免循环依赖
        from .pdf_to_markdown import convert_pdf_to_markdown

        file_paths = self._normalize_file_paths(file_path)
        
        for attempt in range(self.max_retries):
            try:
                content_parts = []
                
                # 1. 处理多个本地文件
                for fp in file_paths:
                    if not os.path.exists(fp):
                        return f"Error: File not found: {fp}"
                    
                    file_ext = os.path.splitext(fp)[1].lower()
                    
                    # 仅支持图片
                    if file_ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                        with open(fp, "rb") as f:
                            file_data = base64.b64encode(f.read()).decode("utf-8")
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": file_data}
                        })
                    elif file_ext == '.pdf':
                        try:
                            markdown_text = convert_pdf_to_markdown(fp)
                            prompt += f"\n\n--- [File: {os.path.basename(fp)} 内容开始] ---\n{markdown_text}\n--- [内容结束] ---"
                        except Exception as e:
                            return f"Error parsing PDF {fp}: {e}"
                                   
                # 5. 添加文本提示词
                content_parts.append({
                    "type": "text",
                    "text": prompt
                })
                
                # 构建请求
                messages = [{"role": "user", "content": content_parts}]
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "stream": True,
                }
                
                if self.enable_thinking:
                    request_params["thinking"] = {"type": "enabled"}
                
                # 调用API
                response = self.client.chat.completions.create(**request_params)
                
                response_text = ""
                for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            response_text += delta.content
                
                if not response_text:
                    return "Warning: API返回空响应。请检查文件URL是否为官方域名(如cdn.bigmodel.cn)"
                
                return response_text
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return f"LLM Generation Error: {e}"


# 在测试代码部分添加
if __name__ == "__main__":
    llm = LLMClient(provider="openai", model="google/gemini-2.0-flash-exp:free")
    
    # 测试1: 单个本地图片
    # image_path = "e:/图片/Saved Pictures/R-C - 副本.jpg"
    # if os.path.exists(image_path):
    #     response = llm.generate(
    #         prompt="详细描述这张图片的内容，中文简短回复", 
    #         file_path=image_path
    #     )
    #     logger.info(f"\n单图片响应:\n{response}\n")
    
    # 测试2: 多个本地图片
    # image_paths = [
    #     "e:/图片/Saved Pictures/R-C - 副本.jpg",
    #     "e:/图片/Saved Pictures/R-C (1).jpg"
    # ]
    # # 检查文件是否存在
    # existing_paths = [p for p in image_paths if os.path.exists(p)]
    # if existing_paths:
    #     response = llm.generate(
    #         prompt="比较这些图片的异同，中文简短回复", 
    #         file_path=existing_paths
    #     )
    #     logger.info(f"\n多图片响应:\n{response}\n")

    # # 测试3: 纯文本
    # response = llm.generate(
    #     prompt="请简要介绍一下智谱AI的GLM-4.6v-flash模型有哪些特点？中文简短回复"
    # )
    # logger.info(f"\n纯文本响应:\n{response}\n")

    # 测试4: 多个本地文件（图片+PDF）
    mixed_files = ["e:/图片/Saved Pictures/R-C - 副本.jpg", "new_workflow/pdfs/巴菲特的阿尔法.pdf"]
    existing_mixed_files = [p for p in mixed_files if os.path.exists(p)]
    if existing_mixed_files:
        response = llm.generate(
            prompt="pdf文件是关于什么的，我提供的图片跟文件有关吗，中文简短回复",
            file_path=existing_mixed_files
        )
        logger.info(f"\n多文件响应:\n{response}\n")

    # 测试5: 本地PDF文件
    # pdf_file = "new_workflow/pdfs/我国股票市场知情交易的形成及策略分析.pdf"
    # if os.path.exists(pdf_file):
    #     response = llm.generate(
    #         prompt="请简要总结这个PDF文件的主要内容，中文简短回复",
    #         file_path=pdf_file
    #     )
    #     logger.info(f"\nPDF文件响应:\n{response}\n")
