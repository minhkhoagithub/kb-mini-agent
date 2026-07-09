import os
import requests


DEFAULT_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json?per_page=100"


def fetch_articles(limit: int = 30):
    start_url = os.getenv("SUPPORT_ARTICLES_URL", DEFAULT_URL)
    articles = []
    url = start_url

    session = requests.Session()
    session.headers.update({
        "User-Agent": "kb-mini-agent/1.0"
    })

    while url and len(articles) < limit:
        print(f"Fetching: {url}")

        response = session.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        batch = data.get("articles", [])

        for article in batch:
            if article.get("body") and article.get("html_url"):
                articles.append(article)

            if len(articles) >= limit:
                break

        url = data.get("next_page")

    return articles[:limit]