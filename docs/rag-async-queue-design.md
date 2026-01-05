# 智能法律助手 - 异步任务队列设计文档

## 概述

异步任务队列是RAG系统的关键基础设施，负责管理文档处理、向量化等耗时任务的异步执行，确保系统的高可用性和可扩展性。本系统采用Celery + Redis架构，支持分布式任务处理和实时状态监控。

## 设计目标

- **高可用性**：支持任务失败重试和容错处理
- **可扩展性**：支持水平扩展，处理大量并发任务
- **实时监控**：提供任务状态跟踪和进度报告
- **优先级调度**：支持不同优先级任务的调度
- **资源管理**：合理分配系统资源，避免过载

## 架构设计

### 系统架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web API层     │    │   任务队列      │    │   工作节点      │
│                 │    │                 │    │                 │
│  FastAPI应用    │───▶│    Redis        │───▶│   Celery Worker │
│                 │    │   (消息代理)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据库        │    │   任务状态      │    │   文件存储      │
│                 │    │                 │    │                 │
│  PostgreSQL     │    │   监控系统      │    │   本地/云存储   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 模块结构

```
backend/app/services/task_queue/
├── __init__.py              # 模块初始化
├── celery_app.py            # Celery应用配置
├── task_definitions.py      # 任务定义
├── task_manager.py          # 任务管理器
├── worker_manager.py        # 工作节点管理
├── monitor.py               # 监控系统
├── scheduler.py             # 调度器
├── exceptions.py            # 异常定义
└── utils.py                 # 工具函数
```

## 核心组件设计

### Celery应用配置

```python
# celery_app.py
from celery import Celery
from ..core.config import settings

class CeleryConfig:
    """Celery配置类"""
    
    # Redis作为消息代理
    broker_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
    result_backend = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"
    
    # 任务序列化
    task_serializer = 'json'
    result_serializer = 'json'
    accept_content = ['json']
    
    # 时区设置
    timezone = 'Asia/Shanghai'
    enable_utc = True
    
    # 任务路由
    task_routes = {
        'task_queue.tasks.process_document': {'queue': 'documents'},
        'task_queue.tasks.generate_embeddings': {'queue': 'embeddings'},
        'task_queue.tasks.cleanup_tasks': {'queue': 'maintenance'},
    }

# 创建Celery应用
celery_app = Celery('legal_assistant')
celery_app.config_from_object(CeleryConfig)

# 自动发现任务
celery_app.autodiscover_tasks(['app.services.task_queue'])
```

### 任务定义

```python
# task_definitions.py
from celery import Task
from ..core.database import async_session_maker
from ..models.document import Document

class BaseTask(Task):
    """基础任务类"""
    
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败回调"""
        # 记录错误日志
        # 更新任务状态
        pass
    
    def on_success(self, retval, task_id, args, kwargs):
        """任务成功回调"""
        # 记录成功日志
        # 更新任务状态
        pass

@celery_app.task(bind=True, base=BaseTask)
async def process_document_task(self, document_id: str):
    """文档处理任务"""
    
    # 更新任务状态为处理中
    await self.update_task_status(document_id, 'processing')
    
    try:
        # 获取文档信息
        async with async_session_maker() as session:
            document = await session.get(Document, document_id)
            
            if not document:
                raise DocumentNotFoundError(f"文档 {document_id} 不存在")
            
            # 调用文档处理器
            from .document_processor import DocumentProcessor
            processor = DocumentProcessor()
            result = await processor.process_document(document.file_path)
            
            # 更新文档状态
            document.status = 'completed'
            document.total_chunks = len(result.chunks)
            document.processed_chunks = len(result.chunks)
            await session.commit()
            
            # 触发向量化任务
            generate_embeddings_task.delay(document_id)
            
            return {
                'document_id': document_id,
                'status': 'completed',
                'chunks_processed': len(result.chunks)
            }
            
    except Exception as e:
        # 更新任务状态为失败
        await self.update_task_status(document_id, 'failed', str(e))
        raise

@celery_app.task(bind=True, base=BaseTask)
async def generate_embeddings_task(self, document_id: str):
    """向量化任务"""
    
    # 实现向量化逻辑
    pass
```

### 任务管理器

```python
# task_manager.py
from celery.result import AsyncResult
from ..core.database import async_session_maker
from ..models.task import Task as TaskModel

class TaskManager:
    """任务管理器"""
    
    def __init__(self, celery_app):
        self.celery_app = celery_app
    
    async def submit_document_processing(self, document_id: str) -> str:
        """提交文档处理任务"""
        
        # 创建任务记录
        async with async_session_maker() as session:
            task = TaskModel(
                type='document_processing',
                payload={'document_id': document_id},
                status='pending'
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
        
        # 提交Celery任务
        celery_task = process_document_task.apply_async(
            args=[document_id],
            task_id=str(task.id)
        )
        
        return str(task.id)
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        
        # 查询数据库中的任务记录
        async with async_session_maker() as session:
            task = await session.get(TaskModel, task_id)
            if not task:
                raise TaskNotFoundError(f"任务 {task_id} 不存在")
            
            # 获取Celery任务状态
            celery_result = AsyncResult(task_id, app=self.celery_app)
            
            return {
                'task_id': task_id,
                'type': task.type,
                'status': task.status,
                'celery_status': celery_result.status,
                'progress': task.progress,
                'result': task.result,
                'error_message': task.error_message,
                'created_at': task.created_at,
                'updated_at': task.updated_at
            }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        
        celery_result = AsyncResult(task_id, app=self.celery_app)
        
        if celery_result.state in ['PENDING', 'RECEIVED']:
            celery_result.revoke(terminate=True)
            
            # 更新任务状态
            async with async_session_maker() as session:
                task = await session.get(TaskModel, task_id)
                if task:
                    task.status = 'cancelled'
                    await session.commit()
                    return True
        
        return False
```

## 任务调度策略

### 优先级调度

```python
# scheduler.py
from enum import Enum

class TaskPriority(Enum):
    """任务优先级"""
    HIGH = 1      # 用户交互相关任务
    MEDIUM = 2    # 批量处理任务
    LOW = 3       # 维护任务

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.queues = {
            'high_priority': [],
            'medium_priority': [],
            'low_priority': []
        }
    
    def schedule_task(self, task_func, args, kwargs, priority: TaskPriority):
        """调度任务"""
        
        task_info = {
            'func': task_func,
            'args': args,
            'kwargs': kwargs,
            'priority': priority,
            'submitted_at': datetime.now()
        }
        
        # 根据优先级放入对应队列
        if priority == TaskPriority.HIGH:
            self.queues['high_priority'].append(task_info)
        elif priority == TaskPriority.MEDIUM:
            self.queues['medium_priority'].append(task_info)
        else:
            self.queues['low_priority'].append(task_info)
    
    def get_next_task(self) -> Optional[Dict]:
        """获取下一个待执行任务"""
        
        # 按优先级顺序检查队列
        for queue_name in ['high_priority', 'medium_priority', 'low_priority']:
            if self.queues[queue_name]:
                return self.queues[queue_name].pop(0)
        
        return None
```

### 资源管理

```python
# resource_manager.py
import psutil

class ResourceManager:
    """资源管理器"""
    
    def __init__(self, max_memory_usage: float = 0.8, max_cpu_usage: float = 0.8):
        self.max_memory_usage = max_memory_usage
        self.max_cpu_usage = max_cpu_usage
    
    def can_accept_new_task(self) -> bool:
        """检查是否可以接受新任务"""
        
        memory_usage = psutil.virtual_memory().percent / 100
        cpu_usage = psutil.cpu_percent(interval=1) / 100
        
        return (memory_usage < self.max_memory_usage and 
                cpu_usage < self.max_cpu_usage)
    
    def get_system_metrics(self) -> Dict[str, float]:
        """获取系统指标"""
        
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        return {
            'memory_used_percent': memory.percent,
            'memory_used_gb': memory.used / (1024**3),
            'cpu_used_percent': cpu,
            'disk_used_percent': disk.percent,
            'active_tasks': self.get_active_task_count()
        }
```

## 监控系统

### 任务监控

```python
# monitor.py
from prometheus_client import Counter, Gauge, Histogram

class TaskMonitor:
    """任务监控器"""
    
    # Prometheus指标
    tasks_submitted = Counter('tasks_submitted_total', 
                             'Total tasks submitted', ['type'])
    tasks_completed = Counter('tasks_completed_total', 
                             'Total tasks completed', ['type', 'status'])
    task_duration = Histogram('task_duration_seconds', 
                             'Task duration in seconds', ['type'])
    active_tasks = Gauge('active_tasks', 'Number of active tasks')
    
    def __init__(self):
        self.active_tasks_count = 0
    
    def task_started(self, task_type: str):
        """任务开始"""
        self.active_tasks_count += 1
        self.active_tasks.set(self.active_tasks_count)
        self.tasks_submitted.labels(type=task_type).inc()
    
    def task_completed(self, task_type: str, status: str, duration: float):
        """任务完成"""
        self.active_tasks_count -= 1
        self.active_tasks.set(self.active_tasks_count)
        self.tasks_completed.labels(type=task_type, status=status).inc()
        self.task_duration.labels(type=task_type).observe(duration)
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        
        return {
            'active_tasks': self.active_tasks_count,
            'total_submitted': self._get_total_submitted(),
            'total_completed': self._get_total_completed(),
            'success_rate': self._calculate_success_rate()
        }
```

### 实时状态跟踪

```python
# status_tracker.py
class TaskStatusTracker:
    """任务状态跟踪器"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def update_task_progress(self, task_id: str, progress: float, 
                                 message: str = None):
        """更新任务进度"""
        
        status_data = {
            'progress': progress,
            'message': message,
            'updated_at': datetime.now().isoformat()
        }
        
        await self.redis.hset(
            f'task_status:{task_id}',
            mapping=status_data
        )
        await self.redis.expire(f'task_status:{task_id}', 3600)  # 1小时过期
    
    async def get_task_progress(self, task_id: str) -> Optional[Dict]:
        """获取任务进度"""
        
        status_data = await self.redis.hgetall(f'task_status:{task_id}')
        if status_data:
            return {
                'progress': float(status_data.get('progress', 0)),
                'message': status_data.get('message'),
                'updated_at': status_data.get('updated_at')
            }
        
        return None
```

## 错误处理和重试机制

### 重试策略

```python
# retry_policy.py
from celery import Task
from tenacity import retry, stop_after_attempt, wait_exponential

class RetryPolicy:
    """重试策略"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def execute_with_retry(self, func, *args, **kwargs):
        """带重试的执行"""
        return await func(*args, **kwargs)

class DocumentProcessingTask(BaseTask):
    """文档处理任务（带重试）"""
    
    max_retries = 3
    default_retry_delay = 60  # 60秒
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """重试回调"""
        # 记录重试日志
        pass
```

### 死信队列

```python
# dead_letter_queue.py
class DeadLetterQueue:
    """死信队列管理器"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.dlq_key = 'dead_letter_queue'
    
    async def add_failed_task(self, task_info: Dict):
        """添加失败任务到死信队列"""
        
        task_info['failed_at'] = datetime.now().isoformat()
        
        await self.redis.lpush(
            self.dlq_key,
            json.dumps(task_info)
        )
    
    async def get_failed_tasks(self, count: int = 10) -> List[Dict]:
        """获取失败任务列表"""
        
        tasks = await self.redis.lrange(self.dlq_key, 0, count - 1)
        return [json.loads(task) for task in tasks]
```

## 数据库设计

### 任务表扩展

```sql
-- 扩展任务表（在现有表基础上）
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS progress FLOAT DEFAULT 0.0;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 2;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS celery_task_id VARCHAR(255);

-- 创建任务统计视图
CREATE VIEW task_statistics AS
SELECT 
    type,
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_duration
FROM tasks 
GROUP BY type, status;
```

## 部署配置

### Docker配置

```yaml
# docker-compose.yml 新增服务
version: '3.8'
services:
  # Redis服务
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Celery Worker
  celery-worker:
    build: ./backend
    command: celery -A app.services.task_queue.celery_app worker --loglevel=info
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
    deploy:
      replicas: 2

  # Celery Beat（定时任务）
  celery-beat:
    build: ./backend
    command: celery -A app.services.task_queue.celery_app beat --loglevel=info
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis

volumes:
  redis_data:
```

### 环境配置

```python
# 环境变量配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_WORKER_CONCURRENCY=4
CELERY_TASK_TIME_LIMIT=300  # 5分钟
```

## 测试策略

### 单元测试

```python
class TestTaskQueue:
    """任务队列测试"""
    
    def test_task_submission(self):
        """测试任务提交"""
        pass
    
    def test_task_status_tracking(self):
        """测试任务状态跟踪"""
        pass
    
    def test_retry_mechanism(self):
        """测试重试机制"""
        pass
    
    def test_resource_management(self):
        """测试资源管理"""
        pass
```

### 集成测试

```python
class IntegrationTest:
    """集成测试"""
    
    def test_end_to_end_processing(self):
        """测试端到端文档处理流程"""
        pass
    
    def test_concurrent_processing(self):
        """测试并发处理"""
        pass
```

## 总结

异步任务队列系统为智能法律助手提供了强大的任务处理能力：

1. **提高系统响应性**：通过异步处理避免阻塞用户请求
2. **增强系统可靠性**：通过重试机制和错误处理确保任务完成
3. **支持水平扩展**：通过分布式架构支持系统扩展
4. **提供监控能力**：通过详细指标支持系统运维

该设计为RAG系统的稳定运行提供了坚实的技术基础。