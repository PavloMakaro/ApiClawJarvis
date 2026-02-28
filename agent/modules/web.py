"""
Web scraping module - ASYNC VERSION
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup


async def visit_page(url: str) -> str:
    """Visit webpage and extract text"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                response.raise_for_status()
                html = await response.text()

                soup = BeautifulSoup(html, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()

                text = soup.get_text()

                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (
                    phrase.strip() for line in lines for phrase in line.split("  ")
                )
                text = "\n".join(chunk for chunk in chunks if chunk)

                return text[:5000] + "\n...(truncated)" if len(text) > 5000 else text
    except Exception as e:
        return f"Error visiting page: {str(e)}"


async def fetch_url(url: str) -> str:
    """Fetch raw URL content"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                response.raise_for_status()
                return await response.text()
    except Exception as e:
        return f"Error fetching URL: {str(e)}"


def register_tools(registry):
    """Register web tools"""
    registry.register(
        "visit_page", visit_page, "Visit webpage and extract text. Arguments: url (str)"
    )
    registry.register(
        "fetch_url", fetch_url, "Fetch raw URL content. Arguments: url (str)"
    )
