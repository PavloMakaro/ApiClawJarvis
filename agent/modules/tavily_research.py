"""
Tavily research module — глубокий поиск через Tavily API.
Поддерживает оба варианта: SDK (tavily-python) и прямые HTTP-вызовы.
"""

import requests
import config


TAVILY_API_URL = "https://api.tavily.com/search"


def _search_via_sdk(query):
    """Поиск через tavily-python SDK (если установлен)."""
    from tavily import TavilyClient
    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    return client.search(
        query=query,
        search_depth="advanced",
        include_answer=True,
        max_results=5
    )


def _search_via_http(query):
    """Поиск через прямой HTTP-вызов (fallback)."""
    payload = {
        "api_key": config.TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "include_answer": True,
        "max_results": 5,
    }
    resp = requests.post(TAVILY_API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def tavily_deep_research(query: str) -> str:
    """
    Глубокое исследование через Tavily API.

    Args:
        query: Поисковый запрос

    Returns:
        str: Синтезированный ответ с источниками
    """
    try:
        api_key = getattr(config, 'TAVILY_API_KEY', None)
        if not api_key:
            return "Ошибка: TAVILY_API_KEY не найден в config.py"

        # Пробуем SDK, если не получится — HTTP fallback
        try:
            data = _search_via_sdk(query)
        except ImportError:
            data = _search_via_http(query)

        answer = data.get('answer', 'Ответ не сгенерирован.')
        sources = data.get('results', [])

        result = f"🔍 **Результат исследования:**\n\n{answer}\n\n"

        if sources:
            result += "📚 **Источники:**\n"
            for i, source in enumerate(sources, 1):
                title = source.get('title', 'Без названия')
                url = source.get('url', '#')
                result += f"{i}. **{title}**\n   {url}\n"

        return result

    except requests.Timeout:
        return "Ошибка: Tavily API не ответил (timeout 30s)."
    except Exception as e:
        return f"Ошибка при исследовании: {str(e)}"


def register_tools(registry):
    registry.register(
        "tavily_deep_research",
        tavily_deep_research,
        "Глубокий поиск через Tavily API — исследует веб, синтезирует ответ с источниками. "
        "Args: query (str — поисковый запрос)."
    )
