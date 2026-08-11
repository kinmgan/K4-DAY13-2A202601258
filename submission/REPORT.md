# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: Ngan Tạ
- Repository URL: https://github.com/kinmgan/K4-DAY13-2A202601258
- Commit SHA cuối: 6be96e9
- Thành viên và vai trò:

| STT | Họ tên | MSSV | Vai trò |
|---|---|---|---|
| 1 | Tạ Kim Ngân | 2A202601258 | Langfuse tracing, Prompt versioning, Root cause analysis (CP2 & CP3) |
| 2 | Trương Minh Hoàng | 2A202601262 | Streamlit dashboard, SLO definition & Alerting (CP2 & CP3) |
| 3 | Kim Tuấn Trường | 2A202601842 | Logging, PII redaction, Load testing & Evidence capture (CP1 & CP3) |

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (`evidence/validate-logs-result.txt`; 29 log records, 12 correlation IDs)
- Tổng số traces: 16 traces cho cohort K4 (3 baseline + 2 challenge attempt + 11 khác)
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: `streamlit run scripts/streamlit_dashboard.py` → http://localhost:8501
  + Evidence: `evidence/dashboard-baseline.png`, `evidence/dashboard-incident.png`

## 3. Logging và tracing

- Evidence correlation ID: `evidence/correlation-id-headers.png`
- Evidence PII redaction: `evidence/json-log-redacted.png`
- Evidence trace waterfall: ![Trace chậm nhất](evidence/checkpoint3/trace_slow.png)
- Giải thích một span đáng chú ý:
  - Span `run` (GENERATION) trong trace `18b70603c3fb39fd056edb2c4f859fa3` có metadata `retrieve_context_ms = 2500`, chiếm ~94% tổng 2660ms latency.
  - Span này wrap cả `retrieve_context` + `resolve_prompt` + `llm.generate`.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: `v2` (label `baseline`)
- Version/label candidate: `v3` (label `candidate`)
- Trace ID của mỗi version: db1ba3b45da789db41956b9c2635c3e6 - v2,
d34de24f38996ac8861b89fc384656e8 - v3
- Bằng chứng đổi label hoặc rollback: `evidence/change_label.png`

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: PASS (xem `evidence/validate-dashboard-result.txt`)
- Evidence dashboard:
  - Baseline: `evidence/dashboard-baseline.png`
  - Incident: `evidence/dashboard-incident.png`
- SLO đã chọn và lý do:
  - **Latency P95 ≤ 2000ms** (lấy từ `config/challenge.json::latency_threshold_ms`).
  - Error rate ≤ 2%.
  - Total cost ≤ $2.5 / load test.
  - Quality mean ≥ 0.75.
- Alert rules: `config/alert_rules.yaml` (đã có sẵn).
- Runbook: xem `REPORT.md` mục 6.

## 6. Điều tra challenge

- **Challenge ID**: `day13-k4-observability-v1` (Cohort K4, seed 1304, incident `rag_slow`).
- **Triệu chứng từ metrics**:
  - `/metrics` khi incident BẬT (sau load test concurrency 5): `{"traffic": 6, "latency_p50": 2653, "latency_p95": 2656, "latency_p99": 2656}`
  - `/health` xác nhận: `{"incidents": {"rag_slow": true}}`
  - Load test client thấy latency 5350–13341 ms (do concurrency cao + rag_slow).
- **Trace ID liên quan** (Langfuse, project K4 cohort):

  | Trace ID | Session | retrieve_context_ms |
  |---|---|---|
  | `18b70603c3fb39fd056edb2c4f859fa3` | k4-challenge-s01 | 2500 |
  | `7a43a9818781866f497d3e15c40218e5` | k4-challenge-s02 | 2500 |
  | `f5b3f657f2069367101fed5ee07e3788` | k4-challenge-s03 | 2500 |
  | `2f9dea020e280dfe9506e2050b69b862` | k4-challenge-s04 | 2500 |
  | `3a14f04914428c59957f961586ef291b` | k4-challenge-s05 | 2500 |

  URL: `https://jp.cloud.langfuse.com/project/traces/<id>`

- **Log line / correlation ID liên quan** (5 file JSONL trong `evidence/checkpoint3/log_correlation_*.jsonl`):

  | Correlation ID | File evidence |
  |---|---|
  | `req-2e655792` | `log_correlation_req-2e655792.jsonl` |
  | `req-c7eb0d4a` | `log_correlation_req-c7eb0d4a.jsonl` |
  | `req-f781c63f` | `log_correlation_req-f781c63f.jsonl` |
  | `req-9941321c` | `log_correlation_req-9941321c.jsonl` |
  | `req-b272bd10` | `log_correlation_req-b272bd10.jsonl` |

  Mỗi file chứa 3 dòng: `request_received` → `context_retrieved (latency_ms=2500)` → `response_sent (latency_ms≈2653)`.

- **Root cause**: Hàm `retrieve()` trong `app/mock_rag.py` chèn `time.sleep(2.5)` khi `STATE["rag_slow"] = True`. Span `retrieve_context` chiếm 94% tổng latency, vượt ngưỡng `latency_threshold_ms = 2000` trong `config/challenge.json`. Bằng chứng:
  - `data/logs.jsonl`: 5/5 `context_retrieved` đều có `latency_ms = 2500`.
  - Langfuse trace `metadata.retrieve_context_ms = 2500` cho cả 5 trace.
  - Dòng code vi phạm: `app/mock_rag.py::retrieve` → `if STATE["rag_slow"]: time.sleep(2.5)`.

- **Fix action**:
  ```bash
  python scripts/inject_incident.py --disable
  # hoặc gọi POST /incidents/rag_slow/disable
  ```
  Response: `200 {"ok": true, "incidents": {"rag_slow": false, ...}}`.

  Trong production: cần cache retrieve theo `hash(message)` + đặt `timeout=1.0s` cho retrieve.

- **Verification**: load test lần 2 sau fix:
  - Latency: 1741–1899 ms (giảm ~85% so với 5350–13341 ms).
  - `/metrics`: `{"traffic": 5, "latency_p50": 151, "latency_p95": 790, "latency_p99": 790}`.
  - Log sau fix: `context_retrieved.latency_ms = 0` cho tất cả 5 request (`evidence/checkpoint3/log_after_fix_*.jsonl`).

- **Preventive measures**:
  1. **SLO Alert** khi `latency_p95 > 2000ms` (lấy từ `latency_threshold_ms`).
  2. **Per-span latency panel** trong dashboard — đã có streamlit panel cho `context_retrieved` event sau khi thêm log.
  3. **Auto rollback incident** nếu `rag_slow = True` kéo dài > 5 phút.
  4. **Cache retrieve** theo `hash(message)` (LRU 60s) để chịu được re-request.
  5. **Timeout + circuit breaker** ở tầng retrieve (fail-fast thay vì block cả request).

## 7. Đóng góp cá nhân

| Thành viên | MSSV | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|---|
| Tạ Kim Ngân | 2A202601258 | Langfuse tracing + prompt versioning (CP2); Challenge root cause + fix (CP3); viết `scripts/fetch_langfuse_traces.py`, `scripts/fetch_trace_detail.py`; soạn phần REPORT §3 §6 và phụ lục. | `f35303e` | `@observe` decorator, `langfuse.update_current_span`, prompt label versioning, quy trình metrics→traces→logs khi điều tra incident. |
| Trương Minh Hoàng | 2A202601262 | Streamlit dashboard (`scripts/streamlit_dashboard.py`); SLO definition trong §5; evidence `dashboard-baseline.png` / `dashboard-incident.png`; `validate_dashboard.py` pass. | `94b1cf0` | Streamlit + Pandas quantile aggregation; ánh xạ từ `data/metrics.jsonl` → SLO panel; thiết kế baseline vs incident view. |
| Kim Tuấn Trường | 2A202601842 | Logging + PII redaction (CP1): `app/agent.py` JSON log, `correlation_id` middleware, structlog context binding; hỗ trợ điều tra Challenge (CP3) cùng Ngân — chạy load test `concurrency=5`, capture 5 log correlation file `.jsonl` (`log_correlation_*.jsonl`) cho 5 trace ID. | `525a945` | Structlog context binding, regex PII scrubbing, correlation ID propagation, load test thiết kế với ThreadPoolExecutor. |

## Phụ lục: file evidence

```
evidence/
├── 2 prompt.png                                  # 2 prompt versions trên Langfuse
├── change_label.png                              # Trước/sau khi đổi label
├── correlation-id-headers.png                    # Correlation ID trên response header
├── dashboard-baseline.png                        # Dashboard trước incident
├── dashboard-incident.png                        # Dashboard khi incident
├── json-log-redacted.png                         # Log JSON có PII redaction
├── traces_list.png                               # Danh sách các traces
├── validate-dashboard-result.txt                 # Kết quả validate_dashboard.py
├── validate-logs-result.txt                      # Kết quả validate_logs.py
├── waterfall .png                                # Trace waterfall
└── checkpoint3/
    ├── trace_slow.png                            # Screenshot Langfuse
    ├── trace_slow_f5b3f657f2069367101fed5ee07e3788.png # Screenshot trace chi tiết
    ├── metrics_during_incident.png               # Screenshot metrics khi incident
    ├── log_correlation_req-2e655792.jsonl        # Log lúc có incident
    ├── log_correlation_req-c7eb0d4a.jsonl
    ├── log_correlation_req-f781c63f.jsonl
    ├── log_correlation_req-9941321c.jsonl
    ├── log_correlation_req-b272bd10.jsonl
    ├── log_after_fix_req-10e6253f.jsonl          # Log sau khi fix
    ├── log_after_fix_req-4b5b4d88.jsonl
    ├── log_after_fix_req-04ac4355.jsonl
    ├── log_after_fix_req-1a2ef3b9.jsonl
    └── log_after_fix_req-bf5616b7.jsonl
```

### Ảnh Langfuse cần chụp (1 ảnh)

Chỉ cần **1 ảnh** bất kỳ trong 5 challenge trace, miễn thấy được:

| Ảnh | Trace ID | Session |
|---|---|---|---|
| `trace_slow.png`  | `f5b3f657f2069367101fed5ee07e3788` | k4-challenge-s03 | 

Ảnh chụp phải thấy được các trường:
- `retrieve_context_ms = 2500` ← bằng chứng root cause
- `prompt_name = day13-chat`, `prompt_label = production`, `prompt_version = 3`
- `query_preview` (preview của câu hỏi)
- `doc_count = 1`

