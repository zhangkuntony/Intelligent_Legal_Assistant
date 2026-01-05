"""
文档处理缓存
"""

import os
import hashlib
import pickle
import time
from typing import Optional, Dict, Any

from .base_processor import ProcessedDocument


class DocumentCache:
    """文档处理缓存"""
    
    def __init__(self, cache_dir: str = None, ttl: int = 3600):
        """
        初始化缓存
        
        Args:
            cache_dir: 缓存目录路径
            ttl: 缓存生存时间（秒）
        """
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), '.document_cache')
        self.ttl = ttl
        
        # 确保缓存目录存在
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        # 使用文件路径、大小和修改时间计算哈希
        file_stat = os.stat(file_path)
        hash_input = f"{file_path}:{file_stat.st_size}:{file_stat.st_mtime}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _get_cache_path(self, file_hash: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{file_hash}.pkl")
    
    def _is_cache_valid(self, cache_path: str) -> bool:
        """检查缓存是否有效"""
        if not os.path.exists(cache_path):
            return False
        
        # 检查缓存文件是否过期
        cache_mtime = os.path.getmtime(cache_path)
        current_time = time.time()
        
        return (current_time - cache_mtime) < self.ttl
    
    async def get_cached_result(self, file_path: str) -> Optional[ProcessedDocument]:
        """获取缓存的处理结果"""
        try:
            file_hash = self._get_file_hash(file_path)
            cache_path = self._get_cache_path(file_hash)
            
            # 检查缓存是否存在且有效
            if not self._is_cache_valid(cache_path):
                return None
            
            # 加载缓存数据
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
            
            # 验证缓存数据的完整性
            if not self._validate_cache_data(cached_data):
                self._remove_cache(file_hash)
                return None
            
            return cached_data
            
        except Exception:
            # 缓存读取失败，返回None
            return None
    
    async def cache_result(self, file_path: str, result: ProcessedDocument):
        """缓存处理结果"""
        try:
            file_hash = self._get_file_hash(file_path)
            cache_path = self._get_cache_path(file_hash)
            
            # 保存缓存数据
            with open(cache_path, 'wb') as f:
                pickle.dump(result, f)
            
            # 更新缓存文件的修改时间
            os.utime(cache_path, None)
            
        except Exception as e:
            # 缓存保存失败，记录日志但继续执行
            print(f"缓存保存失败: {str(e)}")
    
    def _validate_cache_data(self, cached_data: Any) -> bool:
        """验证缓存数据的完整性"""
        # 检查是否是ProcessedDocument实例
        if not isinstance(cached_data, ProcessedDocument):
            return False
        
        # 检查必要字段是否存在
        required_fields = ['original_path', 'extracted_text', 'chunks', 'metadata', 'status']
        for field in required_fields:
            if not hasattr(cached_data, field):
                return False
        
        return True
    
    def _remove_cache(self, file_hash: str):
        """移除缓存文件"""
        cache_path = self._get_cache_path(file_hash)
        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
        except Exception:
            pass
    
    async def clear_expired_cache(self) -> int:
        """清理过期缓存"""
        expired_count = 0
        current_time = time.time()
        
        try:
            for cache_file in os.listdir(self.cache_dir):
                if not cache_file.endswith('.pkl'):
                    continue
                
                cache_path = os.path.join(self.cache_dir, cache_file)
                cache_mtime = os.path.getmtime(cache_path)
                
                if (current_time - cache_mtime) >= self.ttl:
                    try:
                        os.remove(cache_path)
                        expired_count += 1
                    except Exception:
                        pass
            
        except Exception as e:
            print(f"清理过期缓存失败: {str(e)}")
        
        return expired_count
    
    async def clear_all_cache(self) -> int:
        """清理所有缓存"""
        cleared_count = 0
        
        try:
            for cache_file in os.listdir(self.cache_dir):
                if cache_file.endswith('.pkl'):
                    cache_path = os.path.join(self.cache_dir, cache_file)
                    try:
                        os.remove(cache_path)
                        cleared_count += 1
                    except Exception:
                        pass
            
        except Exception as e:
            print(f"清理所有缓存失败: {str(e)}")
        
        return cleared_count
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')]
            total_size = 0
            
            for cache_file in cache_files:
                cache_path = os.path.join(self.cache_dir, cache_file)
                total_size += os.path.getsize(cache_path)
            
            return {
                'total_files': len(cache_files),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'cache_dir': self.cache_dir,
                'ttl_seconds': self.ttl
            }
            
        except Exception:
            return {
                'total_files': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'cache_dir': self.cache_dir,
                'ttl_seconds': self.ttl
            }
    
    def set_ttl(self, ttl: int):
        """设置缓存生存时间"""
        self.ttl = ttl
    
    def set_cache_dir(self, cache_dir: str):
        """设置缓存目录"""
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)


class MemoryCache:
    """内存缓存（用于临时存储）"""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self._cache:
            return None
        
        cache_item = self._cache[key]
        
        # 检查是否过期
        if time.time() - cache_item['timestamp'] > self.ttl:
            del self._cache[key]
            return None
        
        return cache_item['value']
    
    async def set(self, key: str, value: Any):
        """设置缓存值"""
        # 如果缓存已满，移除最旧的项
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['timestamp'])
            del self._cache[oldest_key]
        
        self._cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    async def delete(self, key: str):
        """删除缓存项"""
        if key in self._cache:
            del self._cache[key]
    
    async def clear(self):
        """清空缓存"""
        self._cache.clear()
    
    async def clear_expired(self) -> int:
        """清理过期缓存"""
        expired_keys = []
        current_time = time.time()
        
        for key, item in self._cache.items():
            if current_time - item['timestamp'] > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        current_time = time.time()
        expired_count = 0
        
        for item in self._cache.values():
            if current_time - item['timestamp'] > self.ttl:
                expired_count += 1
        
        return {
            'total_items': len(self._cache),
            'expired_items': expired_count,
            'max_size': self.max_size,
            'ttl_seconds': self.ttl
        }