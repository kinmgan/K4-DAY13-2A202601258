import os
from langfuse import Langfuse
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

# Khởi tạo client Langfuse
client = Langfuse(
    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
    host=os.environ.get("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
)

def create_prompts():
    print("Creating Version 1 (v1)...")
    prompt_v1 = client.create_prompt(
        name="day13-chat",
        type="text",
        prompt=(
            "You are a helpful AI assistant assisting with {{feature}}.\n\n"
            "Context docs: {{docs}}\n\n"
            "User message: {{message}}\n\n"
            "Please provide a clear and concise response."
        ),
        labels=["baseline", "production"]
    )
    print(f"Created v1 successfully (Version: {prompt_v1.version}) with labels 'baseline', 'production'.")

    print("\nCreating Version 2 (v2)...")
    prompt_v2 = client.create_prompt(
        name="day13-chat",
        type="text",
        prompt=(
            "You are an expert AI assistant tasked with answering user queries regarding: {{feature}}.\n\n"
            "Please strictly refer to the provided documentation below to answer the user's message.\n\n"
            "<docs>\n{{docs}}\n</docs>\n\n"
            "<user_message>\n{{message}}\n</user_message>\n\n"
            "Provide a detailed, step-by-step response based on the docs."
        ),
        labels=["candidate"]
    )
    print(f"Created v2 successfully (Version: {prompt_v2.version}) with label 'candidate'.")
    
    print("\nDone! You can check the Langfuse dashboard.")

if __name__ == "__main__":
    create_prompts()
