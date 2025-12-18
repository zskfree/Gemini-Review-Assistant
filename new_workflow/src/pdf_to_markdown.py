# pdf_to_markdown.py
"""
PDF转Markdown模块
支持普通PDF和扫描件PDF的转换
"""
import os
from typing import Optional, Tuple
from .llm_client import LLMClient


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
            print("[警告] markitdown 未安装，将仅使用LLM处理")
            print("提示: pip install markitdown[pdf]")
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
    
    def convert(self, pdf_path: str, force_llm: bool = False) -> Tuple[str, str]:
        """
        将PDF转换为Markdown格式
        
        Args:
            pdf_path: PDF文件路径
            force_llm: 是否强制使用LLM处理（跳过markitdown）
            
        Returns:
            Tuple[str, str]: (转换后的Markdown文本, 使用的方法)
                            方法可能是 "markitdown" 或 "llm_vision"
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        if not pdf_path.lower().endswith('.pdf'):
            raise ValueError(f"文件不是PDF格式: {pdf_path}")
        
        # 如果强制使用LLM或markitdown不可用，直接用LLM处理
        if force_llm or not self.markitdown_available:
            if force_llm:
                print(f"[强制模式] 使用LLM处理: {os.path.basename(pdf_path)}")
            else:
                print(f"[自动模式] markitdown不可用，使用LLM处理: {os.path.basename(pdf_path)}")
            return self._convert_with_llm(pdf_path), "llm_vision"
        
        # 先尝试使用 markitdown
        try:
            print(f"[尝试1] 使用markitdown处理: {os.path.basename(pdf_path)}")
            result = self.markitdown.convert(pdf_path)
            markdown_text = result.text_content
            
            # 检查转换结果是否有效（不是空或几乎为空）
            if self._is_valid_conversion(markdown_text):
                print(f"[成功] markitdown转换成功")
                return markdown_text, "markitdown"
            else:
                print(f"[警告] markitdown转换结果无效，可能是扫描件")
                
        except Exception as e:
            error_str = str(e)
            # 检查是否是依赖缺失错误
            if "MissingDependencyException" in error_str or "dependencies needed" in error_str:
                print(f"[警告] markitdown缺少PDF依赖，请运行: pip install markitdown[pdf]")
                self.markitdown_available = False  # 标记为不可用
            else:
                print(f"[警告] markitdown处理失败: {e}")
        
        # 回退到LLM处理（适用于扫描件）
        print(f"[尝试2] 使用LLM视觉能力处理")
        return self._convert_with_llm(pdf_path), "llm_vision"
    
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
            print(f"[错误] {error_msg}")
            raise Exception(error_msg)
    
    def convert_batch(self, pdf_paths: list, force_llm: bool = False) -> dict:
        """
        批量转换多个PDF文件
        
        Args:
            pdf_paths: PDF文件路径列表
            force_llm: 是否强制使用LLM处理
            
        Returns:
            dict: {文件路径: (Markdown文本, 使用的方法, 是否成功)}
        """
        results = {}
        
        for i, pdf_path in enumerate(pdf_paths, 1):
            print(f"\n{'='*60}")
            print(f"处理第 {i}/{len(pdf_paths)} 个文件")
            print(f"{'='*60}")
            
            try:
                markdown_text, method = self.convert(pdf_path, force_llm=force_llm)
                results[pdf_path] = (markdown_text, method, True)
                print(f"[✓] 转换成功")
                
            except Exception as e:
                results[pdf_path] = (str(e), None, False)
                print(f"[✗] 转换失败: {e}")
        
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
        
        print(f"[保存] Markdown已保存到: {output_path}")


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
        print(f"未找到PDF文件: {pdf_folder}")
        return {}
    
    print(f"找到 {len(pdf_files)} 个PDF文件")
    
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
    print(f"\n{'='*60}")
    print(f"转换完成")
    print(f"{'='*60}")
    print(f"总计: {len(pdf_files)} 个文件")
    print(f"成功: {success_count} 个")
    print(f"失败: {len(pdf_files) - success_count} 个")
    print(f"输出目录: {output_folder}")
    
    return results


# 测试代码
if __name__ == "__main__":
    # 测试1: 转换单个PDF
    print("\n【测试1】转换单个PDF文件")
    print("-" * 60)
    
    test_pdf = "new_workflow/pdfs/我国股票市场知情交易的形成及策略分析.pdf"
    
    if os.path.exists(test_pdf):
        try:
            # 创建转换器（使用Gemini，因为它对PDF支持最好）
            llm = LLMClient(provider="gemini", model="gemini-flash-lite-latest")
            converter = PDFToMarkdownConverter(llm_client=llm)
            
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