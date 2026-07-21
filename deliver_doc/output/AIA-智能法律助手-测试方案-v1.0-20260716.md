# 智能法律助手平台测试方案（含用例）

## 1 目标、范围与环境

目标：验证 SRS FR-01~FR-10、NFR-01~NFR-06，覆盖单元、组件、集成、E2E 和回归。环境：Windows/Linux、Python 3.9+、CPU、离线；后端 FastAPI，数据库 PostgreSQL，向量 Milvus 或 Mock，样例 PDF 3 份、`key_metrics.csv`、`dev_set.jsonl`。初始化：复制 `.env.example`，设置 `USE_MOCK=true`、`TOP_K=5`，安装 `backend/requirements.txt`，运行 `pytest backend/app/tests`。

## 2 策略与通过准则

单元覆盖 Loader/Cleaner/Chunker/Validator；组件覆盖索引、检索、Prompt；集成覆盖 RAG 链；E2E 覆盖登录→上传→问答→引用。正向、反向、边界和回归均纳入。通过标准：E2E=100%，字段完整率=100%，引用准确率≥90%，指标一致率≥90%（±5%），dev_set Acc≥85%、AvgConfidence≥0.75，异常通过率≥95%。

## 3 用例

| ID | 关联 | 场景/步骤 | 预期 |
|---|---|---|---|
| TC-PDF-001 | FR-01 | 加载 3 个 PDF，检查 page/source | Document 字段完整 |
| TC-DOC-002 | FR-01 | 上传 DOCX/TXT | 状态 completed，生成 chunks |
| TC-CLN-003 | FR-02 | 输入页眉、断词、异常空格 | 清洗规则生效 |
| TC-CHK-004 | FR-03 | chunk_size=500、overlap=50 | 块含 section/chunk_id |
| TC-IDX-005 | FR-04 | 删除索引后 build | 文件生成且可查询 |
| TC-IDX-006 | FR-04 | 重启后 load_local | 日志显示复用 |
| TC-RET-007 | FR-05 | query，Top-k=5 | 返回≤5条证据 |
| TC-RET-008 | FR-05 | 开关 BM25，对比去重 | 无重复，召回不下降 |
| TC-PRM-009 | FR-06 | 构造含 5 条 context 的 prompt | 仅使用 CONTEXT，引用格式正确 |
| TC-LLM-010 | FR-07 | Mock 返回 JSON/坏 JSON | 正常解析或 fallback |
| TC-OUT-011 | FR-09 | 执行问答 | 字段齐全、citations 非空 |
| TC-VAL-012 | FR-08 | CSV 偏差 3%/8% | 前者通过，后者降 confidence 并 notes |
| TC-CLI-013 | FR-10 | 调用 API/CLI | 2xx JSON，错误码规范 |
| TC-EVAL-014 | NFR-04 | 批量执行 dev_set | 输出 Total/Correct/Acc/AvgConf |
| TC-AUTH-015 | NFR-06 | 无 token/越权访问 | 401/403，数据隔离 |
| TC-ERR-101 | NFR-02 | 删除 CSV 必填列 | 422，列名清晰 |
| TC-ERR-102 | NFR-02 | 无关问题空检索 | 不崩溃，引用为空并提示 |
| TC-ERR-103 | NFR-02 | LLM 半截 JSON | fallback JSON，notes 保留 |
| TC-ERR-104 | NFR-02 | 删除引用 | 不得返回无引用成功 |
| TC-ERR-105 | FR-08 | 偏差>5% | mismatch notes、confidence下降 |
| TC-ERR-106 | FR-04 | 破坏索引文件 | 自动重建或明确报错 |
| TC-ERR-107 | FR-05 | 不存在公司/年份 | 返回未找到来源 |
| TC-ERR-108 | NFR-04 | 超长上下文 | 裁剪后仍为合法 JSON |

## 4 数据与证据

每条用例保存 `evidence/<case_id>.json`、`evidence/logs/<case_id>.log`；截图位于 `evidence/screenshots/`。格式校验脚本检查 `answer,citations,used_metrics,confidence` 和引用正则；评测脚本批量读取 `dev_set.jsonl` 输出 `evidence/eval_summary.csv`。

## 6 测试数据设计

| 数据集 | 数量 | 构成 | 用途 |
|---|---:|---|---|
| PDF 基线 | 3 | 可复制文本、表格、分页脚注 | 解析/引用 |
| DOC/DOCX/TXT | 各 2 | 中文条款、英文条款、空段落 | 格式兼容 |
| CSV 指标 | 30 行 | 5 公司×6 年，含缺失和异常值 | 指标校验 |
| dev_set | 50 条 | 事实、比较、无关、拒答问题 | 批量评测 |
| 异常集 | 12 条 | 坏文件、坏索引、缺列、超长输入 | 鲁棒性 |

数据生成规则：所有金额统一亿元、比率统一百分比、EPS 统一元/股；年份为 4 位整数；敏感数据使用脱敏公司名。每次执行记录文件大小、行数、SHA256，避免测试数据漂移。

## 7 覆盖率矩阵

| 能力 | 单元 | 组件 | 集成 | E2E | 用例 |
|---|---|---|---|---|---|
| Loader | Y | Y | Y | Y | 001/002 |
| Cleaner/Chunker | Y | Y | Y | Y | 003/004 |
| Indexer/Retriever | Y | Y | Y | Y | 005~008 |
| Prompt/LLM/Parser | Y | Y | Y | Y | 009/010/011 |
| Validator | Y | Y | Y | Y | 012 |
| API/Auth | Y | Y | Y | Y | 013/015 |
| NFR 异常 | - | Y | Y | Y | 101~108 |

## 8 自动化执行与退出码

```bash
python -m pytest backend/app/tests -q --junitxml=evidence/junit.xml
python -m app.tests.validate_rag --dataset data/eval/dev_set.jsonl --output evidence/eval_summary.csv
python scripts/check_output_schema.py evidence/cli/*.json
```

脚本退出码：0=全部通过；1=功能失败；2=环境或数据缺失；3=指标低于阈值。CI 必须上传 JUnit、日志、JSON、CSV 四类制品。

## 9 性能与安全测试

性能测试使用 1/5/20 并发、100 次问答，记录平均/P50/P95/P99 延迟、CPU 峰值和内存峰值；P95 超过 10 秒判失败。安全测试包含未认证访问、越权文档、路径穿越、超大文件、恶意扩展名、Prompt 注入；任何越权成功均为 P0。

## 5 风险与回归

PDF 扫描件、Milvus 不可用、模型输出漂移、上下文截断为 P0/P1 风险；修复后至少执行关联用例和全量 TC-EVAL-014。每次版本记录缺陷 ID、复现命令、日志片段、回归轮次。
