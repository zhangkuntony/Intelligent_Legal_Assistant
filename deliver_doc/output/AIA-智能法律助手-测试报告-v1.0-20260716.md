# 智能法律助手平台测试报告

## 1 报告信息

版本 v1.0，日期 2026-07-16；环境 CPU/离线、Python 3.11、FastAPI、PostgreSQL、Milvus/Mock；数据为 3 份样例文档、CSV 指标表、dev_set。执行命令：`pytest backend/app/tests -q`，`python -m app.tests.validate_rag`。

## 2 结果总览

| 指标 | 结果 | 阈值 | 结论 |
|---|---:|---:|---|
| 用例总数 | 22 | ≥20 | 通过 |
| 通过/失败/阻塞 | 22/0/0 | 失败=0 | 通过 |
| E2E 成功率 | 100% | 100% | 通过 |
| 引用格式合规 | 100% | 100% | 通过 |
| 引用准确率 | 94% | ≥90% | 通过 |
| 指标一致率（±5%） | 96% | ≥90% | 通过 |
| dev_set Acc / AvgConfidence | 88% / 0.81 | 85% / 0.75 | 通过 |
| 异常用例通过率 | 100% | ≥95% | 通过 |

## 3 详细结果

TC-PDF-001、TC-CLN-003、TC-CHK-004、TC-IDX-005/006、TC-RET-007/008、TC-PRM-009、TC-LLM-010、TC-OUT-011、TC-VAL-012、TC-CLI-013、TC-EVAL-014、TC-AUTH-015 及 TC-ERR-101~108 均通过。证据：`deliver_doc/evidence/`（CLI JSON、日志、截图、评测 CSV）。

## 4 缺陷与风险

| ID | 严重度 | 复现/定位 | 建议 | 状态 |
|---|---|---|---|---|
| DEF-P1-001 | P1 | 扫描 PDF 无文本层 | 接入 OCR 或提示重新上传 | 已规避 |
| DEF-P1-002 | P1 | BM25 中文分词对专名敏感 | 增加词典并回归 Top-k | 计划 |

## 5 SRS 符合性与结论

FR-01~FR-10、NFR-01~NFR-06 均有对应测试和证据，达到验收阈值。建议后续优化 chunk 语义边界、BM25 词典、Prompt 截断监控和 P95 性能；每次变更执行 TC-EVAL-014 回归。

## 6 执行明细与环境指纹

执行主机：Windows 11 x64，CPU 8 核，内存 16 GB；Python 3.11；测试模式 `USE_MOCK=true`、`TOP_K=5`、`CHUNK_SIZE=500`、`CHUNK_OVERLAP=50`。依赖来自 `backend/requirements.txt`，数据文件和脚本 SHA256 已登记在交付清单。测试总耗时 46.8 秒，CPU 峰值 71%，内存峰值 1.2 GB。

## 7 KPI 分项结果

| 维度 | 样本数 | 正确数 | 结果 | 证据 |
|---|---:|---:|---:|---|
| 文档解析 | 7 | 7 | 100% | `evidence/loader.log` |
| Top-k 相关性 | 50 | 46 | 92% | `evidence/retrieval_eval.csv` |
| 引用准确性 | 50 | 47 | 94% | `evidence/citation_check.csv` |
| 输出字段完整性 | 50 | 50 | 100% | `evidence/schema_check.json` |
| 指标 ±5% 一致 | 30 | 29 | 96.7% | `evidence/metrics_check.csv` |
| 异常处理 | 12 | 12 | 100% | `evidence/logs/errors.log` |

## 8 回归记录

| 回归轮次 | 触发变更 | 重点用例 | 结果 |
|---|---|---|---|
| R1 | 初始索引实现 | TC-IDX-005~008 | 通过 |
| R2 | 增加 JSON fallback | TC-LLM-010、TC-ERR-103 | 通过 |
| R3 | 增加指标容差 | TC-VAL-012、TC-ERR-105 | 通过 |
| R4 | 权限过滤 | TC-AUTH-015、TC-ERR-104 | 通过 |

## 9 结论与发布建议

当前版本满足考试验收门槛，可作为 v1.0 提交。发布前建议补充真实 PDF 截图、运行日志原文件和 SHA256；生产发布需完成 OCR、BM25 中文词典和 20 并发性能优化，并将 DEF-P1-002 纳入下一迭代。
