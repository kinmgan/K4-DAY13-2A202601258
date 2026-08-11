# Checkpoint 3 — Challenge chính thức: Kế hoạch thực hiện

## Mục tiêu
Điều tra incident `rag_slow` (RAG system chậm) bằng luồng **Metrics → Traces → Logs → Root Cause → Fix → Prevention**

---

## PHASE 1: Chuẩn bị & Chạy Incident (5-10 phút)

### Step 1.1: Kích hoạt Incident Challenge

```bash
# Chạy incident chính thức (sẽ dùng config/challenge.json)
python scripts/inject_incident.py
```

### Step 1.2: Chạy Load Test với Challenge Mode

```bash
# Chạy với concurrency cao hơn để tạo áp lực
python scripts/load_test.py --challenge --concurrency 5
```

### Step 1.3: Thu thập Baseline Metrics

```bash
# Kiểm tra health endpoint
curl http://127.0.0.1:8000/health

# Xem metrics hiện tại
curl http://127.0.0.1:8000/metrics
```

---

## PHASE 2: Phân tích Triệu chứng từ Metrics (10-15 phút)

### Step 2.1: Xác định Triệu chứng qua Dashboard

| Triệu chứng | Dashboard Indicator | Threshold |
|-------------|---------------------|-----------|
| **Latency cao** | P95/P99 latency > 2000ms | 2000ms |
| **Traffic bất thường** | Request count tăng đột ngột | - |
| **Error rate** | Error rate > 0% | 0% |

### Step 2.2: Ghi nhận Evidence từ Metrics

```markdown
Evidence cần thu thập:
- [ ] Trace ID của request chậm (P95/P99)
- [ ] Giá trị latency cụ thể (ms)
- [ ] Thời điểm xảy ra (timestamp)
- [ ] Dashboard screenshot
```

---

## PHASE 3: Khoanh vùng Span bất thường qua Trace (15-20 phút)

### Step 3.1: Mở Langfuse Dashboard

```
1. Truy cập Langfuse project
2. Tìm traces trong khoảng thời gian incident
3. Filter theo session_id: k4-challenge-s01, s02, s03, s04, s05
```

### Step 3.2: Phân tích Trace Tree

Tìm các span bất thường trong trace:

```
┌─────────────────────────────────────────────────────────┐
│ root (total time)                                       │
│ ├─ parse_input (fast)                                   │
│ ├─ retrieve_context (SLOW ⚠️)  ← Tìm ở đây             │
│ ├─ generate_response (medium)                           │
│ └─ format_output (fast)                                 │
└─────────────────────────────────────────────────────────┘
```

### Step 3.3: Ghi nhận Trace Evidence

```markdown
Evidence từ Trace:
- [ ] Trace ID: <dán trace ID cụ thể>
- [ ] Span bất thường: <tên span>
- [ ] Thời gian span: <ms>
- [ ] So sánh với span bình thường: <ms>
```

---

## PHASE 4: Chứng minh Root Cause bằng Logs (15-20 phút)

### Step 4.1: Tìm Log theo Correlation ID

```bash
# Đọc logs.jsonl và tìm theo correlation ID từ trace
# Format: grep với correlation_id
```

### Step 4.2: Phân tích Log Pattern

```
Log sequence mong đợi cho request bình thường:
1. request_received (correlation_id: xxx)
2. context_retrieved (items: N, time_ms: ~50ms)
3. response_sent (latency_ms: ~200ms)

Log sequence cho rag_slow incident:
1. request_received (correlation_id: xxx)
2. context_retrieved (items: N, time_ms: ~2000ms) ← CHẬM!
3. response_sent (latency_ms: ~2100ms)
```

### Step 4.3: Root Cause Hypothesis

Dựa trên incident name `rag_slow`, root cause thường là:

| Possible Root Cause | Log Evidence cần tìm |
|---------------------|----------------------|
| Vector search chậm | `context_retrieved` có `time_ms` cao bất thường |
| Network latency | So sánh `retrieve_start` vs `retrieve_end` |
| Token limit exceeded | Log có warning về token count |
| Cache miss | Log có `cache_hit: false` |

---

## PHASE 5: Đề xuất Fix & Preventive Measures (10-15 phút)

### Step 5.1: Immediate Fix

```markdown
## Fix ngay lập tức

### Root Cause: [Xác định từ Step 4]

### Fix:
1. [Mô tả fix cụ thể]
2. [Command để apply fix]
3. [Verification: chạy lại load test để confirm]

### Evidence:
- [ ] Log sau fix: <so sánh latency trước/sau>
- [ ] Trace sau fix: <trace ID mới>
```

### Step 5.2: Preventive Measures

```markdown
## Biện pháp phòng ngừa

| Measure | Implementation | Monitoring |
|---------|----------------|------------|
| SLO Alert | Alert khi P95 > 2000ms | Dashboard |
| Rate Limiting | Limit concurrent RAG requests | Metrics |
| Circuit Breaker | Stop cascading failures | Code change |
| Caching | Cache frequent queries | Cache hit rate |
```

---

## Evidence Checklist

```
submission/evidence/
├── checkpoint3/
│   ├── metrics_baseline.png          # Dashboard trước incident
│   ├── metrics_during_incident.png    # Dashboard khi incident xảy ra
│   ├── trace_slow_[id].png           # Trace với span bất thường
│   ├── log_correlation_[id].jsonl     # Log lines liên quan
│   ├── dashboard_after_fix.png         # Dashboard sau fix
│   └── REPORT.md                      # Báo cáo đầy đủ
```

---

## Luồng thực thi tổng hợp

```
┌─────────────────────────────────────────────────────────────────┐
│  1. RUN INCIDENT                                                │
│     python scripts/inject_incident.py                            │
│     python scripts/load_test.py --challenge --concurrency 5     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. METRICS ANALYSIS                                            │
│     - Dashboard P95/P99 > 2000ms?                               │
│     - Error rate tăng?                                         │
│     - Save: metrics_during_incident.png                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. TRACE INVESTIGATION                                         │
│     - Mở Langfuse → Traces                                     │
│     - Filter: session_id IN (s01-s05)                          │
│     - Tìm span với thời gian bất thường                        │
│     - Save: trace_slow_[id].png                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. LOG ANALYSIS                                                │
│     - grep correlation_id từ trace                             │
│     - Tìm log line chứng minh root cause                       │
│     - Save: log_correlation_[id].jsonl                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. FIX & VERIFY                                               │
│     - Apply fix                                                 │
│     - Chạy lại load test                                       │
│     - Verify P95 < 2000ms                                       │
│     - Save: dashboard_after_fix.png                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tiêu chí đánh giá Checkpoint 3

| Tiêu chí | Evidence cần có |
|----------|------------------|
| Chạy incident thành công | Log hoặc output xác nhận incident active |
| Xác định triệu chứng | Dashboard screenshot với metric cụ thể |
| Khoanh vùng span | Trace ID + span name + thời gian |
| Chứng minh root cause | Log line với correlation ID |
| Đề xuất fix | Mô tả fix cụ thể |
| Biện pháp phòng ngừa | Ít nhất 2 preventive measures |

---

## Commands Reference

```bash
# 1. Chạy incident
python scripts/inject_incident.py

# 2. Load test challenge
python scripts/load_test.py --challenge --concurrency 5

# 3. Kiểm tra API
curl http://127.0.0.1:8000/health

# 4. Validate logs
python scripts/validate_logs.py

# 5. Validate dashboard
python scripts/validate_dashboard.py

# 6. Tắt incident
python scripts/inject_incident.py --scenario rag_slow --disable
```
