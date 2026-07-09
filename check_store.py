import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
store_name = os.getenv("GEMINI_FILE_SEARCH_STORE_NAME")

print("Store:", store_name)

docs = list(client.file_search_stores.documents.list(parent=store_name))

print("Document count:", len(docs))

for doc in docs[:5]:
    print(doc)