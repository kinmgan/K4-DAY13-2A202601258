import httpx
import asyncio
import os

async def main():
    url = "http://localhost:8000/chat"
    
    # 1. Gọi API với v1 (production)
    print("--- Đang gọi API với v1 (production) ---")
    os.environ["LANGFUSE_PROMPT_LABEL"] = "production"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "user_id": "u_test_1",
            "session_id": "s_test_1",
            "feature": "summary",
            "message": "Please summarize the observability docs."
        }, timeout=30.0)
        if response.status_code == 200:
            print("Response:", response.json().get("answer", "")[:100], "...")
        else:
            print("Error:", response.text)
            
    # 2. Gọi API với v2 (candidate)
    print("\n--- Đang gọi API với v2 (candidate) ---")
    os.environ["LANGFUSE_PROMPT_LABEL"] = "candidate"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "user_id": "u_test_2",
            "session_id": "s_test_2",
            "feature": "summary",
            "message": "Please summarize the observability docs."
        }, timeout=30.0)
        if response.status_code == 200:
            print("Response:", response.json().get("answer", "")[:100], "...")
        else:
            print("Error:", response.text)

if __name__ == "__main__":
    asyncio.run(main())
