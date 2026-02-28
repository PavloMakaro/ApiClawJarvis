"""
Text tools — работа с текстом: подсчёт символов/слов, генерация паролей,
кодирование/декодирование, хеширование.
"""

import hashlib
import random
import string
import base64
import json
import urllib.parse


async def text_stats(text: str) -> str:
    """Статистика текста: символы, слова, строки, предложения.

    Args:
        text: Анализируемый текст
    """
    chars = len(text)
    chars_no_spaces = len(text.replace(" ", ""))
    words = len(text.split())
    lines = text.count("\n") + 1
    sentences = sum(1 for c in text if c in ".!?")

    return (
        f"📊 Статистика текста:\n"
        f"• Символов: {chars} (без пробелов: {chars_no_spaces})\n"
        f"• Слов: {words}\n"
        f"• Строк: {lines}\n"
        f"• Предложений: ~{sentences}"
    )


async def generate_password(length: int = 16, include_special: bool = True) -> str:
    """Сгенерировать надёжный пароль.

    Args:
        length: Длина пароля (по умолчанию 16)
        include_special: Включить спецсимволы (по умолчанию да)
    """
    try:
        length = max(8, min(int(length), 128))
        chars = string.ascii_letters + string.digits
        if include_special:
            chars += "!@#$%^&*()-_=+"

        password = ''.join(random.SystemRandom().choice(chars) for _ in range(length))

        # Оценка надёжности
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()-_=+" for c in password)
        score = sum([has_upper, has_lower, has_digit, has_special, length >= 12])

        strength = {5: "💪 Отличный", 4: "✅ Хороший", 3: "⚠️ Средний"}.get(score, "❌ Слабый")

        return f"🔐 Пароль: `{password}`\nДлина: {length} | Надёжность: {strength}"
    except Exception as e:
        return f"Ошибка: {str(e)}"


async def encode_base64(text: str) -> str:
    """Закодировать текст в Base64.

    Args:
        text: Текст для кодирования
    """
    encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    return f"Base64: `{encoded}`"


async def decode_base64(text: str) -> str:
    """Декодировать Base64 в текст.

    Args:
        text: Base64-строка
    """
    try:
        decoded = base64.b64decode(text.strip()).decode("utf-8")
        return f"Декодировано: {decoded}"
    except Exception as e:
        return f"Ошибка декодирования: {str(e)}"


async def hash_text(text: str, algorithm: str = "sha256") -> str:
    """Вычислить хеш текста.

    Args:
        text: Текст для хеширования
        algorithm: Алгоритм (md5, sha1, sha256, sha512)
    """
    try:
        algo = algorithm.lower().strip()
        if algo not in ("md5", "sha1", "sha256", "sha512"):
            return "Ошибка: поддерживаемые алгоритмы — md5, sha1, sha256, sha512"

        h = hashlib.new(algo, text.encode("utf-8"))
        return f"{algo.upper()}: `{h.hexdigest()}`"
    except Exception as e:
        return f"Ошибка: {str(e)}"


async def url_encode(text: str) -> str:
    """URL-кодирование текста.

    Args:
        text: Текст для кодирования
    """
    return f"URL: `{urllib.parse.quote(text, safe='')}`"


async def url_decode(text: str) -> str:
    """URL-декодирование.

    Args:
        text: URL-закодированная строка
    """
    return f"Декодировано: {urllib.parse.unquote(text)}"


def register_tools(registry):
    registry.register(
        "text_stats", text_stats,
        "Статистика текста (символы, слова, строки). Args: text (str)."
    )
    registry.register(
        "generate_password", generate_password,
        "Сгенерировать надёжный пароль. Args: length (int, по умолчанию 16), include_special (bool)."
    )
    registry.register(
        "encode_base64", encode_base64,
        "Закодировать текст в Base64. Args: text (str)."
    )
    registry.register(
        "decode_base64", decode_base64,
        "Декодировать Base64 в текст. Args: text (str)."
    )
    registry.register(
        "hash_text", hash_text,
        "Вычислить хеш текста. Args: text (str), algorithm (str — md5/sha1/sha256/sha512)."
    )
    registry.register(
        "url_encode", url_encode,
        "URL-кодирование текста. Args: text (str)."
    )
    registry.register(
        "url_decode", url_decode,
        "URL-декодирование. Args: text (str)."
    )
