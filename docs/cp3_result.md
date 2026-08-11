(.venv) PS C:\Users\ngant\ai_act_lab\lab_13\K4-DAY13-2A202601258> # Chạy incident chính thức (sẽ dùng config/challenge.json)
>> python scripts/inject_incident.py
200 {'ok': True, 'incidents': {'rag_slow': True, 'tool_fail': False, 'cost_spike': False}}
(.venv) PS C:\Users\ngant\ai_act_lab\lab_13\K4-DAY13-2A202601258> # Chạy với concurrency cao hơn để tạo áp lực>> python scripts/load_test.py --challenge --concurrency 5Challenge: day13-k4-observability-v1 | Cohort: K4[200] req-57bf7c01 | monitoring | 14471.5ms                                          
[200] req-be2b84c7 | monitoring | 14472.7ms
[200] req-f96e68a7 | monitoring | 14474.8ms
[200] req-a3412999 | monitoring | 14471.7ms
[200] req-cc3b5bdf | monitoring | 14474.2ms
(.venv) PS C:\Users\ngant\ai_act_lab\lab_13\K4-DAY13-2A202601258> curl http://127.0.0.1:8000/health


StatusCode        : 200
StatusDescription : OK
Content           : {"ok":true,"tracing_enabled":true,"incidents":{"rag_slow":true," 
                    tool_fail":false,"cost_spike":false}}
RawContent        : HTTP/1.1 200 OK
                    x-request-id: req-21d875c7
                    x-response-time-ms: 0.49
                    Content-Length: 101
                    Content-Type: application/json
                    Date: Tue, 11 Aug 2026 13:45:13 GMT
                    Server: uvicorn

                    {"ok":true,"tracing_...
Forms             : {}
Headers           : {[x-request-id, req-21d875c7], [x-response-time-ms, 0.49],       
                    [Content-Length, 101], [Content-Type, application/json]...}      
Images            : {}InputFields       : {}Links             : {}ParsedHtml        : mshtml.HTMLDocumentClass                                         
RawContentLength  : 101



(.venv) PS C:\Users\ngant\ai_act_lab\lab_13\K4-DAY13-2A202601258> curl http://127.0.0.1:8000/metrics


StatusCode        : 200
StatusDescription : OK
Content           : {"traffic":5,"latency_p50":2651.0,"latency_p95":3276.0,"latency_
                    p99":3276.0,"avg_cost_usd":0.002,"total_cost_usd":0.0099,"tokens 
                    _in_total":494,"tokens_out_total":563,"error_breakdown":{},"qual 
                    ity_avg"...
RawContent        : HTTP/1.1 200 OK
                    x-request-id: req-b4483ea0
                    x-response-time-ms: 0.50
                    Content-Length: 206
                    Content-Type: application/json
                    Date: Tue, 11 Aug 2026 13:45:18 GMT
                    Server: uvicorn

                    {"traffic":5,"latenc...
Forms             : {}
Headers           : {[x-request-id, req-b4483ea0], [x-response-time-ms, 0.50],       
                    [Content-Length, 206], [Content-Type, application/json]...}      
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        : mshtml.HTMLDocumentClass
RawContentLength  : 206
