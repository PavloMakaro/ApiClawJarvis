"""
Memory module — keyword-based search over permanent memory file.
Заменяет сломанную векторную память на keyword overlap search.
"""

import os
import re
import asyncio
import logging

logger = logging.getLogger(__name__)

MEMORY_FILE = os.path.join("Permanent memory", "Permanent-memory")


class KeywordMemory:
    """Keyword-based memory search. Не требует внешних API."""

    def __init__(self):
        self.enabled = True
        self._file_cache = None   # Кэш содержимого файла памяти
        self._cache_valid = False # Флаг актуальности кэша

    async def add(self, text, metadata=None):
        """Добавить факт в память (async append)."""
        try:
            os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)

            def _write():
                with open(MEMORY_FILE, "a", encoding="utf-8") as f:
                    f.write(f"\n{text}")

            await asyncio.to_thread(_write)
            self._cache_valid = False  # Инвалидировать кэш при записи
            return "Факт сохранён в память."
        except Exception as e:
            logger.error(f"Memory add error: {e}")
            return f"Ошибка сохранения: {e}"

    async def _get_content(self):
        """Возвращает содержимое файла памяти из кэша или диска."""
        if self._cache_valid and self._file_cache is not None:
            return self._file_cache

        if not os.path.exists(MEMORY_FILE):
            return ""

        def _read():
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return f.read()

        content = await asyncio.to_thread(_read)
        self._file_cache = content
        self._cache_valid = True
        return content

    async def search(self, query, n_results=5):
        """Поиск в памяти по пересечению ключевых слов (async)."""
        try:
            content = await self._get_content()

            if not content.strip():
                return []

            docs = [d.strip() for d in content.split("\n") if d.strip()]

            query_words = set(re.findall(r'\w{2,}', query.lower()))
            if not query_words:
                return docs[-n_results:]

            scored = []
            for doc in docs:
                doc_words = set(re.findall(r'\w{2,}', doc.lower()))
                overlap = len(query_words & doc_words)
                if overlap > 0:
                    score = overlap / len(query_words)
                    scored.append((score, doc))

            scored.sort(reverse=True, key=lambda x: x[0])
            results = [doc for _, doc in scored[:n_results]]

            if not results:
                return docs[-n_results:]

            return results
        except Exception as e:
            logger.error(f"Memory search error: {e}")
            return []


# Singleton
memory_instance = KeywordMemory()
