import asyncio
import asyncio
import os
from pathlib import Path
from typing import List, Union, Optional
from dataclasses import dataclass

from gemini_webapi import GeminiClient, set_log_level
from gemini_webapi.constants import Model

from .get_cookie import get_gemini_tokens

try:
    from src.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# 配置日志
set_log_level("INFO")

@dataclass
class ChatResponse:
    """统一的返回结果对象"""
    text: str
    saved_images: List[str]  # 保存到本地的图片路径列表
    raw_response: object     # 原始响应对象，供高阶使用

class GeminiAgent:
    def __init__(self, 
                 token_id: str = None, 
                 token_ts: str = None, 
                 proxy: str = None, 
                 model: str = Model.UNSPECIFIED):
        """
        :param token_id: __Secure-1PSID
        :param token_ts: __Secure-1PSIDTS
        :param proxy: 代理地址
        :param model: 模型版本
        """
        self.client = GeminiClient(token_id, token_ts, proxy=proxy)
        self.model = model
        self.chat_session = None
        self.timeout = 300

    async def __aenter__(self):
        """支持 async with 语法，自动初始化"""
        await self.client.init(timeout=self.timeout, auto_refresh=True)
        # 默认启动一个对话会话
        self.chat_session = self.client.start_chat(model=self.model)
        logger.info("✅ GeminiAgent 已就绪")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """自动关闭连接"""
        await self.client.close()
        logger.info("💤 GeminiAgent 已关闭")

    async def ask(self, 
                  prompt: str, 
                  files: List[Union[str, Path]] = None, 
                  save_img_path: str = None,
                  new_chat: bool = False) -> ChatResponse:
        """
        统一交互接口：处理文本、文件分析、图片生成
        """
        if new_chat or self.chat_session is None:
            self.chat_session = self.client.start_chat(model=self.model)
            logger.info("🔄 --- 开启新会话 ---")

        logger.info(f"📤 发送: {prompt[:30]}..." + (f" [附带 {len(files)} 个文件]" if files else ""))

        # 发送消息
        response = await self.chat_session.send_message(prompt, files=files or [])
        
        saved_paths = []
        # 如果指定了保存路径，尝试提取并下载图片
        if save_img_path:
            saved_paths = await self._process_and_save_images(response, save_img_path)

        return ChatResponse(
            text=response.text,
            saved_images=saved_paths,
            raw_response=response
        )

    async def _process_and_save_images(self, response, save_dir: str) -> List[str]:
        """内部逻辑：深度提取图片并并发下载"""
        # 1. 搜集所有图片对象
        images = list(response.images)
        if not images and response.candidates:
            for candidate in response.candidates:
                if candidate.images:
                    for img in candidate.images:
                        if img.url not in [i.url for i in images]:
                            images.append(img)
        
        # 检查是否应该有图但没抓到
        if not images and "image_generation_content" in response.text:
             logger.warning("⚠️ 警告: 检测到图片占位符但未解析到对象 (Google API 波动)")

        if not images:
            return []

        # 2. 准备目录
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        # 3. 并发下载
        logger.info(f"⬇️ 正在下载 {len(images)} 张图片...")
        tasks = []
        paths = []
        
        for i, img in enumerate(images):
            clean_title = "".join(c for c in (img.title or "gen") if c.isalnum())[:15]
            filename = f"{clean_title}_{i}_{int(asyncio.get_event_loop().time())}.png"
            full_path = os.path.join(save_dir, filename)
            paths.append(full_path)
            tasks.append(img.save(path=save_dir, filename=filename))

        await asyncio.gather(*tasks, return_exceptions=True)
        return paths
    