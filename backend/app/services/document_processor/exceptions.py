"""
文件处理模块异常定义
"""

class DocumentProcessingError(Exception):
    """文档处理异常基类"""
    
    def __init__(self, message: str, file_path: str = None, error_code: str = None):
        self.message = message
        self.file_path = file_path
        self.error_code = error_code
        super().__init__(self.message)
    
    def __str__(self):
        if self.file_path:
            return f"{self.message} (文件: {self.file_path})"
        return self.message


class UnsupportedFormatError(DocumentProcessingError):
    """不支持的文件格式"""
    
    def __init__(self, file_path: str, supported_formats: list = None):
        message = f"不支持的文件格式: {file_path}"
        if supported_formats:
            message += f", 支持格式: {', '.join(supported_formats)}"
        
        super().__init__(message, file_path, "UNSUPPORTED_FORMAT")


class CorruptedFileError(DocumentProcessingError):
    """文件损坏异常"""
    
    def __init__(self, file_path: str, reason: str = None):
        message = f"文件损坏或无法读取: {file_path}"
        if reason:
            message += f" ({reason})"
        
        super().__init__(message, file_path, "CORRUPTED_FILE")


class ExtractionError(DocumentProcessingError):
    """文本提取异常"""
    
    def __init__(self, file_path: str, extraction_type: str = None, details: str = None):
        message = f"文本提取失败: {file_path}"
        if extraction_type:
            message += f" (提取类型: {extraction_type})"
        if details:
            message += f" (详情: {details})"
        
        super().__init__(message, file_path, "EXTRACTION_ERROR")


class FileSizeExceededError(DocumentProcessingError):
    """文件大小超出限制异常"""
    
    def __init__(self, file_path: str, max_size: int, actual_size: int):
        message = f"文件大小超出限制: {file_path} (最大: {max_size}字节, 实际: {actual_size}字节)"
        super().__init__(message, file_path, "FILE_SIZE_EXCEEDED")


class TimeoutError(DocumentProcessingError):
    """处理超时异常"""
    
    def __init__(self, file_path: str, timeout_seconds: int):
        message = f"文件处理超时: {file_path} (超时时间: {timeout_seconds}秒)"
        super().__init__(message, file_path, "TIMEOUT_ERROR")


class MemoryLimitExceededError(DocumentProcessingError):
    """内存限制超出异常"""
    
    def __init__(self, file_path: str, memory_limit: int):
        message = f"内存使用超出限制: {file_path} (限制: {memory_limit}MB)"
        super().__init__(message, file_path, "MEMORY_LIMIT_EXCEEDED")


class ConfigurationError(DocumentProcessingError):
    """配置错误异常"""
    
    def __init__(self, config_key: str, expected_type: str = None):
        message = f"配置错误: {config_key}"
        if expected_type:
            message += f" (期望类型: {expected_type})"
        
        super().__init__(message, error_code="CONFIGURATION_ERROR")


class DependencyError(DocumentProcessingError):
    """依赖缺失异常"""
    
    def __init__(self, dependency_name: str, installation_command: str = None):
        message = f"缺少必要依赖: {dependency_name}"
        if installation_command:
            message += f" (安装命令: {installation_command})"
        
        super().__init__(message, error_code="DEPENDENCY_ERROR")


class PermissionError(DocumentProcessingError):
    """权限错误异常"""
    
    def __init__(self, file_path: str, operation: str):
        message = f"权限不足: 无法{operation}文件 {file_path}"
        super().__init__(message, file_path, "PERMISSION_ERROR")


class NetworkError(DocumentProcessingError):
    """网络错误异常"""
    
    def __init__(self, operation: str, url: str = None, status_code: int = None):
        message = f"网络错误: {operation}"
        if url:
            message += f" (URL: {url})"
        if status_code:
            message += f" (状态码: {status_code})"
        
        super().__init__(message, error_code="NETWORK_ERROR")


class ValidationError(DocumentProcessingError):
    """验证错误异常"""
    
    def __init__(self, file_path: str, validation_rule: str, details: str = None):
        message = f"文件验证失败: {file_path} (规则: {validation_rule})"
        if details:
            message += f" (详情: {details})"
        
        super().__init__(message, file_path, "VALIDATION_ERROR")


class BatchProcessingError(DocumentProcessingError):
    """批量处理错误异常"""
    
    def __init__(self, failed_files: list, total_files: int, success_files: int):
        message = f"批量处理完成，但有 {len(failed_files)} 个文件失败 (总数: {total_files}, 成功: {success_files})"
        details = {
            'failed_files': failed_files,
            'total_files': total_files,
            'success_files': success_files
        }
        
        super().__init__(message, error_code="BATCH_PROCESSING_ERROR")
        self.details = details