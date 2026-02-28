"""
Unified DateTime Module
Объединяет все функции работы с датой и временем.
Все функции асинхронные.
"""

import asyncio
import datetime
import pytz
from typing import Dict, Any, Optional

# Constants
IRKUTSK_TZ = pytz.timezone("Asia/Irkutsk")
MOSCOW_TZ = pytz.timezone("Europe/Moscow")
UTC_TZ = pytz.UTC

# User preferences storage
_user_date_prefs = {
    "preferred_year": None,
    "year_source": "system_current",
    "user_confirmed": False,
}


# ==================== BASIC TIME FUNCTIONS ====================


async def get_current_time() -> str:
    """Get current time in Irkutsk timezone (UTC+8).

    Returns:
        str: Текущее время в формате YYYY-MM-DD HH:MM:SS (Иркутск)
    """
    try:
        now = datetime.datetime.now(IRKUTSK_TZ)
        return now.strftime("%Y-%m-%d %H:%M:%S") + " (Иркутск, UTC+8)"
    except Exception as e:
        return f"Error: {str(e)}"


async def get_irkutsk_time() -> Dict[str, Any]:
    """Get current time in Irkutsk timezone (UTC+8)"""
    try:
        utc_now = datetime.datetime.now(pytz.UTC)
        irkutsk_now = utc_now.astimezone(IRKUTSK_TZ)

        return {
            "date": irkutsk_now.strftime("%Y-%m-%d"),
            "time": irkutsk_now.strftime("%H:%M:%S"),
            "day_of_week": irkutsk_now.strftime("%A"),
            "full_datetime": irkutsk_now.strftime("%Y-%m-%d %H:%M:%S"),
            "is_working_day": irkutsk_now.weekday() < 5,
            "irkutsk_tz": "UTC+8",
        }
    except Exception as e:
        return {"error": str(e)}


async def get_weather(city: str) -> str:
    """Fetch weather from wttr.in"""
    try:
        import aiohttp

        url = f"https://wttr.in/{city}?format=3"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    return text.strip()
                else:
                    return f"Error: Could not fetch weather for {city}. Status: {response.status}"
    except Exception as e:
        return f"Error fetching weather: {str(e)}"


# ==================== DATETIME INFO FUNCTIONS ====================


async def get_current_datetime_info() -> Dict[str, Any]:
    """Get detailed datetime information with timezone data"""
    try:
        now = datetime.datetime.now()
        irkutsk_now = datetime.datetime.now(IRKUTSK_TZ)

        info = {
            "system_date": now.strftime("%Y-%m-%d"),
            "system_time": now.strftime("%H:%M:%S"),
            "system_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "irkutsk_date": irkutsk_now.strftime("%Y-%m-%d"),
            "irkutsk_time": irkutsk_now.strftime("%H:%M:%S"),
            "irkutsk_datetime": irkutsk_now.strftime("%Y-%m-%d %H:%M:%S"),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "weekday": now.strftime("%A"),
            "is_future": now.year > 2024,
            "timezone": "Asia/Irkutsk (UTC+8)",
            "note": "ВСЕГДА проверяйте эту дату перед ответом на вопросы о текущих событиях!",
        }

        return info
    except Exception as e:
        return {"error": str(e), "note": "Не удалось получить информацию о дате"}


def format_date_warning() -> str:
    """Format date warning for system instructions"""
    try:
        info = asyncio.run(get_current_datetime_info())

        if "error" in info:
            return "⚠️ ВНИМАНИЕ: Не удалось проверить системную дату!"

        warning = f"""
⚠️ **ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ О ДАТЕ:**

📅 **СИСТЕМНАЯ ДАТА:** {info["system_datetime"]}
🌏 **ИРКУТСК:** {info["irkutsk_datetime"]} (UTC+8)

🔍 **АНАЛИЗ:**
• Год: {info["year"]}
• Месяц: {info["month"]} ({info["weekday"]})
• День: {info["day"]}
• Это будущее время: {"ДА" if info["is_future"] else "НЕТ"}

🚨 **ИНСТРУКЦИЯ:**
1. ВСЕГДА проверяйте текущую системную дату перед ответом
2. Если год > 2024, информация о "текущих" событиях может быть некорректной
3. Уточняйте у пользователя, какая дата актуальна
4. Для исторических событий используйте конкретные даты из запроса

{info["note"]}
"""
        return warning
    except Exception as e:
        return f"Ошибка при форматировании предупреждения: {str(e)}"


async def check_date_before_response(user_query: str) -> Optional[str]:
    """Check if date warning is needed for user query"""
    try:
        info = await get_current_datetime_info()

        date_sensitive_keywords = [
            "сегодня",
            "сейчас",
            "текущий",
            "идет",
            "live",
            "турнир",
            "матч",
            "погода",
            "расписание",
            "новости",
            "события",
            "актуальн",
            "вчера",
            "завтра",
            "неделя",
            "месяц",
            "год",
        ]

        query_lower = user_query.lower()
        needs_date_check = any(
            keyword in query_lower for keyword in date_sensitive_keywords
        )

        if needs_date_check and info.get("is_future", False):
            return (
                format_date_warning() + f"\n\n📝 **ЗАПРОС ПОЛЬЗОВАТЕЛЯ:** {user_query}"
            )

        return None
    except Exception as e:
        return f"Ошибка проверки даты: {str(e)}"


# ==================== USER DATE PREFERENCES ====================


async def update_date_preferences(user_input: str) -> Dict[str, Any]:
    """Update user date preferences based on input"""
    global _user_date_prefs

    try:
        input_lower = user_input.lower()

        # Determine preferred year
        if "2026" in input_lower or "двадцать шест" in input_lower:
            _user_date_prefs.update(
                {
                    "preferred_year": 2026,
                    "year_source": "user_specified",
                    "user_confirmed": True,
                }
            )
        elif "2024" in input_lower or "двадцать четвёрт" in input_lower:
            _user_date_prefs.update(
                {
                    "preferred_year": 2024,
                    "year_source": "user_specified",
                    "user_confirmed": True,
                }
            )
        elif any(
            word in input_lower for word in ["текущ", "сейчас", "сегодн", "этот год"]
        ):
            current_year = (await get_current_datetime_info()).get("year", 2026)
            _user_date_prefs.update(
                {
                    "preferred_year": current_year,
                    "year_source": "system_current",
                    "user_confirmed": True,
                }
            )

        return _user_date_prefs
    except Exception as e:
        return {"error": str(e)}


async def get_date_context() -> Dict[str, Any]:
    """Get date context for responses"""
    try:
        current_info = await get_current_datetime_info()
        current_year = current_info.get("year", 2026)

        context = {
            "system_year": current_year,
            "preferred_year": _user_date_prefs.get("preferred_year", current_year),
            "year_source": _user_date_prefs.get("year_source", "system_current"),
            "user_confirmed": _user_date_prefs.get("user_confirmed", False),
            "is_aligned": current_year == _user_date_prefs.get("preferred_year"),
            "current_date": current_info.get("system_datetime", "2026-02-16"),
        }

        return context
    except Exception as e:
        return {"error": str(e)}


def register_tools(registry):
    """Register all datetime tools"""
    registry.register(
        "get_current_time", get_current_time, "Returns current date and time"
    )
    registry.register(
        "get_irkutsk_time",
        get_irkutsk_time,
        "Returns current time in Irkutsk timezone (UTC+8)",
    )
    registry.register(
        "get_weather", get_weather, "Get weather for a city. Arguments: city (str)"
    )
    registry.register(
        "get_current_datetime_info",
        get_current_datetime_info,
        "Get detailed datetime information",
    )
    registry.register(
        "check_date_before_response",
        check_date_before_response,
        "Check if date warning needed. Arguments: user_query (str)",
    )
    registry.register(
        "update_date_preferences",
        update_date_preferences,
        "Update user date preferences. Arguments: user_input (str)",
    )
    registry.register(
        "get_date_context", get_date_context, "Get date context for responses"
    )
