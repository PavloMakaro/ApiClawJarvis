"""
Notes module — заметки и TODO-листы пользователя.
Хранение в JSON-файле, поддержка тегов и приоритетов.
"""

import asyncio
import json
import os
import datetime
from typing import Optional

NOTES_FILE = "data/notes.json"


async def _load_notes():
    if not os.path.exists(NOTES_FILE):
        return {}
    try:
        def _read():
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return await asyncio.to_thread(_read)
    except Exception:
        return {}


async def _save_notes(data):
    os.makedirs("data", exist_ok=True)
    def _write():
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    await asyncio.to_thread(_write)


async def add_note(text: str, tag: str = "general", priority: str = "normal",
                   chat_id=None, **kwargs) -> str:
    """Создать заметку или TODO.

    Args:
        text: Текст заметки
        tag: Тег/категория (general, work, study, personal, idea)
        priority: Приоритет (low, normal, high, urgent)
    """
    if not chat_id:
        return "Ошибка: нет chat_id."

    chat_id = str(chat_id)
    notes = await _load_notes()

    if chat_id not in notes:
        notes[chat_id] = []

    note = {
        "id": len(notes[chat_id]) + 1,
        "text": text,
        "tag": tag,
        "priority": priority,
        "done": False,
        "created": datetime.datetime.now().isoformat(),
    }
    notes[chat_id].append(note)
    await _save_notes(notes)

    icon = {"low": "⬜", "normal": "🟦", "high": "🟧", "urgent": "🟥"}.get(priority, "🟦")
    return f"{icon} Заметка #{note['id']} создана [{tag}]: {text}"


async def list_notes(tag: str = "", show_done: bool = False,
                     chat_id=None, **kwargs) -> str:
    """Показать все заметки. Фильтрация по тегу.

    Args:
        tag: Фильтр по тегу (пусто = все)
        show_done: Показывать выполненные (по умолчанию нет)
    """
    if not chat_id:
        return "Ошибка: нет chat_id."

    chat_id = str(chat_id)
    notes = await _load_notes()
    user_notes = notes.get(chat_id, [])

    if not user_notes:
        return "Заметок нет."

    # Фильтрация
    filtered = user_notes
    if tag:
        filtered = [n for n in filtered if n["tag"] == tag]
    if not show_done:
        filtered = [n for n in filtered if not n.get("done")]

    if not filtered:
        return "Нет подходящих заметок."

    # Сортировка по приоритету
    priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
    filtered.sort(key=lambda n: priority_order.get(n["priority"], 2))

    lines = ["📝 *Заметки:*\n"]
    for n in filtered:
        icon = {"low": "⬜", "normal": "🟦", "high": "🟧", "urgent": "🟥"}.get(n["priority"], "🟦")
        done = "✅" if n.get("done") else icon
        tag_str = f"[{n['tag']}]" if n["tag"] != "general" else ""
        lines.append(f"{done} #{n['id']} {tag_str} {n['text']}")

    return "\n".join(lines)


async def complete_note(note_id: int, chat_id=None, **kwargs) -> str:
    """Пометить заметку как выполненную.

    Args:
        note_id: Номер заметки
    """
    if not chat_id:
        return "Ошибка: нет chat_id."

    chat_id = str(chat_id)
    notes = await _load_notes()
    user_notes = notes.get(chat_id, [])

    note_id = int(note_id)
    for n in user_notes:
        if n["id"] == note_id:
            n["done"] = True
            await _save_notes(notes)
            return f"✅ Заметка #{note_id} выполнена: {n['text']}"

    return f"Заметка #{note_id} не найдена."


async def delete_note(note_id: int, chat_id=None, **kwargs) -> str:
    """Удалить заметку.

    Args:
        note_id: Номер заметки
    """
    if not chat_id:
        return "Ошибка: нет chat_id."

    chat_id = str(chat_id)
    notes = await _load_notes()
    user_notes = notes.get(chat_id, [])

    note_id = int(note_id)
    for i, n in enumerate(user_notes):
        if n["id"] == note_id:
            removed = user_notes.pop(i)
            await _save_notes(notes)
            return f"🗑 Заметка #{note_id} удалена: {removed['text']}"

    return f"Заметка #{note_id} не найдена."


def register_tools(registry):
    registry.register(
        "add_note", add_note,
        "Создать заметку/TODO. Args: text (str), tag (str — general/work/study/personal/idea, опционально), "
        "priority (str — low/normal/high/urgent, опционально).",
        requires_context=True
    )
    registry.register(
        "list_notes", list_notes,
        "Показать заметки. Args: tag (str — фильтр по тегу, опционально), show_done (bool, опционально).",
        requires_context=True
    )
    registry.register(
        "complete_note", complete_note,
        "Пометить заметку как выполненную. Args: note_id (int).",
        requires_context=True
    )
    registry.register(
        "delete_note", delete_note,
        "Удалить заметку. Args: note_id (int).",
        requires_context=True
    )
