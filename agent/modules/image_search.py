"""
Image search module — поиск и скачивание изображений через Tavily API.
Поддерживает SDK и прямые HTTP-вызовы (fallback).
"""

import os
import asyncio
import aiohttp
import requests
import config

TAVILY_API_URL = "https://api.tavily.com/search"


def register_tools(registry):
    registry.register(
        name="search_and_download_images",
        func=search_and_download_images,
        description="Поиск и скачивание изображений через Tavily API. "
                    "Args: query (str), max_results (int, опционально), send_to_chat (bool, опционально).",
        requires_context=True
    )


async def search_and_download_images(query: str, max_results: int = 3, send_to_chat: bool = False,
                                     bot=None, chat_id=None, **kwargs) -> dict:
    """Поиск и скачивание изображений.

    Args:
        query: Поисковый запрос
        max_results: Максимум результатов (по умолчанию 3)
        send_to_chat: Отправить в чат (по умолчанию нет)
    """
    try:
        api_key = getattr(config, 'TAVILY_API_KEY', None)
        if not api_key:
            return {"success": False, "error": "TAVILY_API_KEY не найден"}

        def fetch_urls():
            # Пробуем SDK, fallback на HTTP
            try:
                from tavily import TavilyClient
                client = TavilyClient(api_key=api_key)
                response = client.search(query=query, search_depth="advanced", include_images=True)
            except ImportError:
                payload = {
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_images": True,
                    "max_results": 5,
                }
                resp = requests.post(TAVILY_API_URL, json=payload, timeout=20)
                resp.raise_for_status()
                response = resp.json()
            return response.get("images", [])[:max_results]

        try:
            image_urls = await asyncio.to_thread(fetch_urls)
        except Exception as e:
            return {"success": False, "error": f"Tavily search failed: {str(e)}"}

        if not image_urls:
            return {"success": True, "downloaded": 0, "sent_to_chat": 0, "local_paths": []}

        save_dir = os.path.join("downloads", "images", str(chat_id) if chat_id else "public")
        os.makedirs(save_dir, exist_ok=True)

        downloaded = []
        async with aiohttp.ClientSession() as session:
            for i, url in enumerate(image_urls):
                if not isinstance(url, str) or not url.startswith("http"):
                    continue
                try:
                    ext = url.split(".")[-1].split("?")[0]
                    if len(ext) > 4 or not ext.isalnum():
                        ext = "jpg"
                    safe_query = "".join(c if c.isalnum() else "_" for c in query)[:15]
                    filepath = os.path.join(save_dir, f"{safe_query}_{i}.{ext}")

                    timeout = aiohttp.ClientTimeout(total=10)
                    async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout) as img_resp:
                        if img_resp.status == 200:
                            with open(filepath, 'wb') as f:
                                async for chunk in img_resp.content.iter_chunked(8192):
                                    f.write(chunk)
                            downloaded.append({"path": filepath})
                except Exception:
                    continue

        sent_count = 0
        paths = [f["path"] for f in downloaded]

        if send_to_chat and bot and chat_id:
            for file_info in downloaded:
                try:
                    with open(file_info["path"], 'rb') as photo_file:
                        await bot.send_photo(chat_id=chat_id, photo=photo_file)
                    sent_count += 1
                except Exception:
                    pass

        return {"success": True, "downloaded": len(paths), "sent_to_chat": sent_count, "local_paths": paths}

    except Exception as e:
        return {"success": False, "error": str(e)}
