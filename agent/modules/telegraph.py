"""
Consolidated Telegraph module — публикация статей на Telegra.ph.
Объединяет функционал из 5 предыдущих модулей в один.
"""

import asyncio
import re
import requests
from typing import Optional


class TelegraphClient:
    BASE_URL = "https://api.telegra.ph"

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.session = requests.Session()

    def create_account(self, short_name: str = "Jarvis", author_name: str = "Jarvis AI") -> dict:
        """Создать аккаунт Telegraph и получить access_token."""
        resp = self.session.get(
            f"{self.BASE_URL}/createAccount",
            params={"short_name": short_name, "author_name": author_name}
        )
        result = resp.json()
        if result.get("ok"):
            self.access_token = result["result"]["access_token"]
        return result

    def _ensure_auth(self):
        """Создать аккаунт если нет токена."""
        if not self.access_token:
            self.create_account()

    def upload_image(self, image_path: str) -> Optional[str]:
        """Загрузить изображение на Telegraph и вернуть URL."""
        try:
            with open(image_path, 'rb') as f:
                resp = requests.post(
                    "https://telegra.ph/upload",
                    files={'file': ('image.jpg', f, 'image/jpeg')}
                )
            if resp.status_code == 200:
                result = resp.json()
                if isinstance(result, list) and result:
                    return f"https://telegra.ph{result[0]['src']}"
            return None
        except Exception:
            return None

    def _markdown_to_html(self, md: str) -> str:
        """Простая конвертация Markdown в HTML для Telegraph."""
        html = md

        # Headers
        html = re.sub(r'^### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Links
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)

        # Code blocks
        html = re.sub(r'```[\w]*\n(.*?)```', r'<pre>\1</pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

        # Lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        # Remove nested ul tags
        html = re.sub(r'</ul>\s*<ul>', '', html)

        # Paragraphs (double newlines)
        paragraphs = html.split('\n\n')
        result_parts = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith('<'):
                p = f'<p>{p}</p>'
            if p:
                result_parts.append(p)
        html = '\n'.join(result_parts)

        # Single newlines to <br>
        html = re.sub(r'(?<!>)\n(?!<)', '<br/>', html)

        return html

    def create_page(self, title: str, content: str, author_name: str = "Jarvis AI",
                    is_markdown: bool = False) -> dict:
        """Создать страницу на Telegraph.

        Args:
            title: Заголовок статьи
            content: HTML или Markdown контент
            author_name: Имя автора
            is_markdown: True если контент в формате Markdown
        """
        self._ensure_auth()

        if is_markdown:
            content = self._markdown_to_html(content)

        resp = self.session.post(
            f"{self.BASE_URL}/createPage",
            json={
                "access_token": self.access_token,
                "title": title,
                "content": [{"tag": "p", "children": [content]}] if '<' not in content else content,
                "author_name": author_name,
                "return_content": False
            }
        )

        # Telegraph API может принимать content как HTML-строку через параметры
        # Пробуем альтернативный формат если первый не сработал
        result = resp.json()
        if not result.get("ok"):
            resp = self.session.get(
                f"{self.BASE_URL}/createPage",
                params={
                    "access_token": self.access_token,
                    "title": title,
                    "content": content,
                    "author_name": author_name,
                }
            )
            result = resp.json()

        return result

    def edit_page(self, path: str, title: str, content: str,
                  author_name: str = "Jarvis AI") -> dict:
        """Редактировать существующую страницу.

        Args:
            path: Путь страницы (из URL)
            title: Новый заголовок
            content: Новый HTML-контент
            author_name: Имя автора
        """
        self._ensure_auth()
        resp = self.session.get(
            f"{self.BASE_URL}/editPage/{path}",
            params={
                "access_token": self.access_token,
                "title": title,
                "content": content,
                "author_name": author_name,
            }
        )
        return resp.json()


# Singleton client
_client = TelegraphClient()


async def publish_telegraph(title: str, content: str,
                            author_name: str = "Jarvis AI",
                            is_markdown: bool = False) -> str:
    """Опубликовать статью на Telegraph. Возвращает URL.

    Args:
        title: Заголовок статьи
        content: Текст статьи (HTML или Markdown)
        author_name: Имя автора (по умолчанию "Jarvis AI")
        is_markdown: True если контент в Markdown формате
    """
    try:
        result = await asyncio.to_thread(
            _client.create_page, title, content, author_name, is_markdown
        )
        if result.get("ok"):
            url = result["result"].get("url", f"https://telegra.ph/{result['result']['path']}")
            return f"Статья опубликована: {url}"
        return f"Ошибка публикации: {result.get('error', 'Неизвестная ошибка')}"
    except Exception as e:
        return f"Ошибка: {e}"


async def upload_telegraph_image(image_path: str) -> str:
    """Загрузить изображение на Telegraph и вернуть URL.

    Args:
        image_path: Локальный путь к файлу изображения
    """
    try:
        url = await asyncio.to_thread(_client.upload_image, image_path)
        if url:
            return f"Изображение загружено: {url}"
        return "Ошибка загрузки изображения"
    except Exception as e:
        return f"Ошибка: {e}"


def register_tools(registry):
    """Register Telegraph tools."""
    registry.register(
        "publish_telegraph",
        publish_telegraph,
        "Опубликовать статью на Telegraph. Args: title (str), content (str — HTML или Markdown), "
        "author_name (str, опционально), is_markdown (bool, опционально)",
    )
    registry.register(
        "upload_telegraph_image",
        upload_telegraph_image,
        "Загрузить изображение на Telegraph. Args: image_path (str — путь к файлу)",
    )
