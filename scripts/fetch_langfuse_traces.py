"""Fetch Langfuse traces by session id for the K4 challenge."""
import os
import base64
import json
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()
host = os.getenv("LANGFUSE_BASE_URL")
pub = os.getenv("LANGFUSE_PUBLIC_KEY")
sec = os.getenv("LANGFUSE_SECRET_KEY")

if not (host and pub and sec):
    print("Missing Langfuse credentials")
    sys.exit(1)

auth = base64.b64encode(f"{pub}:{sec}".encode()).decode()
headers = {"Authorization": f"Basic {auth}"}

sessions = [
    "k4-challenge-s01",
    "k4-challenge-s02",
    "k4-challenge-s03",
    "k4-challenge-s04",
    "k4-challenge-s05",
]

results = {}
with httpx.Client(timeout=20.0) as c:
    for sid in sessions:
        r = c.get(
            f"{host}/api/public/traces",
            params={"sessionId": sid, "limit": 10},
            headers=headers,
        )
        if r.status_code != 200:
            print(f"[{sid}] HTTP {r.status_code}: {r.text[:200]}")
            continue
        traces = r.json().get("data", [])
        print(f"== session {sid}: {len(traces)} traces ==")
        for t in traces:
            meta = t.get("metadata") or {}
            obs = t.get("observations") or []
            print(
                f"  TRACE_ID={t.get('id')}  ts={t.get('timestamp')}  "
                f"corr={meta.get('correlation_id')}  "
                f"prompt={meta.get('prompt_name')}@{meta.get('prompt_version')}({meta.get('prompt_label')})  "
                f"retrieve_ms={meta.get('retrieve_context_ms')}  "
                f"observations={len(obs)}"
            )
            results.setdefault(sid, []).append(
                {
                    "trace_id": t.get("id"),
                    "timestamp": t.get("timestamp"),
                    "correlation_id": meta.get("correlation_id"),
                    "session_id": t.get("sessionId"),
                    "user_id": t.get("userId"),
                    "prompt_name": meta.get("prompt_name"),
                    "prompt_label": meta.get("prompt_label"),
                    "prompt_version": meta.get("prompt_version"),
                    "retrieve_context_ms": meta.get("retrieve_context_ms"),
                    "doc_count": meta.get("doc_count"),
                    "observation_count": len(obs),
                    "url": f"{host.rstrip('/')}/project/traces/{t.get('id')}",
                }
            )

with open("submission/evidence/checkpoint3/langfuse_traces.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nSaved to submission/evidence/checkpoint3/langfuse_traces.json")