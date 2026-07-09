import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from uploader import SYSTEM_PROMPT


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
store_name = os.getenv("GEMINI_FILE_SEARCH_STORE_NAME")
model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

if not api_key:
    raise RuntimeError("Missing GEMINI_API_KEY in .env")

if not store_name:
    raise RuntimeError("Missing GEMINI_FILE_SEARCH_STORE_NAME in .env")

client = genai.Client(api_key=api_key)

question = 'How do I add a YouTube video? Please answer using the uploaded docs and include the relevant "Article URL:" line.'

prompt = f"""{SYSTEM_PROMPT}

Question: {question}

Important:
- Use File Search only to find the relevant document.
- Answer in no more than 5 bullet points.
- Include the Article URL line from the document if available.
"""

response = client.models.generate_content(
    model=model,
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store_name]
                )
            )
        ],
        temperature=0.2,
        max_output_tokens=800,
    )
)

print("\n===== QUESTION =====")
print(question)

print("\n===== ANSWER =====")
print(response.text)

print("\n===== GROUNDING METADATA =====")
try:
    print(response.candidates[0].grounding_metadata)
except Exception as exc:
    print(f"No grounding metadata printed: {exc}")