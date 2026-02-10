"""
日志配置模块
统一的日志系统，替代散落的 print 语句
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name="discord_dashboard", log_dir=None, level=logging.INFO):
    """
    配置并返回 logger 实例
    
    - 控制台输出 (stdout)
    - 文件输出 (自动轮转: 5MB * 3 个文件)
    
    Args:
        name: logger 名称
        log_dir: 日志目录，默认从 config 读取
        level: 日志级别
    
    Returns:
        logging.Logger
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 格式
    fmt_console = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    fmt_file = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # 控制台 handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt_console)
    logger.addHandler(console)
    
    # 文件 handler (可选，如果 log_dir 可用)
    if log_dir is None:
        try:
            from config import LOGS_DIR
            log_dir = LOGS_DIR
        except ImportError:
            log_dir = None
    
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_path / "app.log",
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt_file)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name="discord_dashboard"):
    """获取已配置的 logger（如果未配置则自动初始化）"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
