"""
Worker HTML — збирає новини з Ukrinform.ua через Crawl4AI.
Зберігає raw HTML та normalized JSON.
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from bs4 import BeautifulSoup

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker-html")

# --- Config ---
CONFIG_PATH = Path("config.json")
with open(CONFIG_PATH) as f:
    config = json.load(f)

SOURCE = config["source"]
BASE_URL = config["base_url"]
START_URLS = config["start_urls"]
MAX_PAGES = config["max_pages"]
OUTPUT_DIR = Path(config["output_dir"])

RAW_DIR = OUTPUT_DIR / "raw"
NORM_DIR = OUTPUT_DIR / "normalized"
RAW_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)


def make_id(url: str) -> str:
    """Create a short deterministic ID from URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def extract_article_links(html: str, base_url: str) -> list[str]:
    """Extract article links from a rubric/listing page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Ukrinform article URLs: /rubric-xxx/1234567-slug.html
        if href.startswith("/rubric-") and href.endswith(".html"):
            links.append(base_url + href)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique.append(link)
    return unique


def parse_article(html: str, url: str) -> dict:
    """Parse a single article page into normalized format."""
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "No title"

    # Get article body
    article_body = soup.select_one(".newsText") or soup.select_one("article")
    if article_body:
        # Remove scripts and styles
        for tag in article_body.find_all(["script", "style"]):
            tag.decompose()
        content = article_body.get_text(separator="\n", strip=True)
    else:
        content = ""

    # Extract all links from article
    links = []
    if article_body:
        for a_tag in article_body.find_all("a", href=True):
            links.append(a_tag["href"])

    return {
        "url": url,
        "title": title,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE,
        "content": content,
        "links": links,
    }


async def crawl_page(crawler: AsyncWebCrawler, url: str) -> str | None:
    """Crawl a single URL and return HTML."""
    try:
        result = await crawler.arun(url=url, config=CrawlerRunConfig())
        if result.success:
            return result.html
        else:
            logger.warning(f"Failed to crawl {url}: {result.error_message}")
            return None
    except Exception as e:
        logger.error(f"Error crawling {url}: {e}")
        return None


async def main():
    logger.info("=== Worker HTML started ===")
    logger.info(f"Source: {SOURCE}, Max pages: {MAX_PAGES}")

    browser_config = BrowserConfig(headless=True)
    article_urls: list[str] = []

    # Step 1: Collect article URLs from listing pages
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for start_url in START_URLS:
            logger.info(f"Fetching listing page: {start_url}")
            html = await crawl_page(crawler, start_url)
            if html:
                links = extract_article_links(html, BASE_URL)
                logger.info(f"  Found {len(links)} article links")
                article_urls.extend(links)

            if len(article_urls) >= MAX_PAGES:
                break

    # Limit to max pages
    article_urls = list(dict.fromkeys(article_urls))[:MAX_PAGES]
    logger.info(f"Total unique articles to fetch: {len(article_urls)}")

    # Step 2: Fetch and parse each article
    success_count = 0
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i, url in enumerate(article_urls, 1):
            logger.info(f"[{i}/{len(article_urls)}] Fetching: {url}")
            html = await crawl_page(crawler, url)

            if not html:
                continue

            page_id = make_id(url)

            # Save raw HTML
            raw_path = RAW_DIR / f"{page_id}.html"
            raw_path.write_text(html, encoding="utf-8")
            logger.info(f"  Saved raw: {raw_path.name}")

            # Parse and save normalized JSON
            article = parse_article(html, url)
            norm_path = NORM_DIR / f"{page_id}.json"
            norm_path.write_text(
                json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info(f"  Saved normalized: {norm_path.name}")
            success_count += 1

    logger.info(f"=== Done. Successfully processed {success_count}/{len(article_urls)} articles ===")


if __name__ == "__main__":
    asyncio.run(main())
