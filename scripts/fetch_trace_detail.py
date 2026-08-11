"""Fetch one Langfuse trace detail with observations."""
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

auth = base64.b64encode(f"{pub}:{sec}".encode()).decode()
headers = {"Authorization": f"Basic {auth}"}

trace_id = sys.argv[1] if len(sys.argv) > 1 else "18b70603c3fb39fd056edb2c4f859fa3"

with httpx.Client(timeout=20.0) as c:
    r = c.get(f"{host}/api/public/traces/{trace_id}", headers=headers)
    if r.status_code != 200:
        print(f"HTTP {r.status_code}: {r.text[:300]}")
        sys.exit(1)
    trace = r.json()
    r2 = c.get(
        f"{host}/api/public/observations",
        params={"traceId": trace_id, "limit": 50},
        headers=headers,
    )
    obs = r2.json().get("data", []) if r2.status_code == 200 else []

print("=== TRACE ===")
print(json.dumps(trace, ensure_ascii=False, indent=2)[:2000])
print("\n=== OBSERVATIONS ===")
for o in obs:
    print(f"- type={o.get('type')}  name={o.get('name')}  start={o.get('startTime')}  end={o.get('endTime')}")
    meta = o.get("metadata") or {}
    for k in ("retrieve_context_ms", "doc_count", "prompt_name", "prompt_label", "prompt_version"):
        if k in meta:
            print(f"    {k} = {meta[k]}")

with open(f"submission/evidence/checkpoint3/trace_detail_{trace_id[:8]}.json", "w", encoding="utf-8") as f:
    json.dump({"trace": trace, "observations": obs}, f, ensure_ascii=False, indent=2)
print(f"\nSaved to submission/evidence/checkpoint3/trace_detail_{trace_id[:8]}.json")