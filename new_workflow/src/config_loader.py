# config_loader.py
import yaml
import os
from typing import Dict, Any, List
from .logger import logger

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载 YAML 配置文件
    
    如果不指定路径，会从以下位置按顺序查找：
    1. 当前工作目录的 new_workflow/config.yaml
    2. 脚本所在目录向上查找
    """
    if config_path is None:
        # 优先查找项目根目录下的 new_workflow/config.yaml
        possible_paths = [
            "new_workflow/config.yaml",  # 从项目根目录运行
            os.path.join(os.path.dirname(__file__), "../config.yaml"),  # 从 src 目录运行
            os.path.join(os.path.dirname(__file__), "../../new_workflow/config.yaml"),  # 备用路径
        ]
        
        config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
        
        if config_path is None:
            raise FileNotFoundError(
                f"配置文件未找到。尝试了以下路径:\n" + 
                "\n".join(possible_paths)
            )
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logger.error(f"错误: 配置文件 '{config_path}' 未找到。")
        raise
    except yaml.YAMLError as e:
        logger.error(f"错误: 解析配置文件 '{config_path}' 失败: {e}")
        raise
    except Exception as e:
        logger.error(f"加载配置时发生未知错误: {e}")
        raise

def load_text_file(file_path: str) -> str:
    """加载指定路径的文本文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"错误: 文本文件 '{file_path}' 未找到。")
        return ""
    except Exception as e:
        logger.error(f"读取文件 '{file_path}' 时出错: {e}")
        return ""

def get_config(key: str, default: Any = None) -> Any:
    """获取配置项的值，支持嵌套键（使用点号分隔）"""
    try:
        config = load_config()
        keys = key.split('.')
        value = config
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default
    except Exception as e:
        logger.error(f"获取配置项 '{key}' 失败: {e}")
        return default

def update_recursive(original: Dict[str, Any], new_data: Dict[str, Any]):
    """递归更新字典，保留原有的结构"""
    for key, value in new_data.items():
        if key in original and isinstance(original[key], dict) and isinstance(value, dict):
            update_recursive(original[key], value)
        else:
            original[key] = value

def save_config(config_path: str, new_config: Dict[str, Any]):
    """
    保存配置到文件，尽量保留原有格式和注释
    优先尝试使用 ruamel.yaml (如果安装了)，否则使用 pyyaml
    """
    try:
        from ruamel.yaml import YAML
        yaml_parser = YAML()
        yaml_parser.preserve_quotes = True
        
        # 读取原始文件以获取结构
        with open(config_path, 'r', encoding='utf-8') as f:
            code_yaml = yaml_parser.load(f)
            
        # 更新数据
        update_recursive(code_yaml, new_config)
        
        # 写回文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml_parser.dump(code_yaml, f)
            
    except ImportError:
        # 降级方案：使用 pyyaml (无法保留注释)
        logger.warning("ruamel.yaml not found, falling back to standard yaml (comments will be lost)")
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(new_config, f, allow_unicode=True, sort_keys=False)
            
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise

if __name__ == "__main__":
    api_key = get_config("api.genai_key")
    print(f"API Key: {api_key[:50]}..." if api_key else "API Key not found")