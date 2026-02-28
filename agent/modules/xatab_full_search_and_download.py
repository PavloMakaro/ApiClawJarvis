import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from datetime import datetime
from pathlib import Path
import os

BASE_URL = "https://byxatab.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def clean_filename(filename):
    """Очищает строку для использования в имени файла"""
    # Удаляем недопустимые символы
    cleaned = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Заменяем пробелы на подчеркивания
    cleaned = cleaned.replace(' ', '_')
    # Удаляем лишние символы
    cleaned = re.sub(r'[^\w\-_.]', '', cleaned)
    return cleaned.lower()

def xatab_full_search_and_download(game_name):
    """
    Полный поиск игры на xatab: поиск, получение информации, скачивание торрента

    Args:
        game_name (str): Название игры для поиска

    Returns:
        dict: Результат с информацией об игре и путями к файлам
    """
    try:
        # Шаг 1: Поиск игры
        print(f"🔍 Поиск игры: {game_name}")
        search_url = f"{BASE_URL}/search/{urllib.parse.quote(game_name)}/"
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.content, "html.parser")

        # Находим первую найденную игру
        game_link = None
        for link in soup.find_all("a", class_=lambda x: x and ("grid-item" in x or "release2" in x)):
            url = link.get("href", "")
            if url and "/games/" in url:
                game_link = url
                break

        if not game_link:
            return {"success": False, "error": f"Игра '{game_name}' не найдена"}

        # Шаг 2: Получение деталей игры
        print(f"📖 Получение информации об игре")
        response = requests.get(game_link, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.content, "html.parser")

        # Извлекаем информацию
        title_tag = soup.find("h1")
        title = title_tag.text.strip() if title_tag else "Unknown"

        # Создаем чистое имя файла из заголовка
        clean_title = clean_filename(title)

        # Обложка
        img_tag = soup.find("div", class_="page__poster")
        poster_url = ""
        if img_tag:
            img = img_tag.find("img")
            if img:
                poster_url = img.get("src", "")
                if poster_url and not poster_url.startswith("http"):
                    poster_url = BASE_URL + poster_url

        if not poster_url:
            og_image = soup.find("meta", property="og:image")
            if og_image:
                poster_url = og_image.get("content", "")

        # Описание
        desc_el = soup.find("div", class_="full-story") or soup.find("div", class_="entry-content")
        description = ""
        if desc_el:
            # Очищаем HTML теги
            clean_desc = re.sub(r'<[^>]+>', '', desc_el.decode_contents())
            description = clean_desc[:500] + "..." if len(clean_desc) > 500 else clean_desc

        # Ссылка на скачивание
        download_link = ""
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "do=download" in href:
                if href.startswith("/"):
                    download_link = BASE_URL + href
                elif href.startswith("http"):
                    download_link = href
                else:
                    download_link = BASE_URL + "/" + href
                break

        if not download_link:
            return {"success": False, "error": "Ссылка на скачивание не найдена"}

        # Шаг 3: Скачивание обложки
        poster_path = None
        if poster_url:
            try:
                download_dir = Path('downloads/game_covers')
                download_dir.mkdir(parents=True, exist_ok=True)

                poster_filename = f"{clean_title}_cover.jpg"
                poster_path = download_dir / poster_filename

                response = requests.get(poster_url, headers=HEADERS, timeout=10)
                response.raise_for_status()

                with open(poster_path, 'wb') as f:
                    f.write(response.content)

                print(f"✅ Обложка сохранена: {poster_path}")
            except Exception as e:
                print(f"⚠️ Не удалось скачать обложку: {e}")
                poster_path = None

        # Шаг 4: Скачивание торрента
        torrent_path = None
        if download_link:
            try:
                download_dir = Path('downloads/torrents')
                download_dir.mkdir(parents=True, exist_ok=True)

                torrent_filename = f"{clean_title}.torrent"
                torrent_path = download_dir / torrent_filename

                response = requests.get(download_link, headers=HEADERS, stream=True, timeout=30)
                response.raise_for_status()

                with open(torrent_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                print(f"✅ Торрент скачан: {torrent_path}")
            except Exception as e:
                return {"success": False, "error": f"Ошибка при скачивании торрента: {e}"}

        # Формируем результат
        result = {
            "success": True,
            "game_info": {
                "title": title,
                "description": description,
                "original_url": game_link,
                "download_url": download_link,
                "cover_url": poster_url
            },
            "files": {
                "cover_path": str(poster_path) if poster_path else None,
                "torrent_path": str(torrent_path) if torrent_path else None
            },
            "message": f"Игра '{title}' успешно найдена и скачана"
        }

        return result

    except requests.RequestException as e:
        return {"success": False, "error": f"Ошибка сети: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Ошибка: {str(e)}"}

def register_tools(registry):
    """Регистрирует инструменты"""
    registry.register(
        "xatab_full_search_and_download",
        xatab_full_search_and_download,
        "Полный поиск игры на xatab: поиск, получение информации, скачивание торрента и обложки. Аргумент: game_name (название игры)"
    )

# Пример использования:
# result = xatab_full_search_and_download("Manor Lords")
# print(result)