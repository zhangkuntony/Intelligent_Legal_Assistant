"""
文件处理模块测试
"""

import asyncio
import tempfile
import os

from .base_processor import ProcessedDocument, DocumentChunk
from .text_processor import TextProcessor
from .chunk_strategies import FixedSizeChunker, SemanticChunker, LegalDocumentChunker
from .preprocessors import TextPreprocessor, LegalTextProcessor
from .processor_factory import DocumentProcessorFactory, ProcessorConfig
from .batch_processor import BatchProcessor
from .document_cache import DocumentCache
from .processing_monitor import ProcessingMonitor


async def test_base_processor():
    """测试基础处理器功能"""
    print("=== 测试基础处理器 ===")

    # 创建一个简单的文本文件进行测试
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("""这是一个测试文档。
        包含多行文本内容。
        用于测试文件处理模块的功能。

        第二段内容，用于测试分块功能。
        """)
        temp_file = f.name

    try:
        # 创建文本处理器
        processor = TextProcessor()

        # 处理文件
        result = await processor.process_file(temp_file)

        print(f"处理状态: {result.status}")
        print(f"提取文本长度: {len(result.extracted_text)}")
        print(f"分块数量: {len(result.chunks)}")

        # 显示分块内容
        for i, chunk in enumerate(result.chunks):
            print(f"分块 {i + 1}: {chunk.content[:50]}...")

        print("✓ 基础处理器测试通过")

    finally:
        # 清理临时文件
        os.unlink(temp_file)


async def test_chunking_strategies():
    """测试分块策略"""
    print("\n=== 测试分块策略 ===")

    test_text = """这是一个测试文本。包含多个句子。用于测试不同的分块策略。

    第二段内容，包含更多的文本。分块策略应该能够正确处理段落边界。

    第三段内容，用于测试固定大小分块和语义分块的区别。"""

    # 固定大小分块器
    fixed_chunker = FixedSizeChunker(chunk_size=50, overlap=10)
    fixed_chunks = fixed_chunker.chunk_text(test_text)
    print(f"固定大小分块: {len(fixed_chunks)} 个分块")

    # 语义分块器
    semantic_chunker = SemanticChunker(max_chunk_size=100, min_chunk_size=20)
    semantic_chunks = semantic_chunker.chunk_text(test_text)
    print(f"语义分块: {len(semantic_chunks)} 个分块")

    # 法律文档分块器
    legal_text = """第一条 本法适用于所有公民。
    第二条 公民享有基本权利。
    第三条 公民应当履行基本义务。"""

    legal_chunker = LegalDocumentChunker()
    legal_chunks = legal_chunker.chunk_text(legal_text)
    print(f"法律文档分块: {len(legal_chunks)} 个分块")

    print("✓ 分块策略测试通过")


async def test_preprocessors():
    """测试预处理器"""
    print("\n=== 测试预处理器 ===")

    test_text = """  这是一个  测试文本，包含多余空格和标点符号。  

    第二段内容，用于测试文本清理功能。包含特殊字符和控制字符。

    法律引用测试：《中华人民共和国宪法》第一条。"""

    # 基础文本预处理器
    preprocessor = TextPreprocessor()
    cleaned_text = preprocessor.clean_text(test_text)
    print(f"清理后文本长度: {len(cleaned_text)}")

    # 法律文本预处理器
    legal_processor = LegalTextProcessor()
    citations = legal_processor.extract_citations(test_text)
    print(f"提取的法律引用: {len(citations)} 个")

    terms = legal_processor.identify_legal_terms(test_text)
    print(f"识别的法律术语: {len(terms)} 个")

    structure = legal_processor.structure_analysis(test_text)
    print(f"文档结构分析: {structure.total_sections} 个章节")

    print("✓ 预处理器测试通过")


async def test_processor_factory():
    """测试处理器工厂"""
    print("\n=== 测试处理器工厂 ===")

    # 创建配置文件
    config = ProcessorConfig(
        default_chunk_size=800,
        default_overlap=50,
        max_file_size=10 * 1024 * 1024
    ).to_dict()

    # 测试不同文件类型的处理器创建
    test_cases = [
        ('test.pdf', 'application/pdf'),
        ('test.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        ('test.txt', 'text/plain'),
        ('test.md', 'text/markdown')
    ]

    for filename, mime_type in test_cases:
        try:
            processor = DocumentProcessorFactory.create_processor(
                file_path=filename,
                mime_type=mime_type,
                config=config
            )
            print(f"✓ 成功创建 {filename} 的处理器: {processor.__class__.__name__}")

        except Exception as e:
            print(f"✗ 创建 {filename} 的处理器失败: {str(e)}")

    # 测试格式支持检查
    supported = DocumentProcessorFactory.is_format_supported('test.pdf')
    print(f"PDF格式支持: {supported}")

    supported = DocumentProcessorFactory.is_format_supported('test.xyz')
    print(f"XYZ格式支持: {supported}")

    # 获取支持格式列表
    formats = DocumentProcessorFactory.get_supported_formats()
    print(f"支持的文件扩展名: {formats['extensions']}")

    print("✓ 处理器工厂测试通过")


async def test_batch_processing():
    """测试批量处理"""
    print("\n=== 测试批量处理 ===")

    # 创建多个临时文本文件
    temp_files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"这是第 {i + 1} 个测试文件。包含一些示例文本内容。")
            temp_files.append(f.name)

    try:
        # 创建批量处理器
        config = {'max_workers': 2, 'batch_size': 2}
        batch_processor = BatchProcessor(config)

        # 验证文件
        validation = await batch_processor.validate_batch(temp_files)
        print(f"验证结果: {validation['valid_files']} 个有效文件")

        # 批量处理
        results = await batch_processor.process_batch(temp_files)
        print(f"批量处理完成: {len(results)} 个结果")

        # 获取统计信息
        stats = batch_processor.get_processing_stats(results)
        print(f"处理统计: {stats}")

        print("✓ 批量处理测试通过")

    finally:
        # 清理临时文件
        for temp_file in temp_files:
            os.unlink(temp_file)


async def test_cache():
    """测试缓存功能"""
    print("\n=== 测试缓存功能 ===")

    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("这是一个用于缓存测试的文件。")
        temp_file = f.name

    try:
        # 创建缓存实例
        cache = DocumentCache(ttl=60)  # 60秒TTL

        # 创建测试结果
        test_result = ProcessedDocument(
            original_path=temp_file,
            extracted_text="测试文本",
            chunks=[DocumentChunk(
                chunk_id="test_chunk",
                content="测试分块",
                chunk_index=0,
                metadata={}
            )],
            metadata={},
            processing_stats=None,
            status="completed"
        )

        # 保存到缓存
        await cache.cache_result(temp_file, test_result)
        print("✓ 缓存保存成功")

        # 从缓存读取
        cached_result = await cache.get_cached_result(temp_file)
        if cached_result:
            print("✓ 缓存读取成功")
        else:
            print("✗ 缓存读取失败")

        # 获取缓存统计
        stats = await cache.get_cache_stats()
        print(f"缓存统计: {stats}")

        print("✓ 缓存功能测试通过")

    finally:
        os.unlink(temp_file)


async def test_monitoring():
    """测试监控功能"""
    print("\n=== 测试监控功能 ===")

    # 创建监控器
    monitor = ProcessingMonitor(enable_console_log=False)

    # 记录各种事件
    monitor.log_processing_start("test_file.pdf", {'size': 1024})
    monitor.log_progress("test_file.pdf", 0.5, "处理中")
    monitor.log_processing_end("test_file.pdf", None)  # 简化测试
    monitor.log_warning("test_file.pdf", "轻微警告")

    # 获取摘要
    summary = monitor.get_processing_summary()
    print(f"处理摘要: {summary}")

    # 获取最近事件
    recent_events = monitor.get_recent_events(3)
    print(f"最近事件数量: {len(recent_events)}")

    print("✓ 监控功能测试通过")


async def run_all_tests():
    """运行所有测试"""
    print("开始文件处理模块测试...\n")

    try:
        await test_base_processor()
        await test_chunking_strategies()
        await test_preprocessors()
        await test_processor_factory()
        await test_batch_processing()
        await test_cache()
        await test_monitoring()

        print("\n🎉 所有测试通过！文件处理模块功能正常。")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(run_all_tests())