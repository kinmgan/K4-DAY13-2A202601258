"""Quick smoke test for Langfuse tracing.

- Goes through the running app's /chat with the prompt label that is set in
  .env (LANGFUSE_PROMPT_LABEL). No extra labels, no env mutation.
- After each call, looks the resulting Langfuse trace up via the
  x-request-id correlation_id we generated, so we can copy the trace_id
  straight into the submission report when Langfuse is hard to reach.
"""

from __future__ import annotations

import base64
import os
import sys
import uuid
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv()


CHAT_URL = "http://localhost:8000/chat"
PROMPT_LABEL = os.getenv("LANGFUSE_PROMPT_LABEL", "production")
PROMPT_NAME = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")
HOST = (
    os.getenv("LANGFUSE_HOST")
    or os.getenv("LANGFUSE_BASE_URL")
    or "https://cloud.langfuse.com"
)
PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")


def call_chat(client: httpx.Client) -> dict[str, Any]:
    """Send one /chat request and return response + correlation id."""

    correlation_id = f"smoke-{uuid.uuid4().hex[:8]}"
    response = client.post(
        CHAT_URL,
        json={
            "user_id": "u_smoke",
            "session_id": "s_smoke",
            "feature": "summary",
            "message": "Please summarize the observability docs.",
        },
        headers={"x-request-id": correlation_id},
        timeout=30.0,
    )
    response.raise_for_status()
    body = response.json()
    return {
        "correlation_id": correlation_id,
        "answer_preview": body.get("answer", "")[:120],
        "latency_ms": body.get("latency_ms"),
    }


def fetch_trace(session_id: str) -> list[dict[str, Any]] | None:
    """Look up traces filtered by sessionId via the Langfuse public API."""

    if not PUBLIC_KEY or not SECRET_KEY:
        print("Missing LANGFUSE_PUBLIC_KEY/SECRET_KEY; skip remote lookup.")
        return None

    auth = base64.b64encode(f"{PUBLIC_KEY}:{SECRET_KEY}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}

    # Use the documented --session-id filter so we don't depend on flaky
    # client-side matching of opaque trace ids.
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{HOST}/api/public/traces",
            params={"sessionId": session_id, "limit": 5},
            headers=headers,
        )
        if resp.status_code != 200:
            print(f"Langfuse lookup failed: HTTP {resp.status_code} - {resp.text[:200]}")
            return None
        return resp.json().get("data", [])


def main() -> int:
    if not (PUBLIC_KEY and SECRET_KEY):
        print("[warn] Langfuse credentials missing in .env - tracing likely disabled.")

    print(f"prompt_name={PROMPT_NAME!r} label={PROMPT_LABEL!r} host={HOST}")
    print(f"Single test against running app (label from .env = {PROMPT_LABEL!r}).")
    print()

    with httpx.Client() as client:
        result = call_chat(client)
        print(f"-> HTTP 200, correlation_id={result['correlation_id']}")
        print(f"-> answer preview: {result['answer_preview']!r}...")
        print(f"-> latency_ms: {result['latency_ms']}")

    print()
    print("Waiting briefly so Langfuse can flush the trace...")
    import time

    time.sleep(2.0)
    traces = fetch_trace(session_id="s_smoke")
    if traces is None:
        print("No remote trace available (Langfuse unreachable or no creds).")
        return 1
    if not traces:
        print("Trace not visible yet - increase delay or check Langfuse filters.")
        print(f"Used session_id=s_smoke, correlation_id={result['correlation_id']}")
        return 2
    for trace in traces:
        meta = (trace.get("metadata") or {})
        print(
            f"LANGFUSE TRACE_ID={trace.get('id')}  "
            f"ts={trace.get('timestamp')}  "
            f"session={trace.get('sessionId')}"
        )
        print(
            f"  prompt_name={meta.get('prompt_name')!r}  "
            f"label={meta.get('prompt_label')!r}  "
            f"version={meta.get('prompt_version')!r}  "
            f"source={meta.get('prompt_source')!r}"
        )
        print(f"  url: {HOST.rstrip('/')}/project/traces/{trace.get('id')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
