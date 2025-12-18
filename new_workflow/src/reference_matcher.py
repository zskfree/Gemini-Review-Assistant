# new_workflow/src/reference_matcher.py
"""参考文献匹配模块"""
import json
import os
from typing import Dict, List
from .llm_client import LLMClient
from .config_loader import get_config

def align_pdfs_with_references(pdf_files: List[str], references_text: str) -> Dict[str, str]:
    """
    使用LLM将PDF文件名与参考文献列表进行对齐
    
    Args:
        pdf_files: PDF文件路径列表
        references_text: 参考文献列表文本
        
    Returns:
        文件名到参考文献的映射字典
    """
    llm = LLMClient(provider=get_config("model.reference_extraction.provider"), 
                    model=get_config("model.reference_extraction.model_name"),
                    temperature=get_config("model.reference_extraction.temperature"))
    
    # 提取文件名用于Prompt，减少Token消耗
    file_names = [os.path.basename(f) for f in pdf_files]
    
    prompt = f"""
    任务：将以下 PDF 文件名与提供的参考文献列表进行一一对应匹配。
    
    PDF 文件名列表：
    {json.dumps(file_names, ensure_ascii=False)}
    
    参考文献列表：
    {references_text}
    
    要求：
    1. 分析文件名和参考文献的标题、作者等信息，找到最匹配的对应关系。
    2. 返回一个 JSON 对象，键是 PDF 文件名，值是对应的完整参考文献字符串。
    3. 如果某个文件没有找到对应的参考文献，对应的值设为 null。
    4. 仅返回 JSON 格式结果，不要包含 Markdown 代码块标记或其他文字。
    5. 确保每个参考文献只被分配给一个文件，避免一对多映射关系。
    6. 如果无法确定匹配关系，请将该文件的值设为 null。
    7. 值不要包含参考文献的编号。
    8. 示例输出格式：
    {{
        "知情交易、信息不确定性与股票风险溢价.pdf": "陈国进, 张润泽, 谢沛霖, 等. 知情交易、信息不确定性与股票风险溢价[J]. 管理科学学报, 2019, 22(4): 53-74.",
        "paper2.pdf": null,
        ...
    }}
    """    
    print("正在调用大模型进行文献对齐...")
    try:
        response = llm.generate(prompt=prompt)
        # 清理可能存在的Markdown标记
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        mapping = json.loads(cleaned_response)
        return mapping
    except Exception as e:
        print(f"对齐参考文献时发生错误: {e}")
        return {}

def validate_reference_mapping(mapping: Dict[str, str], references_text: str) -> Dict[str, str]:
    """
    验证参考文献映射的有效性，确保一对一映射关系
    
    Args:
        mapping: 文件名到参考文献的映射字典
        references_text: 参考文献列表文本
        
    Returns:
        验证后的映射字典，确保一对一映射关系
    """
    valid_mapping = {}
    
    # 记录已被映射的参考文献，防止一对多映射
    used_references = set()
    
    for file_name, reference in mapping.items():
        # 检查参考文献是否有效且未被其他文件使用
        if reference and reference in references_text and reference not in used_references:
            valid_mapping[file_name] = reference
            used_references.add(reference)
        else:
            valid_mapping[file_name] = None
            
    # 检查是否有重复映射到相同参考文献的情况
    reference_count = {}
    for ref in valid_mapping.values():
        if ref:
            reference_count[ref] = reference_count.get(ref, 0) + 1
    
    # 将重复映射的项设为None（保留第一个）
    reference_first_file = {}
    for file_name, reference in valid_mapping.items():
        if reference and reference_count[reference] > 1:
            if reference not in reference_first_file:
                reference_first_file[reference] = file_name
            elif reference_first_file[reference] != file_name:
                valid_mapping[file_name] = None
                
    return valid_mapping

def load_or_create_mapping(reference_mapping_path: str, pdf_files: List[str], 
                          reference_file_path: str) -> Dict[str, str]:
    """
    加载或创建参考文献映射
    
    Args:
        reference_mapping_path: 映射文件保存路径
        pdf_files: PDF文件列表
        reference_file_path: 参考文献文件路径
        
    Returns:
        文件名到参考文献的映射字典
    """
    # 如果映射文件存在，直接加载
    if os.path.exists(reference_mapping_path):
        with open(reference_mapping_path, "r", encoding="utf-8") as f:
            if os.path.getsize(reference_mapping_path) == 0:
                print("参考文献映射文件为空，重新创建映射")
                return {}
            return json.load(f)
    
    # 否则创建新的映射
    if not os.path.exists(reference_file_path):
        print(f"未找到参考文献文件: {reference_file_path}")
        return {}
    
    try:
        with open(reference_file_path, "r", encoding="utf-8") as f:
            references_text = f.read()
        
        if not references_text.strip():
            print("参考文献文件为空")
            return {}
        
        # 进行对齐并验证
        reference_mapping = align_pdfs_with_references(pdf_files, references_text)
        reference_mapping = validate_reference_mapping(reference_mapping, references_text)
        
        # 保存映射
        with open(reference_mapping_path, "w", encoding="utf-8") as f:
            json.dump(reference_mapping, f, ensure_ascii=False, indent=4)
        
        matched_count = sum(1 for ref in reference_mapping.values() if ref is not None)
        total_count = len(reference_mapping)
        print(f"匹配结果: {matched_count} / {total_count} 个文件找到了对应的参考文献。")
        
        return reference_mapping
    except Exception as e:
        print(f"创建参考文献映射失败: {e}")
        return {}
    