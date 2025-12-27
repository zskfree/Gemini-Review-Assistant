# new_workflow/src/logger.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime

# 默认日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

def setup_logger(name: str = "ScholarFlow", log_level: int = logging.INFO, log_file: str = None) -> logging.Logger:
    """
    配置并返回一个 Logger 实例
    
    Args:
        name: Logger 名称
        log_level: 日志级别
        log_file: 日志文件名（若未指定，默认使用 scholarconf_{date}.log）
        
    Returns:
        logging.Logger: 配置好的 Logger
    """
    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)
    
    if log_file is None:
        current_date = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(LOG_DIR, f"scholarflow_{current_date}.log")
    else:
        log_file = os.path.join(LOG_DIR, log_file)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 防止重复添加 Handler
    if logger.handlers:
        return logger

    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1.控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    # 2. 文件 Handler (滚动日志，最大 5MB，保留 5 个备份)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8', delay=True
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)

    return logger

# 创建默认实例
logger = setup_logger()
