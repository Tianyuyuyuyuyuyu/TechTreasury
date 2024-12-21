import os
import logging
from pathlib import Path

def setup_logging(log_file='conversion.log'):
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_relative_path(base_path, full_path):
    """获取相对路径"""
    return os.path.relpath(full_path, base_path)

def is_hidden_file(file_path):
    """检查是否为隐藏文件"""
    return os.path.basename(file_path).startswith('.')

def get_safe_filename(filename):
    """获取安全的文件名"""
    return "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '-', '_', '.')]).rstrip() 