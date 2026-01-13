"""IndexNow service for instant URL submission to Bing, Yandex, and participating search engines.

IndexNow protocol allows websites to notify search engines about content changes,
reducing indexing time from days to minutes.

Spec: https://www.indexnow.org/documentation
"""

import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# IndexNow configuration
INDEXNOW_KEY = os.getenv("INDEXNOW_KEY", "")
INDEXNOW_HOST = "https://941return.com"
INDEXNOW_API_URLS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
]
# Rate limit: 10,000 URLs/day per spec
MAX_URLS_PER_BATCH = 10000


def is_configured() -> bool:
    """Check if IndexNow is configured with a valid key."""
    return bool(INDEXNOW_KEY and len(INDEXNOW_KEY) >= 8)


def get_key() -> str:
    """Return the IndexNow API key."""
    return INDEXNOW_KEY


async def submit_url(url: str) -> bool:
    """Submit a single URL to IndexNow.

    Args:
        url: The full URL to submit (e.g., https://941return.com/blog/my-post)

    Returns:
        True if submission was successful, False otherwise
    """
    if not is_configured():
        logger.warning("IndexNow key not configured, skipping submission")
        return False

    return await submit_urls([url])


async def submit_urls(urls: list[str]) -> bool:
    """Submit multiple URLs to IndexNow.

    Args:
        urls: List of full URLs to submit

    Returns:
        True if submission was successful, False otherwise
    """
    if not is_configured():
        logger.warning("IndexNow key not configured, skipping submission")
        return False

    if not urls:
        return True

    if len(urls) > MAX_URLS_PER_BATCH:
        logger.warning(f"Batch size {len(urls)} exceeds limit {MAX_URLS_PER_BATCH}")
        urls = urls[:MAX_URLS_PER_BATCH]

    # Use batch submission for multiple URLs
    payload = {
        "host": "941return.com",
        "key": INDEXNOW_KEY,
        "keyLocation": f"{INDEXNOW_HOST}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }

    success = False
    async with httpx.AsyncClient(timeout=10.0) as client:
        for api_url in INDEXNOW_API_URLS:
            try:
                response = await client.post(
                    api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                # 200 = OK, 202 = Accepted
                if response.status_code in (200, 202):
                    logger.info(
                        f"IndexNow submission successful to {api_url}: "
                        f"{len(urls)} URLs, status {response.status_code}"
                    )
                    success = True
                    break
                else:
                    logger.warning(
                        f"IndexNow submission to {api_url} returned {response.status_code}: "
                        f"{response.text}"
                    )
            except httpx.RequestError as e:
                logger.error(f"IndexNow request to {api_url} failed: {e}")
                continue

    return success


async def submit_blog_post(slug: str) -> bool:
    """Submit a blog post URL to IndexNow.

    Args:
        slug: The blog post slug

    Returns:
        True if submission was successful
    """
    url = f"{INDEXNOW_HOST}/blog/{slug}"
    return await submit_url(url)


async def submit_all_blog_posts(slugs: list[str]) -> bool:
    """Submit all blog post URLs to IndexNow (useful for initial indexing).

    Args:
        slugs: List of blog post slugs

    Returns:
        True if submission was successful
    """
    urls = [f"{INDEXNOW_HOST}/blog/{slug}" for slug in slugs]
    return await submit_urls(urls)
