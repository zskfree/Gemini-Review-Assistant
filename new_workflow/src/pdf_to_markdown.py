# pdf_to_markdown.py
"""
PDF转Markdown模块
支持普通PDF和扫描件PDF的转换
"""
import os
from typing import Optional, Tuple
from .llm_client import LLMClient
from .logger import logger


class PDFToMarkdownConverter:
    """
    PDF转Markdown转换器
    
    特性:
    - 优先使用 markitdown 处理普通PDF（文本型PDF）
    - 对于扫描件PDF，自动回退到LLM视觉提取
    - 支持自动检测PDF类型
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化转换器
        
        Args:
            llm_client: LLM客户端实例，用于处理扫描件PDF
                       如果为None，将使用默认配置创建
        """
        # 尝试导入 markitdown
        self.markitdown_available = False
        try:
            from markitdown import MarkItDown
            self.markitdown = MarkItDown()
            self.markitdown_available = True
        except ImportError:
            logger.warning("markitdown 未安装，将仅使用LLM处理。提示: pip install markitdown[pdf]")
            self.markitdown = None
        
        self.llm_client = llm_client or LLMClient(provider="gemini", model="gemini-flash-lite-latest")
        
        # 用于识别扫描件的提示词
        self.ocr_prompt = """请提取这个PDF文档中的所有文本内容，并以Markdown格式输出。

要求：
1. 保持原文的结构和层次（标题、段落、列表等）
2. 如果有表格，请用Markdown表格格式呈现
3. 保留重要的格式信息（粗体、斜体等）
4. 如果是学术论文，请特别注意：
   - 标题和作者信息
   - 摘要（Abstract）
   - 章节标题
   - 参考文献
5. 直接输出内容，不要添加额外说明

请开始提取："""
    
    def convert(self, pdf_path: str, force_llm: bool = False, force_refresh: bool = False) -> Tuple[str, str]:
        """
        将PDF转换为Markdown格式
        
        Args:
            pdf_path: PDF文件路径
            force_llm: 是否强制使用LLM处理（跳过markitdown）
            force_refresh: 是否强制刷新缓存（忽略已有缓存）
            
        Returns:
            Tuple[str, str]: (转换后的Markdown文本, 使用的方法)
                            方法可能是 "markitdown" 或 "llm_vision" 或 "cache"
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        if not pdf_path.lower().endswith('.pdf'):
            raise ValueError(f"文件不是PDF格式: {pdf_path}")
            
        # 1. 检查缓存
        from .config_loader import get_config
        cache_dir = get_config("paths.markdown_cache", "new_workflow/cache/markdowns")
        # 简单的缓存策略：md5(filepath) or basename.md. 这里简单使用 basename
        # 更好的做法是 hash 文件内容，但为了性能暂时只用文件名
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        cache_path = os.path.join(cache_dir, f"{base_name}.md")
        
        if not force_refresh and os.path.exists(cache_path):
            try:
                # 检查缓存是否比PDF新
                if os.path.getmtime(cache_path) > os.path.getmtime(pdf_path):
                    logger.info(f"[Cache] 命中缓存: {os.path.basename(cache_path)}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read(), "cache"
            except Exception as e:
                logger.warning(f"读取缓存失败: {e}, 将重新转换")
        
        # 2. 执行转换
        markdown_text = ""
        method = ""
        
        # 如果强制使用LLM或markitdown不可用，直接用LLM处理
        if force_llm or not self.markitdown_available:
            if force_llm:
                logger.info(f"[强制模式] 使用LLM处理: {os.path.basename(pdf_path)}")
            else:
                logger.info(f"[自动模式] markitdown不可用，使用LLM处理: {os.path.basename(pdf_path)}")
            markdown_text = self._convert_with_llm(pdf_path)
            method = "llm_vision"
            
        else:
            # 先尝试使用 markitdown
            try:
                logger.debug(f"[尝试1] 使用markitdown处理: {os.path.basename(pdf_path)}")
                result = self.markitdown.convert(pdf_path)
                text = result.text_content
                
                # 检查转换结果是否有效
                if self._is_valid_conversion(text):
                    logger.info(f"[成功] markitdown转换成功")
                    markdown_text = text
                    method = "markitdown"
                else:
                    logger.warning(f"[警告] markitdown转换结果无效，可能是扫描件")
                    # 无效则回退
                    logger.info(f"[尝试2] 使用LLM视觉能力处理")
                    markdown_text = self._convert_with_llm(pdf_path)
                    method = "llm_vision"
                    
            except Exception as e:
                error_str = str(e)
                if "MissingDependencyException" in error_str or "dependencies needed" in error_str:
                    logger.warning(f"markitdown缺少PDF依赖，请运行: pip install markitdown[pdf]")
                    self.markitdown_available = False
                else:
                    logger.warning(f"markitdown处理失败: {e}")
                
                # 失败则回退
                logger.info(f"[尝试2] 使用LLM视觉能力处理")
                markdown_text = self._convert_with_llm(pdf_path)
                method = "llm_vision"

        # 3. 写入缓存
        if markdown_text:
            try:
                os.makedirs(cache_dir, exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_text)
                logger.debug(f"[Cache] 已写入缓存: {cache_path}")
            except Exception as e:
                logger.warning(f"写入缓存失败: {e}")
                
        return markdown_text, method

    def _is_valid_conversion(self, text: str, min_length: int = 100) -> bool:
        """
        检查转换结果是否有效
        
        Args:
            text: 转换后的文本
            min_length: 最小有效长度
            
        Returns:
            bool: 是否有效
        """
        if not text or len(text.strip()) < min_length:
            return False
        
        # 检查是否包含实际内容（不只是空白和特殊字符）
        alphanumeric_count = sum(c.isalnum() for c in text)
        if alphanumeric_count < min_length * 0.3:  # 至少30%的字符应该是字母数字
            return False
        
        return True
    
    def _convert_with_llm(self, pdf_path: str) -> str:
        """
        使用LLM视觉能力提取PDF内容（适用于扫描件）
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            str: 提取的Markdown文本
        """
        try:
            markdown_text = self.llm_client.generate(
                prompt=self.ocr_prompt,
                file_path=pdf_path
            )
            
            # 检查是否有错误信息
            if markdown_text.startswith("Error:") or markdown_text.startswith("LLM Generation Error"):
                raise Exception(markdown_text)
            
            return markdown_text
            
        except Exception as e:
            error_msg = f"LLM处理失败: {e}"
            logger.error(f"{error_msg}")
            raise Exception(error_msg)
    
    def convert_batch(self, pdf_paths: list, force_llm: bool = False) -> dict:
        """
        批量转换多个PDF文件 (并发版)
        
        Args:
            pdf_paths: PDF文件路径列表
            force_llm: 是否强制使用LLM处理
            
        Returns:
            dict: {文件路径: (Markdown文本, 使用的方法, 是否成功)}
        """
        results = {}
        
        # 1. 引入必要的并发工具
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from .config_loader import get_config
        import time
        
        # 2. 获取并发数配置
        max_workers = get_config("concurrency.max_workers", 3)
        logger.info(f"同时处理PDF，最大线程数: {max_workers}")
        
        # 3. 定义单个任务函数 (Wrapper)
        def _process_one(path, idx, total):
            start_time = time.time()
            logger.info(f"开始处理第 {idx}/{total} 个文件: {os.path.basename(path)}")
            try:
                # 传入 force_refresh=False (默认)
                md_text, method = self.convert(path, force_llm=force_llm)
                elapsed = time.time() - start_time
                logger.info(f"[✓] {os.path.basename(path)} 转换成功 (耗时: {elapsed:.2f}s)")
                return path, md_text, method, True
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"[✗] {os.path.basename(path)} 转换失败: {e} (耗时: {elapsed:.2f}s)")
                return path, str(e), None, False

        # 4. 执行并发任务
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(_process_one, pdf_path, i, len(pdf_paths)): pdf_path 
                for i, pdf_path in enumerate(pdf_paths, 1)
            }
            
            for future in as_completed(future_to_path):
                path, content, method, success = future.result()
                results[path] = (content, method, success)
        
        return results
    
    def save_markdown(self, markdown_text: str, output_path: str):
        """
        保存Markdown文本到文件
        
        Args:
            markdown_text: Markdown文本
            output_path: 输出文件路径
        """
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:  # 如果有目录部分
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        logger.info(f"[保存] Markdown已保存到: {output_path}")


# 便捷函数
def convert_pdf_to_markdown(pdf_path: str, 
                           output_path: Optional[str] = None,
                           force_llm: bool = False,
                           llm_client: Optional[LLMClient] = None) -> str:
    """
    便捷函数：将单个PDF转换为Markdown
    
    Args:
        pdf_path: PDF文件路径
        output_path: 输出文件路径（可选）
        force_llm: 是否强制使用LLM
        llm_client: 自定义LLM客户端（可选）
        
    Returns:
        str: Markdown文本
    """
    converter = PDFToMarkdownConverter(llm_client=llm_client)
    markdown_text, method = converter.convert(pdf_path, force_llm=force_llm)
    
    if output_path:
        converter.save_markdown(markdown_text, output_path)
    
    return markdown_text


def convert_pdfs_in_folder(pdf_folder: str,
                           output_folder: str,
                           force_llm: bool = False,
                           llm_client: Optional[LLMClient] = None) -> dict:
    """
    便捷函数：转换文件夹中的所有PDF
    
    Args:
        pdf_folder: PDF文件夹路径
        output_folder: 输出文件夹路径
        force_llm: 是否强制使用LLM
        llm_client: 自定义LLM客户端（可选）
        
    Returns:
        dict: 转换结果统计
    """
    from pdf_processor import get_pdf_files
    
    pdf_files = get_pdf_files(pdf_folder)
    
    if not pdf_files:
        logger.warning(f"未找到PDF文件: {pdf_folder}")
        return {}
    
    logger.info(f"找到 {len(pdf_files)} 个PDF文件")
    
    converter = PDFToMarkdownConverter(llm_client=llm_client)
    results = converter.convert_batch(pdf_files, force_llm=force_llm)
    
    # 保存结果
    os.makedirs(output_folder, exist_ok=True)
    success_count = 0
    
    for pdf_path, (content, method, success) in results.items():
        if success:
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_path = os.path.join(output_folder, f"{base_name}.md")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            success_count += 1
    
    # 打印统计
    logger.info(f"转换完成. 成功: {success_count}/{len(pdf_files)}, 失败: {len(pdf_files) - success_count}, 输出: {output_folder}")
    
    return results


# 测试代码
if __name__ == "__main__":
    # 测试1: 转换单个PDF
    print("\n【测试1】转换单个PDF文件")
    print("-" * 60)
    
    test_pdf = "new_workflow/pdfs/我国股票市场知情交易的形成及策略分析.pdf"
    
    if os.path.exists(test_pdf):
        try:
            # 创建转换器
            # llm = LLMClient(provider="gemini", model="gemini-flash-lite-latest")
            converter = PDFToMarkdownConverter() # Use default
            
            # 转换
            markdown_text, method = converter.convert(test_pdf)
            
            print(f"\n转换方法: {method}")
            print(f"文本长度: {len(markdown_text)} 字符")
            print(f"\n前500字符预览:")
            print("-" * 60)
            print(markdown_text[:500])
            
        except Exception as e:
            print(f"转换失败: {e}")
    else:
        print(f"测试文件不存在: {test_pdf}")
    
    # 测试2: 批量转换（如果需要）
    # print("\n【测试2】批量转换PDF文件夹")
    # print("-" * 60)
    # results = convert_pdfs_in_folder(
    #     pdf_folder="new_workflow/pdfs",
    #     output_folder="new_workflow/txts/markdown_outputs",
    #     force_llm=False  # 设为True可强制使用LLM处理所有文件
    # )