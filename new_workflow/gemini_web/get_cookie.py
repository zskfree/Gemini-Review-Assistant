import json
import os
try:
    from src.logger import logger
except ImportError:
    # Fallback for standalone testing if needed, though app context is preferred
    import logging
    logger = logging.getLogger(__name__)

def get_gemini_tokens(cookie_path=None):
    """
    从cookie.json文件中提取Gemini所需的token
    :param cookie_path: cookie.json 文件的路径。如果为None，则尝试默认路径。
    :return: tuple (token_id, token_ts) 如果成功，否则返回 (None, None)
    """
    try:
        if not cookie_path:
            # 默认路径: 当前文件所在目录下的 cookie/cookie.json
            cookie_path = os.path.join(os.path.dirname(__file__), 'cookie', 'cookie.json')

        if not os.path.exists(cookie_path):
             logger.error(f"❌ 错误: 找不到 Cookie 文件: {cookie_path}")
             return None, None
             
        with open(cookie_path, 'r', encoding='utf-8') as f:
            cookies_list = json.load(f)
        
        tokens = {
            '__Secure-1PSID': None,
            '__Secure-1PSIDTS': None
        }
        
        for c in cookies_list:
            if c['name'] in tokens:
                tokens[c['name']] = c['value']
        
        if tokens['__Secure-1PSID'] and tokens['__Secure-1PSIDTS']:
            return tokens['__Secure-1PSID'], tokens['__Secure-1PSIDTS']
        else:
            logger.error("❌ 未能找到必需的 Cookie 信息")
            logger.error(f"找到 __Secure-1PSID: {'是' if tokens['__Secure-1PSID'] else '否'}")
            logger.error(f"找到 __Secure-1PSIDTS: {'是' if tokens['__Secure-1PSIDTS'] else '否'}")
            return None, None
            
    except json.JSONDecodeError:
        logger.error(f"❌ 错误: Cookie 文件格式不正确 (JSON解析失败): {cookie_path}")
        return None, None
    except Exception as e:
        logger.error(f"❌ 运行出错: {e}")
        return None, None

def print_gemini_config():
    """
    提取并打印Gemini配置信息，方便复制到代码中
    """
    token_id, token_ts = get_gemini_tokens()
    
    if token_id and token_ts:
        logger.info("\n📝 可直接复制到代码中的格式:")
        logger.info("CONFIG = {")
        logger.info(f"    \"token_id\": \"{token_id}\",")
        logger.info(f"    \"token_ts\": \"{token_ts}\",")