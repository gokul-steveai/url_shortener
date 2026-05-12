import logging
import httpx
from bs4 import BeautifulSoup
from groq import AsyncGroq
from app.core.config import settings

logger = logging.getLogger(__name__)

_SCRAPE_CHAR_LIMIT = 8000  # chars sent to LLM to stay within token budget

_PROMPT = (
    "You are a concise web content analyst. "
    "Given the text extracted from a webpage, write a 2-3 sentence summary "
    "that captures the page's main purpose and key information. "
    "Be direct and informative. Do not start with 'This page' or 'This website'.\n\n"
    "Page content:\n{content}"
)


async def _scrape(url: str) -> tuple[str, str]:
    """Returns (clean_body_text, meta_description)."""
    async with httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; BoltLinkBot/1.0)"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    meta_desc = (meta_tag.get("content", "") if meta_tag else "").strip()

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = " ".join(soup.get_text(separator=" ", strip=True).split())
    return text[:_SCRAPE_CHAR_LIMIT], meta_desc


async def _groq_summarize(content: str) -> str | None:
    """Call Groq to generate a summary."""
    try:
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": _PROMPT.format(content=content)}],
            max_tokens=256,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip() or None
    except Exception as e:
        logger.error("groq.failed error=%s", e, exc_info=True)
        return None


class SummarizerService:

    @classmethod
    async def summarize(cls, url: str) -> str | None:
        try:
            text, meta_desc = await _scrape(url)
        except httpx.HTTPStatusError as e:
            logger.error(
                "scrape.http_error url=%s status=%s", url, e.response.status_code
            )
            return None
        except httpx.RequestError as e:
            logger.error("scrape.request_error url=%s error=%s", url, e)
            return None
        except Exception as e:
            logger.error(
                "scrape.unexpected_error url=%s error=%s", url, e, exc_info=True
            )
            return None

        if not text and not meta_desc:
            return None

        if settings.GROQ_API_KEY:
            summary = await _groq_summarize(text or meta_desc)
            if summary:
                return summary

        if meta_desc:
            return meta_desc

        if text:
            snippet = text[:500].rsplit(" ", 1)[0]
            return snippet + "..." if snippet else None

        return None
