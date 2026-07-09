import os
import time
from google import genai


SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply.
"""


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in .env")

    return genai.Client(api_key=api_key)


def create_file_search_store_if_needed(existing_store_name: str | None):
    client = get_client()

    if existing_store_name:
        return existing_store_name

    display_name = os.getenv(
        "FILE_SEARCH_STORE_DISPLAY_NAME",
        "alpha_support_knowledge_base"
    )

    store = client.file_search_stores.create(
        config={
            "display_name": display_name,
            "embedding_model": "models/gemini-embedding-2"
        }
    )

    print("\nCreated new Gemini File Search Store:")
    print(f"GEMINI_FILE_SEARCH_STORE_NAME={store.name}")
    print("Copy this value into your .env file.\n")

    return store.name


def upload_markdown_file(store_name: str, file_path: str):
    client = get_client()

    chunk_size = int(os.getenv("CHUNK_SIZE_TOKENS", "800"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP_TOKENS", "200"))

    operation = client.file_search_stores.upload_to_file_search_store(
        file=file_path,
        file_search_store_name=store_name,
        config={
            "display_name": os.path.basename(file_path),
            "chunking_config": {
                "white_space_config": {
                    "max_tokens_per_chunk": chunk_size,
                    "max_overlap_tokens": chunk_overlap
                }
            }
        }
    )

    while not operation.done:
        print("Waiting for Gemini indexing...")
        time.sleep(5)
        operation = client.operations.get(operation)

    return {
        "status": "completed",
        "file_path": file_path
    }


def count_documents(store_name: str):
    client = get_client()

    count = 0
    try:
        for _ in client.file_search_stores.documents.list(parent=store_name):
            count += 1
    except Exception as exc:
        return f"Could not count documents: {exc}"

    return count