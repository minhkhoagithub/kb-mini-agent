import re
import unicodedata
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def slugify(text: str, max_length: int = 90) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_length] or "article"


def clean_html_to_markdown(title: str, article_url: str, updated_at: str, html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup.select("script, style, nav, footer, header, form"):
        tag.decompose()

    markdown_body = md(
        str(soup),
        heading_style="ATX",
        bullets="-",
        strip=["span"]
    )

    markdown_body = re.sub(r"\n{3,}", "\n\n", markdown_body)
    markdown_body = markdown_body.strip()

    return f"""# {title}

Article URL: {article_url}
Updated At: {updated_at}

{markdown_body}
"""