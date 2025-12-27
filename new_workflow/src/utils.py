# new_workflow/src/utils.py
import re
import json
from typing import Any, Optional, Dict, List, Union

def extract_json_from_text(text: str) -> Optional[Union[Dict, List]]:
    """
    从文本中健壮地提取 JSON 对象或数组。
    支持处理 Markdown 代码块 (```json ... ```) 和非标准的前后缀。
    
    Args:
        text: 包含 JSON 的字符串
        
    Returns:
        解析后的 Python 对象 (Dict 或 List)，如果失败返回 None
    """
    if not text:
        return None
        
    # 1. 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # 2. 清理 Markdown 代码块常用的标记
    cleaned_text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        pass

    # 3. 使用正则寻找最外层的 {} 或 []
    # 寻找可能是 JSON 对象的模式
    # dotall=True (re.S) 让 . 匹配换行符
    
    # 尝试匹配 { ... }
    match_dict = re.search(r'(\{.*\})', text, re.S)
    if match_dict:
        try:
            return json.loads(match_dict.group(1))
        except json.JSONDecodeError:
            pass
            
    # 尝试匹配 [ ... ]
    match_list = re.search(r'(\[.*\])', text, re.S)
    if match_list:
        try:
            return json.loads(match_list.group(1))
        except json.JSONDecodeError:
            pass
            
    # 4. 如果还是失败，可能是 JSON 不完整或者格式极其混乱
    # 这里可以添加更复杂的修复逻辑（如修复未闭合的引号），但通常用正则提取就够了
    
    return None
