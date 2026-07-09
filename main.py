import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

from scraper import fetch_articles
from markdowner import clean_html_to_markdown, slugify
from uploader import (
    create_file_search_store_if_needed,
    upload_markdown_file,
    count_documents
)


load_dotenv()

DATA_DIR = Path("data/markdown")
STATE_DIR = Path("state")
LOGS_DIR = Path("logs")

STATE_FILE = STATE_DIR / "articles_state.json"
LAST_RUN_FILE = LOGS_DIR / "last_run.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_state():
    if not STATE_FILE.exists():
        return {"_meta": {}}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def save_log(log):
    with open(LAST_RUN_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def estimate_chunks(markdown: str) -> int:
    chunk_size_tokens = int(os.getenv("CHUNK_SIZE_TOKENS", "800"))

    # Ước lượng: 1 token khoảng 4 ký tự tiếng Anh
    approx_tokens = max(1, len(markdown) // 4)

    return max(1, (approx_tokens + chunk_size_tokens - 1) // chunk_size_tokens)


def main():
    ensure_dirs()

    max_articles = int(os.getenv("MAX_ARTICLES", "30"))
    upload_enabled = os.getenv("UPLOAD_TO_GEMINI", "true").lower() == "true"

    state = load_state()

    store_name = (
        os.getenv("GEMINI_FILE_SEARCH_STORE_NAME")
        or state.get("_meta", {}).get("gemini_file_search_store_name")
    )

    if upload_enabled:
        store_name = create_file_search_store_if_needed(store_name)
        state.setdefault("_meta", {})["gemini_file_search_store_name"] = store_name

    articles = fetch_articles(limit=max_articles)

    counts = {
        "added": 0,
        "updated": 0,
        "skipped": 0,
        "uploaded_files": 0,
        "estimated_chunks": 0,
        "failed": 0
    }

    processed_items = []

    for article in articles:
        article_id = str(article.get("id"))
        title = article.get("title") or f"Article {article_id}"
        article_url = article.get("html_url") or ""
        updated_at = article.get("updated_at") or ""
        body_html = article.get("body") or ""

        slug = f"{slugify(title)}-{article_id}"
        file_path = DATA_DIR / f"{slug}.md"

        markdown = clean_html_to_markdown(
            title=title,
            article_url=article_url,
            updated_at=updated_at,
            html=body_html
        )

        content_hash = sha256_text(markdown)
        old_record = state.get(article_id)

        if not old_record:
            status = "added"
        elif old_record.get("hash") != content_hash:
            status = "updated"
        else:
            status = "skipped"

        file_path.write_text(markdown, encoding="utf-8")

        estimated = estimate_chunks(markdown)

        if status == "skipped":
            counts["skipped"] += 1
        else:
            counts[status] += 1
            counts["estimated_chunks"] += estimated

            if upload_enabled:
                try:
                    upload_result = upload_markdown_file(
                        store_name=store_name,
                        file_path=str(file_path)
                    )

                    counts["uploaded_files"] += 1

                    state[article_id] = {
                        "article_id": article_id,
                        "title": title,
                        "article_url": article_url,
                        "updated_at": updated_at,
                        "slug": slug,
                        "file_path": str(file_path),
                        "hash": content_hash,
                        "gemini_store_name": store_name,
                        "upload_status": upload_result.get("status"),
                        "estimated_chunks": estimated,
                        "last_seen_at": now_iso()
                    }

                except Exception as exc:
                    counts["failed"] += 1
                    print(f"Upload failed for {title}: {exc}")

            else:
                state[article_id] = {
                    "article_id": article_id,
                    "title": title,
                    "article_url": article_url,
                    "updated_at": updated_at,
                    "slug": slug,
                    "file_path": str(file_path),
                    "hash": content_hash,
                    "estimated_chunks": estimated,
                    "last_seen_at": now_iso()
                }

        processed_items.append({
            "id": article_id,
            "title": title,
            "status": status,
            "file": str(file_path),
            "url": article_url,
            "estimated_chunks": estimated
        })

    document_count = None

    if upload_enabled and store_name:
        document_count = count_documents(store_name)

    log = {
        "run_at": now_iso(),
        "gemini_file_search_store_name": store_name,
        "max_articles": max_articles,
        "counts": counts,
        "document_count": document_count,
        "items": processed_items
    }

    save_state(state)
    save_log(log)

    print("\n===== LAST RUN SUMMARY =====")
    print(json.dumps(log["counts"], indent=2))
    print(f"Gemini File Search Store: {store_name}")
    print(f"Document count: {document_count}")
    print(f"State saved to: {STATE_FILE}")
    print(f"Log saved to: {LAST_RUN_FILE}")

    if counts["failed"] > 0:
        raise SystemExit(1)

    raise SystemExit(0)


if __name__ == "__main__":
    main()