"""
Telegram tools — отправка файлов, сообщений и фото пользователю.
"""

import os


def register_tools(registry):
    registry.register(
        "send_file", send_file,
        "Отправить файл пользователю в Telegram. Args: filepath (str — путь к файлу).",
        requires_context=True
    )
    registry.register(
        "send_message", send_message,
        "Отправить отдельное сообщение пользователю. Args: text (str), parse_mode (str — 'Markdown' или пусто, опционально).",
        requires_context=True
    )
    registry.register(
        "send_photo", send_photo,
        "Отправить фото пользователю. Args: filepath (str — путь к изображению), caption (str — подпись, опционально).",
        requires_context=True
    )


async def send_file(filepath: str, bot=None, chat_id=None, **kwargs):
    """Отправить файл пользователю.

    Args:
        filepath: Путь к файлу
    """
    if not bot or not chat_id:
        return "Ошибка: нет доступа к Telegram."
    if not os.path.exists(filepath):
        return f"Ошибка: файл '{filepath}' не найден."

    try:
        with open(filepath, 'rb') as f:
            await bot.send_document(chat_id=chat_id, document=f)
        return f"Файл '{os.path.basename(filepath)}' отправлен."
    except Exception as e:
        return f"Ошибка отправки файла: {str(e)}"


async def send_message(text: str, parse_mode: str = "", bot=None, chat_id=None, **kwargs):
    """Отправить сообщение пользователю.

    Args:
        text: Текст сообщения
        parse_mode: Режим форматирования ('Markdown' или пустая строка)
    """
    if not bot or not chat_id:
        return "Ошибка: нет доступа к Telegram."
    try:
        pm = parse_mode if parse_mode else None
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=pm)
        return "Сообщение отправлено."
    except Exception as e:
        # Fallback без parse_mode
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            return "Сообщение отправлено (без форматирования)."
        except Exception as e2:
            return f"Ошибка: {str(e2)}"


async def send_photo(filepath: str, caption: str = "", bot=None, chat_id=None, **kwargs):
    """Отправить фото пользователю.

    Args:
        filepath: Путь к файлу изображения
        caption: Подпись к фото (опционально)
    """
    if not bot or not chat_id:
        return "Ошибка: нет доступа к Telegram."
    if not os.path.exists(filepath):
        return f"Ошибка: файл '{filepath}' не найден."

    try:
        with open(filepath, 'rb') as f:
            await bot.send_photo(chat_id=chat_id, photo=f, caption=caption or None)
        return f"Фото отправлено."
    except Exception as e:
        return f"Ошибка отправки фото: {str(e)}"
