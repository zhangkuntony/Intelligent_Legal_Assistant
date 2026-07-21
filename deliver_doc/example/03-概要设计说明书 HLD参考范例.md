

* * *

《人工智能大模型数据训练系统概要设计说明书（HLD）》
===========================

A. 架构对齐与约束落地（12 分）
------------------

* **架构总览图（文字化描述）**
  
      数据源 → 数据采集器(Loader) → 清洗器(Cleaner) → 切块器(Chunker) 
             → 向量索引(Indexer, FAISS) → 检索器(Retriever, Top-k/BM25混检) 
             → 提示词生成器(Promptor) → 大模型/MockLLM(LLM Engine) 
             → 解析与合成(Parser & Synthesizer) → 指标校验(Guardrail) 
             → CLI/HTTP 接口 → 可视化/考评模块(Evaluator)

* **架构约束声明**：
  
  * 🔒 系统需 **离线运行、仅 CPU/GPU，本地索引、不可联网、不可微调**。
  
  * 支持 MockLLM 替代真实模型，用于测试与演示。

* **能力→章节映射**：
  
  * 数据采集 → B.1 Loader
  
  * 模型训练 → B.3 Training Manager
  
  * 考评与校验 → D.2 守护链时序
  
  * 输出与接口 → B.7 Synthesizer & G 部署

* * *

B. 模块分解与接口设计（20 分）
------------------

* **模块职责表（部分示例）**

| 模块          | 接口函数                            | 输入              | 输出           | 配置键                 | 异常        |
| ----------- | ------------------------------- | --------------- | ------------ | ------------------- | --------- |
| Loader      | `load_data(path)`               | 文件路径            | Document[]   | `data_path`         | 文件不存在     |
| Cleaner     | `clean(doc)`                    | Document        | Document     | `clean_rules`       | 格式异常      |
| Chunker     | `split(doc, size, overlap)`     | 文本              | 块集合          | `chunk_size`        | 超长文本      |
| Indexer     | `build_or_load(path)`           | 文本块             | 索引对象         | `vector_store_path` | 索引损坏      |
| Retriever   | `retrieve(q,k,use_bm25)`        | query,k         | 文档列表         | `top_k,use_bm25`    | 空结果       |
| Promptor    | `build_prompt(q,docs)`          | query,docs      | prompt       | `max_chars`         | 超长裁剪      |
| LLM         | `invoke(prompt)`                | prompt          | raw_str/json | `use_mock`          | 超时/解析失败   |
| Synthesizer | `parse_and_normalize(raw,docs)` | raw,docs        | JSON payload | —                   | JSON 失败回退 |
| Guardrail   | `validate(payload,metrics)`     | payload,metrics | 修正后payload   | `tolerance`         | 指标不一致     |

* **统一输出字段**：
  
      {
        "answer": "...",
        "citations": ["dataset:v1"],
        "used_metrics": ["net_profit"],
        "confidence": 0.82,
        "notes": "一致性校验通过"
      }
  
  

* * *

C. 数据/元数据与文件规范（10 分）
--------------------

* **数据清单与目录**：
  
      /data/raw/        原始数据
      /data/clean/      清洗后数据
      /data/train/      训练集
      /data/test/       测试集
      /metrics/         官方指标文件

* **字段字典**（示例）：
  
  | 字段         | 类型    | 单位  | 说明   |
  | ---------- | ----- | --- | ---- |
  | revenue    | float | 亿元  | 营业收入 |
  | net_profit | float | 亿元  | 净利润  |
  | eps        | float | 元/股 | 每股收益 |

* **元数据字段**：`company, year, page, section, source`

* * *

D. 两条关键时序流（12 分）
----------------

1. **QA 链时序**：
   
   * 输入 query → Retriever 检索 Top-k → Promptor 构建 prompt → LLM 返回结果 → Parser 转 JSON → Synthesizer 生成 payload → 若失败 → fallback 策略。

2. **评测/守护链时序**：
   
   * Answer payload → Guardrail 数字抽取 → 与 `key_metrics.csv` 对比 → 容差 ±5% → notes/信心度调整 → 返回最终 JSON。

* * *

E. 关键设计决策与权衡（10 分）
------------------

* **索引方案**：采用 FAISS 本地向量索引（离线可靠、性能优先），并可选 BM25 混检增强鲁棒性。

* **Prompt 策略**：上下文拼接，限制 1800 字符；自动裁剪。

* **输出置信度**：启发式 confidence + Guardrail 调整。

* **MockLLM**：便于测试，真实部署可替换为 Qwen/Llama2 等。

* * *

F. 异常处理、降级与鲁棒性（10 分）
--------------------

* **JSON 解析失败** → 回退文本回答 + 默认引用。

* **检索无结果** → 返回兜底提示。

* **指标超出容差** → notes 标注 mismatch，confidence 下调。

* **索引损坏** → 触发重建，日志报警。

* * *

G. 运行形态与配置/部署视图（8 分）
--------------------

* **运行形态**：支持 CLI 或 HTTP 接口。

* **配置中心**：`.env` 文件定义关键参数：
  
      DATA_PATH=/data/raw
      VECTOR_STORE_PATH=/index/faiss
      TOP_K=5
      USE_BM25=True
      USE_MOCK=True

* **部署视图**：
  
  * 单机 CPU/GPU 集群；
  
  * Docker 容器化可选；
  
  * 依赖：Python3.10、FAISS、PyTorch。

* * *

H. 观测性（6 分）
-----------

* **日志点**：
  
  * 数据加载量、chunk 数、索引复用/重建
  
  * 检索返回条数、prompt 长度
  
  * JSON 解析失败、Guardrail 校验结果

* **证据定位**：日志文件存储 `/logs/`，命名规则 `module_YYYYMMDD.log`。

* * *

I. 合规与安全（4 分）
-------------

* **离线运行、不可联网、不可微调**：通过网络封禁策略与本地模型执行保证。

* **第三方依赖声明**：PyTorch、FAISS、LangChain，仅用于内部训练。

* * *

J. 需求/用例追踪与一致性（4 分）
-------------------

* **追踪表（示例）**

| 能力   | SRS-FR/NFR | HLD 模块           | 用例编号         |
| ---- | ---------- | ---------------- | ------------ |
| 数据采集 | FR-01      | Loader           | TC-Data-001  |
| 数据清洗 | FR-02      | Cleaner          | TC-Clean-002 |
| 模型训练 | FR-03      | Training Manager | TC-Train-005 |
| 指标校验 | FR-09      | Guardrail        | TC-Check-011 |

* * *

K. 图文质量与可读性（4 分）
----------------

* 图表统一编号（例如图 1 架构总览图、图 2 QA 链时序图、图 3 守护链时序图）。

* 附录术语表：
  
  * **LLM**：大语言模型
  
  * **FAISS**：Facebook AI 相似度搜索库
  
  * **Guardrail**：指标一致性校验模块
  
  * **MockLLM**：模拟 LLM，用于测试

* * *


