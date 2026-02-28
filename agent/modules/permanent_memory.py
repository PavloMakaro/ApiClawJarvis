"""
Permanent memory module — сохранение и поиск фактов.
Jarvis 2.0: использует keyword-based search вместо векторной памяти.
"""

import asyncio
import os
from core.memory_rag import memory_instance, MEMORY_FILE as _MEMORY_FILE

MEMORY_FILE = os.path.join("Permanent memory", "Permanent-memory")


async def update_memory(info: str) -> str:
    """Сохранить важный факт в постоянную память.

    Args:
        info: Текст факта для сохранения
    """
    try:
        res = await memory_instance.add(info)
        return f"Память обновлена: {res}"
    except Exception as e:
        return f"Ошибка сохранения: {str(e)}"


async def read_memory(query: str = "") -> str:
    """Поиск в памяти по ключевым словам.

    Args:
        query: Поисковый запрос (ключевые слова). Пустой = последние записи.
    """
    try:
        if query:
            results = await memory_instance.search(query, n_results=5)
            if results:
                formatted = "\n".join([f"- {r}" for r in results])
                return f"Найдено в памяти:\n{formatted}"
            else:
                return "В памяти ничего не найдено по запросу."

        # Без запроса — последние 50 записей
        await _ensure_memory_file()

        def _read():
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return f.read()

        content = await asyncio.to_thread(_read)
        if not content.strip():
            return "Память пуста."
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        recent = lines[-50:]
        total = len(lines)
        header = f"[{len(recent)} из {total} записей]\n" if total > 50 else ""
        return header + "\n".join(recent)
    except Exception as e:
        return f"Ошибка чтения памяти: {str(e)}"


async def clear_memory() -> str:
    """Полностью очистить постоянную память."""
    try:
        await _ensure_memory_file()

        def _write():
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                f.write("")

        await asyncio.to_thread(_write)
        memory_instance._cache_valid = False  # Инвалидировать кэш
        return "Память очищена."
    except Exception as e:
        return f"Ошибка очистки: {str(e)}"


async def _ensure_memory_file():
    """Убедиться что файл памяти существует."""
    directory = os.path.dirname(MEMORY_FILE)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        def _create():
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                f.write("")
        await asyncio.to_thread(_create)


def register_tools(registry):
    """Register memory tools."""
    registry.register(
        "update_memory",
        update_memory,
        "Сохранить факт в постоянную память. Args: info (str — текст факта)",
    )
    registry.register(
        "read_memory",
        read_memory,
        "Поиск в памяти по ключевым словам. Args: query (str — поисковый запрос, опционально)",
    )
    registry.register(
        "clear_memory",
        clear_memory,
        "Полностью очистить постоянную память.",
    )
