"""
工具函数模块
"""

import os
import hashlib
import mimetypes
from typing import Optional, Dict, Any
from pathlib import Path


def get_file_info(file_path: str) -> Dict[str, Any]:
    """获取文件信息"""
    try:
        file_stat = os.stat(file_path)
        
        return {
            'path': file_path,
            'name': Path(file_path).name,
            'extension': Path(file_path).suffix.lower(),
            'size_bytes': file_stat.st_size,
            'size_mb': file_stat.st_size / (1024 * 1024),
            'created_time': file_stat.st_ctime,
            'modified_time': file_stat.st_mtime,
            'is_file': os.path.isfile(file_path),
            'is_directory': os.path.isdir(file_path),
            'exists': os.path.exists(file_path)
        }
    except Exception as e:
        return {
            'path': file_path,
            'error': str(e),
            'exists': False
        }


def calculate_file_hash(file_path: str, algorithm: str = 'md5') -> Optional[str]:
    """计算文件哈希值"""
    try:
        hash_func = getattr(hashlib, algorithm)()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    except Exception:
        return None


def detect_mime_type(file_path: str) -> Optional[str]:
    """检测文件MIME类型"""
    try:
        # 使用mimetypes库
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if mime_type:
            return mime_type
        
        # 如果mimetypes无法检测，尝试基于扩展名
        extension = Path(file_path).suffix.lower()
        
        mime_map = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.markdown': 'text/markdown',
            '.rst': 'text/x-rst',
            '.log': 'text/plain',
        }
        
        return mime_map.get(extension)
    except Exception:
        return None


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"


def safe_filename(filename: str, max_length: int = 255) -> str:
    """生成安全的文件名"""
    # 移除非法字符
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # 移除控制字符
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # 限制长度
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext)
        filename = name[:max_name_length] + ext
    
    return filename


def ensure_directory_exists(directory: str) -> bool:
    """确保目录存在"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception:
        return False


def is_text_file(file_path: str) -> bool:
    """检查是否是文本文件"""
    text_extensions = {'.txt', '.md', '.markdown', '.rst', '.log', '.csv', '.json', '.xml', '.html', '.htm'}
    
    extension = Path(file_path).suffix.lower()
    return extension in text_extensions


def is_archive_file(file_path: str) -> bool:
    """检查是否是压缩文件"""
    archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
    
    extension = Path(file_path).suffix.lower()
    return extension in archive_extensions


def is_image_file(file_path: str) -> bool:
    """检查是否是图像文件"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'}
    
    extension = Path(file_path).suffix.lower()
    return extension in image_extensions


def split_file_path(file_path: str) -> Dict[str, str]:
    """分割文件路径"""
    path_obj = Path(file_path)
    
    return {
        'directory': str(path_obj.parent),
        'filename': path_obj.name,
        'stem': path_obj.stem,
        'extension': path_obj.suffix,
        'absolute_path': str(path_obj.resolve())
    }


def get_relative_path(base_path: str, target_path: str) -> Optional[str]:
    """获取相对路径"""
    try:
        base = Path(base_path).resolve()
        target = Path(target_path).resolve()
        
        return str(target.relative_to(base))
    except ValueError:
        # 如果目标路径不在基础路径下，返回绝对路径
        return str(target_path)


def validate_file_path(file_path: str, check_exists: bool = True) -> Dict[str, Any]:
    """验证文件路径"""
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # 检查路径长度
    if len(file_path) > 260:  # Windows路径长度限制
        result['valid'] = False
        result['errors'].append('文件路径过长')
    
    # 检查非法字符
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        if char in file_path:
            result['valid'] = False
            result['errors'].append(f'包含非法字符: {char}')
            break
    
    # 检查文件是否存在
    if check_exists and not os.path.exists(file_path):
        result['valid'] = False
        result['errors'].append('文件不存在')
    
    # 检查是否是文件
    if check_exists and os.path.exists(file_path) and not os.path.isfile(file_path):
        result['valid'] = False
        result['errors'].append('路径不是文件')
    
    # 检查文件扩展名
    extension = Path(file_path).suffix.lower()
    if not extension:
        result['warnings'].append('文件没有扩展名')
    
    return result


def create_temp_file(prefix: str = 'temp', suffix: str = '.tmp', 
                    content: str = None, directory: str = None) -> Optional[str]:
    """创建临时文件"""
    import tempfile
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            prefix=prefix,
            suffix=suffix,
            dir=directory,
            delete=False,
            encoding='utf-8'
        ) as temp_file:
            
            if content:
                temp_file.write(content)
            
            return temp_file.name
    
    except Exception:
        return None


def read_file_chunks(file_path: str, chunk_size: int = 8192) -> bytes:
    """分块读取文件"""
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def count_file_lines(file_path: str) -> Optional[int]:
    """计算文件行数"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return None


def get_file_encoding(file_path: str) -> Optional[str]:
    """检测文件编码"""
    import chardet
    
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(4096)
        
        detection_result = chardet.detect(raw_data)
        
        if detection_result['confidence'] > 0.7:
            return detection_result['encoding']
        else:
            # 尝试常见编码
            common_encodings = ['utf-8', 'gbk', 'gb2312', 'latin1', 'ascii']
            
            for encoding in common_encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(1024)
                    return encoding
                except UnicodeDecodeError:
                    continue
        
        return None
    
    except Exception:
        return None