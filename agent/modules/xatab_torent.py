import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from datetime import datetime

BASE_URL = "https://byxatab.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def search_games(query: str, page: int = 1) -> dict:
    """
    Поиск игр на byxatab.com

    Args:
        query: поисковый запрос (название игры)
        page: номер страницы (по умолчанию 1)

    Returns:
        dict с списком найденных игр
    """
    try:
        if query:
            url = f"{BASE_URL}/search/{query}/"
            if page > 1:
                url = f"{BASE_URL}/search/{query}/page/{page}/"
        else:
            if page == 1:
                url = BASE_URL
            else:
                url = f"{BASE_URL}/page/{page}/"

        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.content, "html.parser")

        games = []
        seen_urls = set()

        game_links = soup.find_all(
            "a", class_=lambda x: x and ("grid-item" in x or "release2" in x)
        )

        for game_link in game_links:
            try:
                url = game_link.get("href", "")
                if not url or "/games/" not in url:
                    continue

                if url in seen_urls:
                    continue
                seen_urls.add(url)

                classes = game_link.get("class", [])
                if "release" in classes and "release2" not in classes:
                    continue

                title_div = (
                    game_link.find("div", class_="item__title")
                    or game_link.find("div", class_="item__title2")
                    or game_link.find("div", class_="release__title")
                )

                if not title_div:
                    continue
                title = title_div.text.strip()

                img_tag = game_link.find("img")
                image = ""
                if img_tag:
                    image = img_tag.get("src", "")
                    if image and not image.startswith("http"):
                        image = BASE_URL + image

                if not image:
                    continue

                games.append({"title": title, "url": url, "image": image})

                if len(games) >= 50:
                    break

            except Exception as e:
                continue

        return {
            "success": True,
            "query": query,
            "page": page,
            "count": len(games),
            "games": games,
            "last_updated": datetime.now().strftime("%H:%M %d.%m.%Y"),
        }

    except requests.RequestException as e:
        return {"success": False, "error": f"Ошибка сети: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Ошибка парсинга: {str(e)}"}


def get_game_details(game_url: str) -> dict:
    """
    Получить детали игры (описание, картинка, ссылка на торрент)

    Args:
        game_url: полный URL страницы игры

    Returns:
        dict с информацией об игре
    """
    try:
        response = requests.get(game_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.content, "html.parser")

        title_tag = soup.find("h1")
        title = title_tag.text.strip() if title_tag else "Unknown"

        desc_el = (
            soup.find("div", class_="full-story")
            or soup.find("div", class_="entry-content")
            or soup.find("div", class_="page__text")
        )
        description = desc_el.decode_contents() if desc_el else ""

        upd_el = soup.find("div", class_="page__upd")
        last_updated = upd_el.text.strip() if upd_el else ""

        img_tag = soup.find("div", class_="page__poster")
        poster = ""
        if img_tag:
            img = img_tag.find("img")
            if img:
                poster = img.get("src", "")
                if poster and not poster.startswith("http"):
                    poster = BASE_URL + poster

        if not poster:
            og_image = soup.find("meta", property="og:image")
            if og_image:
                poster = og_image.get("content", "")

        tech_specs = {}
        tech_list = soup.find("ul", class_="page__tech")
        if tech_list:
            items = tech_list.find_all("li")
            for item in items:
                span = item.find("span")
                if span:
                    key = span.text.strip()
                    value = item.get_text(strip=True).replace(key, "").strip()
                    tech_specs[key] = value

        download_link = ""
        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link.get("href", "")
            if "do=download" in href:
                if href.startswith("/"):
                    download_link = BASE_URL + href
                elif href.startswith("http"):
                    download_link = href
                else:
                    download_link = BASE_URL + "/" + href
                break

        screenshots = []
        scr_section = soup.find("div", class_="page__scr")
        if scr_section:
            imgs = scr_section.find_all("img")
            for img in imgs:
                src = img.get("src", "")
                if src and "no_image" not in src:
                    if not src.startswith("http"):
                        src = BASE_URL + src
                    screenshots.append(src)

        return {
            "success": True,
            "title": title,
            "description": description,
            "poster": poster,
            "screenshots": screenshots[:10],
            "download_url": download_link,
            "original_url": game_url,
            "last_updated": last_updated,
            "tech_specs": tech_specs,
            "last_scraped": datetime.now().strftime("%H:%M %d.%m.%Y"),
        }

    except requests.RequestException as e:
        return {"success": False, "error": f"Ошибка сети: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Ошибка парсинга: {str(e)}"}


def get_new_games(page: int = 1) -> dict:
    """
    Получить список новых игр

    Args:
        page: номер страницы
    """
    return search_games("", page)


def format_search_results(data: dict) -> str:
    """Форматирует результаты поиска для вывода"""
    if not data.get("success"):
        return f"❌ Ошибка: {data.get('error', 'Неизвестная ошибка')}"

    games = data.get("games", [])
    if not games:
        return f"По запросу '{data.get('query')}' ничего не найдено"

    result = f"🎮 **Результаты поиска: {data['query']}**\n"
    result += f"Найдено: {len(games)} игр\n\n"

    for i, game in enumerate(games[:15], 1):
        result += f"{i}. **{game['title']}**\n"
        result += f"   [Ссылка]({game['url']})\n"

    if len(games) > 15:
        result += f"\n... и ещё {len(games) - 15} игр"

    return result


def format_game_details(data: dict) -> str:
    """Форматирует детали игры для вывода"""
    if not data.get("success"):
        return f"❌ Ошибка: {data.get('error', 'Неизвестная ошибка')}"

    result = f"🎮 **{data['title']}**\n\n"

    if data.get("poster"):
        result += f"![Постер]({data['poster']})\n\n"

    if data.get("download_url"):
        result += f"⬇️ [Скачать торрент]({data['download_url']})\n\n"

    if data.get("tech_specs"):
        result += "**Системные требования:**\n"
        for key, value in data["tech_specs"].items():
            if key and value:
                result += f"- {key}: {value}\n"
        result += "\n"

    desc = data.get("description", "")
    if desc:
        clean_desc = re.sub(r"<[^>]+>", "", desc)[:500]
        result += f"**Описание:**\n{clean_desc}...\n"

    if data.get("last_updated"):
        result += f"\nОбновлено: {data['last_updated']}"

    return result


def register_tools(registry):
    """Регистрирует инструменты для работы с xatab"""
    registry.register(
        "xatab_search",
        search_games,
        "Поиск игр на xatab. Аргумент: query (название игры для поиска).",
    )
    registry.register(
        "xatab_game_details",
        get_game_details,
        "Получить детали игры (описание, скриншоты, ссылка на торрент). Аргумент: game_url (URL страницы игры).",
    )
    registry.register(
        "xatab_new_games", get_new_games, "Получить список новых игр на xatab."
    )
