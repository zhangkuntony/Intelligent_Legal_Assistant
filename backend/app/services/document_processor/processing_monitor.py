"""
处理监控器
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from .base_processor import ProcessingStats


@dataclass
class ProcessingEvent:
    """处理事件"""
    timestamp: datetime
    file_path: str
    event_type: str  # 'start', 'end', 'error', 'warning'
    message: str
    details: Dict[str, Any] = None


class ProcessingMonitor:
    """处理监控器"""

    def __init__(self, log_file: str = None, enable_console_log: bool = True):
        """
        初始化监控器

        Args:
            log_file: 日志文件路径
            enable_console_log: 是否启用控制台日志
        """
        self.log_file = log_file
        self.enable_console_log = enable_console_log
        self.events: List[ProcessingEvent] = []
        self.processing_stats: Dict[str, ProcessingStats] = {}

        # 配置日志
        self._setup_logging()

    def _setup_logging(self):
        """配置日志系统"""
        self.logger = logging.getLogger('document_processor')
        self.logger.setLevel(logging.INFO)

        # 避免重复添加处理器
        if not self.logger.handlers:
            # 控制台处理器
            if self.enable_console_log:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.INFO)
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

            # 文件处理器
            if self.log_file:
                file_handler = logging.FileHandler(self.log_file)
                file_handler.setLevel(logging.INFO)
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

    def log_processing_start(self, file_path: str, details: Dict[str, Any] = None):
        """记录处理开始"""
        event = ProcessingEvent(
            timestamp=datetime.now(),
            file_path=file_path,
            event_type='start',
            message=f'开始处理文件: {file_path}',
            details=details
        )

        self.events.append(event)
        self.logger.info(f'开始处理: {file_path}')

    def log_processing_end(self, file_path: str, stats: ProcessingStats):
        """记录处理结束"""
        # 保存统计信息
        self.processing_stats[file_path] = stats

        event = ProcessingEvent(
            timestamp=datetime.now(),
            file_path=file_path,
            event_type='end',
            message=f'文件处理完成: {file_path}',
            details={
                'processing_time': stats.processing_time,
                'total_chars': stats.total_chars,
                'total_chunks': stats.total_chunks
            }
        )

        self.events.append(event)
        self.logger.info(
            f'处理完成: {file_path} - '
            f'耗时: {stats.processing_time:.2f}s, '
            f'字符数: {stats.total_chars}, '
            f'分块数: {stats.total_chunks}'
        )

    def log_error(self, file_path: str, error: Exception, details: Dict[str, Any] = None):
        """记录错误"""
        event = ProcessingEvent(
            timestamp=datetime.now(),
            file_path=file_path,
            event_type='error',
            message=f'处理错误: {file_path} - {str(error)}',
            details=details or {}
        )

        self.events.append(event)
        self.logger.error(f'处理错误: {file_path} - {str(error)}')

    def log_warning(self, file_path: str, warning: str, details: Dict[str, Any] = None):
        """记录警告"""
        event = ProcessingEvent(
            timestamp=datetime.now(),
            file_path=file_path,
            event_type='warning',
            message=f'处理警告: {file_path} - {warning}',
            details=details or {}
        )

        self.events.append(event)
        self.logger.warning(f'处理警告: {file_path} - {warning}')

    def log_progress(self, file_path: str, progress: float, message: str = ''):
        """记录进度"""
        event = ProcessingEvent(
            timestamp=datetime.now(),
            file_path=file_path,
            event_type='progress',
            message=f'处理进度: {file_path} - {progress:.1%} {message}',
            details={'progress': progress}
        )

        self.events.append(event)
        self.logger.info(f'进度: {file_path} - {progress:.1%} {message}')

    def get_processing_summary(self) -> Dict[str, Any]:
        """获取处理摘要"""
        total_files = len(self.processing_stats)

        if total_files == 0:
            return {
                'total_files': 0,
                'successful_files': 0,
                'failed_files': 0,
                'total_processing_time': 0,
                'average_processing_time': 0,
                'total_characters': 0,
                'total_chunks': 0
            }

        # 计算统计信息
        successful_files = len([stats for stats in self.processing_stats.values()
                                if stats.end_time])
        failed_files = total_files - successful_files

        total_processing_time = sum(stats.processing_time for stats in self.processing_stats.values()
                                    if stats.processing_time)
        average_processing_time = total_processing_time / successful_files if successful_files > 0 else 0

        total_characters = sum(stats.total_chars for stats in self.processing_stats.values())
        total_chunks = sum(stats.total_chunks for stats in self.processing_stats.values())

        # 获取错误信息
        error_events = [e for e in self.events if e.event_type == 'error']
        error_summary = {}
        for error in error_events:
            error_msg = error.message
            if error_msg not in error_summary:
                error_summary[error_msg] = 0
            error_summary[error_msg] += 1

        return {
            'total_files': total_files,
            'successful_files': successful_files,
            'failed_files': failed_files,
            'success_rate': successful_files / total_files if total_files > 0 else 0,
            'total_processing_time': total_processing_time,
            'average_processing_time': average_processing_time,
            'total_characters': total_characters,
            'total_chunks': total_chunks,
            'error_summary': error_summary
        }

    def get_recent_events(self, limit: int = 100) -> List[ProcessingEvent]:
        """获取最近的事件"""
        return self.events[-limit:] if self.events else []

    def get_events_by_type(self, event_type: str) -> List[ProcessingEvent]:
        """按类型获取事件"""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_file(self, file_path: str) -> List[ProcessingEvent]:
        """按文件获取事件"""
        return [e for e in self.events if e.file_path == file_path]

    def clear_events(self):
        """清空事件记录"""
        self.events.clear()
        self.processing_stats.clear()

    def export_events(self, format: str = 'json') -> str:
        """导出事件数据"""
        if format == 'json':
            import json
            events_data = [
                {
                    'timestamp': event.timestamp.isoformat(),
                    'file_path': event.file_path,
                    'event_type': event.event_type,
                    'message': event.message,
                    'details': event.details
                }
                for event in self.events
            ]
            return json.dumps(events_data, ensure_ascii=False, indent=2)

        elif format == 'csv':
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入表头
            writer.writerow(['timestamp', 'file_path', 'event_type', 'message', 'details'])

            # 写入数据
            for event in self.events:
                writer.writerow([
                    event.timestamp.isoformat(),
                    event.file_path,
                    event.event_type,
                    event.message,
                    str(event.details) if event.details else ''
                ])

            return output.getvalue()

        else:
            raise ValueError(f"不支持的导出格式: {format}")

    def set_log_level(self, level: str):
        """设置日志级别"""
        level_map = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }

        if level.lower() in level_map:
            self.logger.setLevel(level_map[level.lower()])
            for handler in self.logger.handlers:
                handler.setLevel(level_map[level.lower()])


class RealTimeMonitor:
    """实时监控器"""

    def __init__(self):
        self.active_processes: Dict[str, Dict[str, Any]] = {}
        self.completed_processes: Dict[str, Dict[str, Any]] = {}
        self.callbacks = {
            'on_start': [],
            'on_progress': [],
            'on_complete': [],
            'on_error': []
        }

    def register_callback(self, event_type: str, callback):
        """注册回调函数"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def start_processing(self, file_path: str, details: Dict[str, Any] = None):
        """开始处理监控"""
        process_info = {
            'file_path': file_path,
            'start_time': time.time(),
            'progress': 0.0,
            'status': 'processing',
            'details': details or {}
        }

        self.active_processes[file_path] = process_info

        # 触发开始回调
        for callback in self.callbacks['on_start']:
            try:
                callback(file_path, details)
            except Exception as e:
                print(f"回调执行失败: {str(e)}")

    def update_progress(self, file_path: str, progress: float, message: str = ''):
        """更新处理进度"""
        if file_path not in self.active_processes:
            return

        self.active_processes[file_path]['progress'] = progress
        self.active_processes[file_path]['last_update'] = time.time()

        if message:
            self.active_processes[file_path]['last_message'] = message

        # 触发进度回调
        for callback in self.callbacks['on_progress']:
            try:
                callback(file_path, progress, message)
            except Exception as e:
                print(f"回调执行失败: {str(e)}")

    def complete_processing(self, file_path: str, result: Any):
        """完成处理"""
        if file_path not in self.active_processes:
            return

        process_info = self.active_processes[file_path]
        process_info['end_time'] = time.time()
        process_info['processing_time'] = process_info['end_time'] - process_info['start_time']
        process_info['status'] = 'completed'
        process_info['result'] = result

        # 移动到完成列表
        self.completed_processes[file_path] = process_info
        del self.active_processes[file_path]

        # 触发完成回调
        for callback in self.callbacks['on_complete']:
            try:
                callback(file_path, result)
            except Exception as e:
                print(f"回调执行失败: {str(e)}")

    def report_error(self, file_path: str, error: Exception):
        """报告错误"""
        if file_path not in self.active_processes:
            return

        process_info = self.active_processes[file_path]
        process_info['end_time'] = time.time()
        process_info['processing_time'] = process_info['end_time'] - process_info['start_time']
        process_info['status'] = 'error'
        process_info['error'] = str(error)

        # 移动到完成列表
        self.completed_processes[file_path] = process_info
        del self.active_processes[file_path]

        # 触发错误回调
        for callback in self.callbacks['on_error']:
            try:
                callback(file_path, error)
            except Exception as e:
                print(f"回调执行失败: {str(e)}")

    def get_active_processes(self) -> Dict[str, Dict[str, Any]]:
        """获取活动进程"""
        return self.active_processes.copy()

    def get_completed_processes(self) -> Dict[str, Dict[str, Any]]:
        """获取已完成进程"""
        return self.completed_processes.copy()

    def get_process_status(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取进程状态"""
        if file_path in self.active_processes:
            return self.active_processes[file_path]
        elif file_path in self.completed_processes:
            return self.completed_processes[file_path]
        else:
            return None

    def cleanup_old_processes(self, max_age: int = 3600):
        """清理旧进程"""
        current_time = time.time()

        # 清理完成进程
        old_completed = []
        for file_path, process_info in self.completed_processes.items():
            if current_time - process_info.get('end_time', 0) > max_age:
                old_completed.append(file_path)

        for file_path in old_completed:
            del self.completed_processes[file_path]

        # 检查超时活动进程
        timed_out = []
        for file_path, process_info in self.active_processes.items():
            last_update = process_info.get('last_update', process_info['start_time'])
            if current_time - last_update > max_age:
                timed_out.append(file_path)

        for file_path in timed_out:
            self.report_error(file_path, Exception("处理超时"))