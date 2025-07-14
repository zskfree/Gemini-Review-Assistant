import yaml
import os
from typing import Dict, Any, List

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """加载 YAML 配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config
    except FileNotFoundError:
        print(f"错误: 配置文件 '{config_path}' 未找到。")
        raise
    except yaml.YAMLError as e:
        print(f"错误: 解析配置文件 '{config_path}' 失败: {e}")
        raise
    except Exception as e:
        print(f"加载配置时发生未知错误: {e}")
        raise


def validate_config(config: Dict[str, Any]) -> List[str]:
    """验证配置文件的有效性"""
    errors = []
    
    # 检查必需的字段
    required_fields = {
        'llm': ['model_name', 'api_key'],
        'paths': ['pdf_dir', 'txt_dir', 'cache_file', 'summary_output_file', 'final_output_file'],
        'prompts': ['research_theme', 'summary_prompt', 'review_final_prompt', 'qualitative_final_prompt'],
        'cache': ['enabled']
    }
    
    for section, fields in required_fields.items():
        if section not in config:
            errors.append(f"缺少配置节: {section}")
            continue
        
        for field in fields:
            if field not in config[section]:
                errors.append(f"缺少配置项: {section}.{field}")
    
    # 检查数值范围
    if 'llm' in config:
        if 'temperature' in config['llm']:
            temp = config['llm']['temperature']
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                errors.append("温度参数必须在0.0-2.0之间")
        
        if 'max_retries' in config['llm']:
            retries = config['llm']['max_retries']
            if not isinstance(retries, int) or retries < 1:
                errors.append("最大重试次数必须是大于0的整数")
    
    return errors


def load_text_file(file_path: str) -> str:
    """加载指定路径的文本文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"错误: 文本文件 '{file_path}' 未找到。")
        # 可以返回空字符串或 None，或者重新抛出异常，取决于主流程如何处理
        return "" # 或者 raise
    except Exception as e:
        print(f"读取文件 '{file_path}' 时出错: {e}")
        return "" # 或者 raise


def load_all_prompts(config: Dict[str, Any]) -> Dict[str, str]:
    """根据配置加载所有需要的提示词文件"""
    prompts = {}
    txt_dir = config['paths']['txt_dir']
    prompt_files = config['prompts']

    for key, filename in prompt_files.items():
        file_path = os.path.join(txt_dir, filename)
        prompts[key] = load_text_file(file_path)
        if not prompts[key]:
            print(f"警告: 提示词 '{key}' ({filename}) 加载失败或为空。")
            # 根据需要决定是否中止程序

    return prompts


def save_config(config: Dict[str, Any], config_path: str = "config.yaml") -> None:
    """保存配置到YAML文件"""
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, 
                     sort_keys=False, indent=2)
    except Exception as e:
        raise Exception(f"保存配置文件失败: {e}")