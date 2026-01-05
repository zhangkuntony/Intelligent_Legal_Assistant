"""
批量文档处理器
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_processor import ProcessedDocument
from .processor_factory import DocumentProcessorFactory
from .exceptions import BatchProcessingError


class BatchProcessor:
    """批量文档处理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.max_workers = self.config.get('max_workers', 4)
        self.batch_size = self.config.get('batch_size', 10)
        self.timeout_seconds = self.config.get('timeout_seconds', 300)
    
    async def process_batch(self, file_paths: List[str], 
                           max_workers: int = None,
                           progress_callback = None) -> List[ProcessedDocument]:
        """批量处理多个文件"""
        
        if max_workers is None:
            max_workers = self.max_workers
        
        total_files = len(file_paths)
        processed_files = 0
        failed_files = []
        results = []
        
        # 分批处理
        for i in range(0, total_files, self.batch_size):
            batch_files = file_paths[i:i + self.batch_size]
            
            # 处理当前批次
            batch_results = await self._process_batch_parallel(
                batch_files, max_workers, progress_callback
            )
            
            # 收集结果
            for file_path, result in zip(batch_files, batch_results):
                processed_files += 1
                
                if result.status.value == 'completed':
                    results.append(result)
                else:
                    failed_files.append({
                        'file_path': file_path,
                        'error': result.processing_stats.errors[0] if result.processing_stats.errors else 'Unknown error'
                    })
                
                # 调用进度回调
                if progress_callback:
                    await progress_callback(
                        processed_files, total_files, file_path, 
                        result.status.value, failed_files
                    )
        
        # 如果有失败的文件，抛出异常
        if failed_files:
            raise BatchProcessingError(
                failed_files, total_files, len(results)
            )
        
        return results
    
    async def _process_batch_parallel(self, file_paths: List[str], 
                                     max_workers: int,
                                     progress_callback = None) -> List[ProcessedDocument]:
        """并行处理批次文件"""
        
        # 使用线程池执行同步处理任务
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 创建处理任务
            future_to_file = {
                executor.submit(self._process_single_file, file_path): file_path
                for file_path in file_paths
            }
            
            # 收集结果
            results = []
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result(timeout=self.timeout_seconds)
                    results.append(result)
                except Exception as e:
                    # 处理失败
                    failed_result = ProcessedDocument(
                        original_path=file_path,
                        extracted_text="",
                        chunks=[],
                        metadata={},
                        processing_stats=None,
                        status="failed"
                    )
                    results.append(failed_result)
        
        return results
    
    def _process_single_file(self, file_path: str) -> ProcessedDocument:
        """处理单个文件（同步版本）"""
        try:
            # 创建适合的处理器
            processor = DocumentProcessorFactory.create_processor(
                file_path=file_path, 
                config=self.config
            )
            
            # 同步处理文件
            # 注意：这里使用了asyncio.run来运行异步方法
            # 在实际应用中，可能需要使用更复杂的异步处理策略
            result = asyncio.run(processor.process_file(file_path))
            return result
            
        except Exception as e:
            # 创建失败结果
            return ProcessedDocument(
                original_path=file_path,
                extracted_text="",
                chunks=[],
                metadata={},
                processing_stats=None,
                status="failed"
            )
    
    async def validate_batch(self, file_paths: List[str]) -> Dict[str, Any]:
        """验证批量文件"""
        validation_results = {
            'total_files': len(file_paths),
            'valid_files': [],
            'invalid_files': [],
            'supported_formats': [],
            'unsupported_formats': []
        }
        
        for file_path in file_paths:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                validation_results['invalid_files'].append({
                    'file_path': file_path,
                    'reason': '文件不存在'
                })
                continue
            
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            max_size = self.config.get('max_file_size', 50 * 1024 * 1024)
            if file_size > max_size:
                validation_results['invalid_files'].append({
                    'file_path': file_path,
                    'reason': f'文件大小超过限制 ({file_size} > {max_size})'
                })
                continue
            
            # 检查文件格式支持
            if not DocumentProcessorFactory.is_format_supported(file_path):
                validation_results['unsupported_formats'].append(file_path)
                continue
            
            # 验证通过
            validation_results['valid_files'].append(file_path)
            validation_results['supported_formats'].append(file_path)
        
        return validation_results
    
    def get_processing_stats(self, results: List[ProcessedDocument]) -> Dict[str, Any]:
        """获取处理统计信息"""
        if not results:
            return {}
        
        total_files = len(results)
        completed_files = len([r for r in results if r.status.value == 'completed'])
        failed_files = total_files - completed_files
        
        total_chars = sum(len(r.extracted_text) for r in results if r.status.value == 'completed')
        total_chunks = sum(len(r.chunks) for r in results if r.status.value == 'completed')
        
        processing_times = [
            r.processing_stats.processing_time 
            for r in results 
            if r.status.value == 'completed' and r.processing_stats
        ]
        
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        max_processing_time = max(processing_times) if processing_times else 0
        min_processing_time = min(processing_times) if processing_times else 0
        
        return {
            'total_files': total_files,
            'completed_files': completed_files,
            'failed_files': failed_files,
            'success_rate': completed_files / total_files if total_files > 0 else 0,
            'total_characters': total_chars,
            'total_chunks': total_chunks,
            'average_processing_time': avg_processing_time,
            'max_processing_time': max_processing_time,
            'min_processing_time': min_processing_time,
            'average_chars_per_file': total_chars / completed_files if completed_files > 0 else 0,
            'average_chunks_per_file': total_chunks / completed_files if completed_files > 0 else 0
        }
    
    async def process_with_retry(self, file_paths: List[str], 
                                max_retries: int = 3,
                                retry_delay: float = 1.0) -> List[ProcessedDocument]:
        """带重试的批量处理"""
        
        results = []
        remaining_files = file_paths.copy()
        
        for attempt in range(max_retries + 1):
            if not remaining_files:
                break
            
            # 处理当前剩余文件
            current_results = await self.process_batch(remaining_files)
            
            # 分离成功和失败的结果
            successful_results = []
            failed_files = []
            
            for file_path, result in zip(remaining_files, current_results):
                if result.status.value == 'completed':
                    successful_results.append(result)
                else:
                    failed_files.append(file_path)
            
            # 添加成功结果
            results.extend(successful_results)
            
            # 如果没有失败文件或达到最大重试次数，退出
            if not failed_files or attempt == max_retries:
                break
            
            # 等待重试
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避
            
            # 更新剩余文件
            remaining_files = failed_files
        
        return results
    
    def save_results(self, results: List[ProcessedDocument], 
                    output_dir: str,
                    format: str = 'json') -> List[str]:
        """保存处理结果"""
        
        output_files = []
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        for result in results:
            if result.status.value != 'completed':
                continue
            
            # 生成输出文件名
            input_filename = Path(result.original_path).stem
            output_filename = f"{input_filename}_processed.{format}"
            output_path = Path(output_dir) / output_filename
            
            try:
                if format == 'json':
                    self._save_as_json(result, output_path)
                elif format == 'txt':
                    self._save_as_text(result, output_path)
                elif format == 'csv':
                    self._save_as_csv(result, output_path)
                else:
                    raise ValueError(f"不支持的输出格式: {format}")
                
                output_files.append(str(output_path))
                
            except Exception as e:
                # 记录保存错误但继续处理其他文件
                print(f"保存文件失败 {output_path}: {str(e)}")
        
        return output_files
    
    def _save_as_json(self, result: ProcessedDocument, output_path: Path):
        """保存为JSON格式"""
        import json
        
        output_data = {
            'original_path': result.original_path,
            'extracted_text': result.extracted_text,
            'chunks': [
                {
                    'chunk_id': chunk.chunk_id,
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_index,
                    'metadata': chunk.metadata,
                    'page_number': chunk.page_number,
                    'section_title': chunk.section_title
                }
                for chunk in result.chunks
            ],
            'metadata': result.metadata,
            'processing_stats': {
                'start_time': result.processing_stats.start_time.isoformat() if result.processing_stats.start_time else None,
                'end_time': result.processing_stats.end_time.isoformat() if result.processing_stats.end_time else None,
                'total_chars': result.processing_stats.total_chars,
                'total_chunks': result.processing_stats.total_chunks,
                'processing_time': result.processing_stats.processing_time,
                'memory_usage': result.processing_stats.memory_usage,
                'errors': result.processing_stats.errors
            },
            'status': result.status.value
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    def _save_as_text(self, result: ProcessedDocument, output_path: Path):
        """保存为文本格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"原始文件: {result.original_path}\n")
            f.write(f"状态: {result.status.value}\n")
            f.write(f"总字符数: {len(result.extracted_text)}\n")
            f.write(f"总分块数: {len(result.chunks)}\n")
            f.write("\n" + "="*50 + "\n")
            f.write("提取的文本内容:\n")
            f.write("="*50 + "\n")
            f.write(result.extracted_text)
            f.write("\n" + "="*50 + "\n")
            f.write("分块内容:\n")
            f.write("="*50 + "\n")
            
            for i, chunk in enumerate(result.chunks):
                f.write(f"\n分块 {i+1} (ID: {chunk.chunk_id}):\n")
                f.write("-"*30 + "\n")
                f.write(chunk.content)
                f.write("\n")
    
    def _save_as_csv(self, result: ProcessedDocument, output_path: Path):
        """保存为CSV格式"""
        import csv
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # 写入头部
            writer.writerow(['chunk_id', 'chunk_index', 'content', 'page_number', 'section_title'])
            
            # 写入分块数据
            for chunk in result.chunks:
                writer.writerow([
                    chunk.chunk_id,
                    chunk.chunk_index,
                    chunk.content.replace('\n', ' ').replace('\r', ''),
                    chunk.page_number or '',
                    chunk.section_title or ''
                ])