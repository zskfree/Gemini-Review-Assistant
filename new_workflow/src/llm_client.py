# llm_client.py
import asyncio
import base64
import os
from google import genai
from google.genai import types
import time
from pathlib import Path
from typing import Optional, Union, List
from .config_loader import get_config

# 禁用 gemini_webapi 详细日志
try:
    from gemini_webapi import set_log_level
    set_log_level("ERROR")
except ImportError:
    pass

from dataclasses import dataclass

PROXY_URL = get_config("proxy.url", "")
if PROXY_URL:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL

from dataclasses import dataclass
@dataclass
class ChatResponse:
    """统一的返回结果对象"""
    text: str
    saved_images: List[str]
    raw_response: object


class LLMClient:
    """
    统一的大模型交互客户端，支持 Google GenAI、OpenAI、智谱AI 和 Gemini Web API。
    设计用于方便扩展其他模型接口。
    
    支持的提供商:
        - gemini: Google GenAI 官方 API
        - gemini_web: Gemini Web API (基于浏览器 Cookie，支持图片生成)
        - openai: OpenAI 兼容接口 (支持 OpenRouter)
        - zhipu: 智谱AI
    """
    
    # 支持的图片扩展名
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic', '.heif'}
    
    def __init__(self, provider=None, api_key=None, model=None, temperature=None):
        """
        初始化 LLM 客户端
        
        Args:
            provider (str): 提供商类型，支持 "gemini"、"gemini_web"、"openai" 或 "zhipu"
            api_key (str, optional): API 密钥 (gemini_web 不需要)
            model (str, optional): 模型名称
            temperature (float, optional): 温度参数
        """
        if provider is None:
            provider = "zhipu"
        self.provider = provider.lower()
        
        self.temperature = temperature if temperature is not None else get_config("api.default_temperature", 0.2)
        self.max_retries = get_config("api.max_retries", 3)
        
        # 根据提供商初始化
        self._init_provider(api_key, model)

    def _init_provider(self, api_key: str, model: str):
        """根据提供商类型初始化客户端"""
        
        if self.provider == "gemini":
            self._init_gemini(api_key, model)
            
        elif self.provider == "gemini_web":
            self._init_gemini_web(model)
            
        elif self.provider == "openai":
            self._init_openai(api_key, model)
            
        elif self.provider == "zhipu":
            self._init_zhipu(api_key, model)
            
        else:
            raise ValueError(f"不支持的提供商: {self.provider}")

    def _init_gemini(self, api_key: str, model: str):
        """初始化 Gemini 官方 API"""
        self.api_key = api_key or get_config("api.genai_key")
        self.base_url = get_config("api.genai_base_url", None)
        self.model = model or get_config("api.genai_model", "gemini-flash-lite-latest")
        
        if not self.api_key:
            raise ValueError("未找到 Gemini API 密钥，请检查配置文件")
        if self.base_url:
            self.client = genai.Client(api_key=self.api_key, http_options={"base_url": self.base_url})
        else:
            self.client = genai.Client(api_key=self.api_key)

    def _init_gemini_web(self, model: str):
        """初始化 Gemini Web API (延迟初始化，异步使用时才创建)"""
        from gemini_webapi.constants import Model
        self.model = model or Model.UNSPECIFIED
        self.proxy = get_config("proxy.url", None)
        # Web API 客户端需要异步初始化，这里只做标记
        self.client = None
        self._gemini_web_initialized = False

    def _init_openai(self, api_key: str, model: str):
        """初始化 OpenAI 兼容接口"""
        self.api_key = api_key or get_config("api.openai_key")
        self.base_url = get_config("api.openai_base_url", "https://openrouter.ai/api/v1/")
        self.model = model or get_config("api.openai_model", "gemini-flash-lite-latest")
        
        if not self.api_key or self.api_key == "your-openai-key":
            raise ValueError("未找到 OpenAI API 密钥，请检查配置文件")
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            raise ImportError("请安装 openai 库: pip install openai")

    def _init_zhipu(self, api_key: str, model: str):
        """初始化智谱AI"""
        self.api_key = api_key or get_config("api.zhipu_key")
        self.model = model or get_config("api.zhipu_model", "glm-4.5-flash")
        self.enable_thinking = get_config("api.zhipu_enable_thinking", True)
        
        if not self.api_key or self.api_key == "your-zhipu-key":
            raise ValueError("未找到智谱AI API 密钥，请检查配置文件")
        try:
            from zai import ZhipuAiClient
            self.client = ZhipuAiClient(api_key=self.api_key)
        except ImportError:
            raise ImportError("请安装 zai 库: pip install zai")

    def _normalize_file_paths(self, file_path: Union[str, List[str], None]) -> List[str]:
        """统一处理文件路径参数，转换为列表形式"""
        if file_path is None:
            return []
        if isinstance(file_path, str):
            return [file_path]
        return file_path

    # ==================== 统一接口 ====================
    
    def generate(self, prompt: str, file_path: Union[str, List[str], None] = None) -> str:
        """
        统一生成接口（同步），自动根据 provider 调用对应方法
        
        注意: gemini_web 提供商需要使用 generate_async() 方法
        """
        if self.provider == "gemini":
            return self.generate_with_gemini(prompt, file_path)
        elif self.provider == "gemini_web":
            # 对于 gemini_web，在同步环境中运行异步代码
            return asyncio.run(self.generate_async(prompt, file_path))
        elif self.provider == "openai":
            return self.generate_with_openai(prompt, file_path)
        elif self.provider == "zhipu":
            return self.generate_with_zhipu(prompt, file_path)

    async def generate_async(
        self, 
        prompt: str, 
        file_path: Union[str, List[str], None] = None,
        save_img_path: str = None,
        new_chat: bool = False
    ) -> Union[str, "ChatResponse"]:
        """
        统一生成接口（异步），支持所有提供商
        
        Args:
            prompt: 提示词
            file_path: 文件路径（单个或列表）
            save_img_path: 图片保存路径（仅 gemini_web 支持）
            new_chat: 是否开启新会话（仅 gemini_web 支持）
            
        Returns:
            str: 当 save_img_path 为 None 时返回纯文本
            ChatResponse: 当 save_img_path 不为 None 时返回完整响应对象 (gemini_web)
        """
        if self.provider == "gemini_web":
            response = await self.generate_with_gemini_web(prompt, file_path, save_img_path, new_chat)
            # 如果未指定图片保存路径，只返回文本内容（保持向后兼容）
            if save_img_path is None:
                return response.text
            return response
        else:
            # 其他提供商使用同步方法包装
            return self.generate(prompt, file_path)

    # ==================== Gemini Web API ====================
    
    async def generate_with_gemini_web(
        self, 
        prompt: str, 
        file_path: Union[str, List[str], None] = None,
        save_img_path: str = None,
        new_chat: bool = False
    ) -> "ChatResponse":
        """
        使用 Gemini Web API 生成内容（基于浏览器 Cookie）
        
        特点:
            - 支持图片生成并自动下载
            - 支持多轮对话
            - 支持文件上传分析
        
        Args:
            prompt: 提示词
            file_path: 文件路径
            save_img_path: 图片保存目录（如需生成图片）
            new_chat: 是否开启新会话
            
        Returns:
            ChatResponse: 包含 text、saved_images、raw_response
        """
        from gemini_webapi import GeminiClient
        from gemini_web.get_cookie import get_gemini_tokens
        from .config_loader import get_config
        from .logger import logger
        
        file_paths = self._normalize_file_paths(file_path)
        
        # 检查文件存在性
        for fp in file_paths:
            if not os.path.exists(fp):
                return ChatResponse(text=f"Error: File not found: {fp}", saved_images=[], raw_response=None)

        # 延迟初始化客户端
        if not self._gemini_web_initialized:
            cookie_file = get_config("api.gemini_cookie_file", None)
            
            # 重试逻辑
            for attempt in range(self.max_retries):
                try:
                    token_id, token_ts = get_gemini_tokens(cookie_file)
                    self.client = GeminiClient(token_id, token_ts, proxy=self.proxy)
                    
                    # 增加超时时间并添加重试
                    await self.client.init(timeout=60, auto_refresh=True)
                    self.chat_session = self.client.start_chat(model=self.model)
                    self._gemini_web_initialized = True
                    logger.info("✅ Gemini Web API 已就绪")
                    break
                except Exception as e:
                    logger.warning(f"Gemini Web 初始化失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 * (attempt + 1))
                    else:
                        raise RuntimeError(f"Gemini Web 初始化失败，已重试 {self.max_retries} 次: {e}")

        # 开启新会话
        if new_chat:
            self.chat_session = self.client.start_chat(model=self.model)
            logger.info("🔄 --- 开启新会话 ---")

        # 发送消息
        response = await self.chat_session.send_message(prompt, files=file_paths or [])
        
        saved_paths = []
        if save_img_path:
            saved_paths = await self._process_and_save_images_web(response, save_img_path, logger)

        return ChatResponse(
            text=response.text,
            saved_images=saved_paths,
            raw_response=response
        )

    async def _process_and_save_images_web(self, response, save_dir: str, logger) -> List[str]:
        """处理 Gemini Web API 返回的图片并保存"""
        # 搜集所有图片对象
        images = list(response.images)
        if not images and response.candidates:
            for candidate in response.candidates:
                if candidate.images:
                    for img in candidate.images:
                        if img.url not in [i.url for i in images]:
                            images.append(img)
        
        if not images and "image_generation_content" in response.text:
            logger.warning("⚠️ 警告: 检测到图片占位符但未解析到对象 (Google API 波动)")

        if not images:
            return []

        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"⬇️ 正在下载 {len(images)} 张图片...")
        tasks = []
        paths = []
        
        for i, img in enumerate(images):
            clean_title = "".join(c for c in (img.title or "gen") if c.isalnum())[:15]
            filename = f"{clean_title}_{i}_{int(time.time())}.png"
            full_path = os.path.join(save_dir, filename)
            paths.append(full_path)
            tasks.append(img.save(path=save_dir, filename=filename))

        await asyncio.gather(*tasks, return_exceptions=True)
        return paths

    async def close_gemini_web(self):
        """关闭 Gemini Web API 连接"""
        if self.provider == "gemini_web" and self._gemini_web_initialized:
            await self.client.close()
            self._gemini_web_initialized = False
            from .logger import logger
            logger.info("💤 Gemini Web API 已关闭")

    # ==================== Context Manager 支持 ====================
    
    async def __aenter__(self):
        """支持 async with 语法"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """自动关闭连接"""
        await self.close_gemini_web()

    # ==================== 其他提供商方法 (保持不变) ====================

    def generate_with_gemini(self, prompt: str, file_path: Union[str, List[str], None] = None) -> str:
        """使用 Gemini API 生成内容。"""
        file_paths = self._normalize_file_paths(file_path)
        
        for attempt in range(self.max_retries):
            try:
                parts = []
                
                for fp in file_paths:
                    if not os.path.exists(fp):
                        return f"Error: File not found: {fp}"
                    
                    ext_to_mime = {
                        '.pdf': 'application/pdf',
                        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                        '.png': 'image/png', '.webp': 'image/webp',
                        '.heic': 'image/heic', '.heif': 'image/heif',
                        '.mp4': 'video/mp4', '.mpeg': 'video/mpeg',
                        '.mov': 'video/mov', '.avi': 'video/avi',
                        '.flv': 'video/x-flv', '.mpg': 'video/mpg',
                        '.webm': 'video/webm', '.wmv': 'video/wmv',
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

                parts.append(types.Part.from_text(text=prompt))
                contents = [types.Content(role="user", parts=parts)]
                
                config = types.GenerateContentConfig(
                    temperature=self.temperature,
                    thinking_config=types.ThinkingConfig(thinking_budget=-1),
                )

                try:
                    response_text = ""
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
                    time.sleep(2 ** attempt)
                    continue
                return f"LLM Generation Error after {self.max_retries} attempts: {e}"

    def generate_with_openai(self, prompt: str, file_path: Union[str, List[str], None] = None) -> str:
        """使用标准 OpenAI 聊天接口生成内容，支持 OpenRouter。"""
        from .pdf_to_markdown import convert_pdf_to_markdown

        file_paths = self._normalize_file_paths(file_path)
        content = [{"type": "text", "text": prompt}]
        
        for fp in file_paths:
            if not os.path.exists(fp):
                return f"Error: File not found: {fp}"
            
            file_ext = os.path.splitext(fp)[1].lower()
            
            if file_ext in self.IMAGE_EXTENSIONS:
                try:
                    with open(fp, "rb") as image_file:
                        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    mime_map = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png', '.webp': 'webp', '.gif': 'gif'}
                    mime_type = f"image/{mime_map.get(file_ext, 'jpeg')}"
                    
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
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
        """使用智谱AI API 生成内容，支持多模态输入。"""
        from .pdf_to_markdown import convert_pdf_to_markdown

        file_paths = self._normalize_file_paths(file_path)
        
        for attempt in range(self.max_retries):
            try:
                content_parts = []
                
                for fp in file_paths:
                    if not os.path.exists(fp):
                        return f"Error: File not found: {fp}"
                    
                    file_ext = os.path.splitext(fp)[1].lower()
                    
                    if file_ext in self.IMAGE_EXTENSIONS:
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
                                   
                content_parts.append({"type": "text", "text": prompt})
                
                messages = [{"role": "user", "content": content_parts}]
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "stream": True,
                }
                
                if self.enable_thinking:
                    request_params["thinking"] = {"type": "enabled"}
                
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


# ==================== 测试代码 ====================
if __name__ == "__main__":
    import asyncio
    
    async def test_gemini_web():
        """测试 Gemini Web API"""
        print("\n--- 测试 Gemini Web API ---")
        
        async with LLMClient(provider="gemini_web") as llm:
            # 测试1: 纯文本对话
            response = await llm.generate_async("你好，请用一句话介绍自己")
            print(f"回复: {response.text[:100]}...")
            
            # 测试2: 图片生成
            response = await llm.generate_async(
                "生成一只可爱的猫咪图片",
                save_img_path="downloads/test_cat"
            )
            if response.saved_images:
                print(f"✅ 图片已保存: {response.saved_images}")
            
            # 测试3: 文件分析
            pdf_path = "path/to/your/file.pdf"
            if os.path.exists(pdf_path):
                response = await llm.generate_async(
                    "总结这个文件的主要内容",
                    file_path=pdf_path,
                    new_chat=True
                )
                print(f"总结: {response.text[:200]}...")

    # 运行测试
    # asyncio.run(test_gemini_web())
    
    # 同步方式使用 (会自动运行 asyncio.run)
    # llm = LLMClient(provider="gemini_web")
    # result = llm.generate("你好")
    # print(result)