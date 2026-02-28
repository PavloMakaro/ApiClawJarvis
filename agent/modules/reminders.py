"""
Unified Reminders Module
Объединяет все функции напоминаний: дневник, расписание пар, системные напоминания.
Все функции асинхронные.
"""

import asyncio
import datetime
import json
import os
from typing import Optional, Dict, List, Any
from zoneinfo import ZoneInfo

# Constants
DATA_DIR = "data"
DIARY_FILE = os.path.join(DATA_DIR, "diary.txt")
SCHEDULE_FILE = os.path.join(DATA_DIR, "schedule_config.json")
DEFAULT_DIARY_TIME = "20:00"
DEFAULT_EVENING_TIME = "20:00"
MORNING_CHECK_TIMES = ["06:00", "07:00", "08:00", "09:00"]

IRKUTSK_TZ = ZoneInfo("Asia/Irkutsk")

# Base schedule data
BASE_SCHEDULE = {
    "числитель": {
        "ПН": [
            {
                "time": "8:30-9:50",
                "subject": "МДК ТОРА",
                "room": "след.м 8:30-9:50 Информатика А301",
            },
            {"time": "10:00-11:20", "subject": "Техническая механика", "room": "П207"},
            {"time": "11:50-13:10", "subject": "ПБДД", "room": "П313"},
        ],
        "ВТ": [
            {"time": "8:30-9:50", "subject": "", "room": "каб"},
            {"time": "10:00-11:20", "subject": "Английский язык", "room": "А107"},
            {"time": "11:50-13:10", "subject": "Электротехника", "room": "А402"},
            {"time": "13:20-14:40", "subject": "Информатика", "room": "А301"},
            {"time": "15:00-16:20", "subject": "Психология общения", "room": "А110"},
        ],
        "СР": [
            {"time": "8:30-9:50", "subject": "МДК Устройство авт.", "room": "П313"},
            {"time": "10:00-11:20", "subject": "Физическая культура", "room": "сп.зал"},
            {"time": "11:50-13:10", "subject": "Инженерная графика", "room": "А111"},
        ],
        "ЧТ": [
            {"time": "8:30-9:50", "subject": "МДК Устройство авт.", "room": "П313"},
            {"time": "10:00-11:20", "subject": "", "room": ""},
            {"time": "11:50-13:10", "subject": "Инженерная графика", "room": "А111"},
        ],
        "ПТ": [
            {"time": "8:30-9:50", "subject": "Электротехника", "room": "А402"},
            {"time": "10:00-11:20", "subject": "МДК Устройство авт.", "room": "П313"},
            {"time": "11:50-13:10", "subject": "Основы философии", "room": "А207"},
        ],
        "СБ": [
            {"time": "8:30-9:50", "subject": "Техническая механика", "room": "П207"},
            {"time": "10:00-11:20", "subject": "", "room": ""},
            {"time": "11:50-13:10", "subject": "ПБДД", "room": "П313"},
            {"time": "13:20-14:40", "subject": "МДК Материалы авт.", "room": "а203"},
        ],
    },
    "знаменатель": {
        "ПН": [
            {"time": "8:30-9:50", "subject": "Информатика", "room": "А301"},
            {"time": "10:00-11:20", "subject": "МДК Материалы авт.", "room": "а203"},
            {"time": "11:50-13:10", "subject": "Английский язык", "room": "А107"},
        ],
        "ВТ": [
            {"time": "8:30-9:50", "subject": "", "room": "каб"},
            {"time": "10:00-11:20", "subject": "МДК Устройство авт.", "room": "Г313"},
            {"time": "11:50-13:10", "subject": "ПБДД", "room": "Г313"},
            {"time": "13:20-14:40", "subject": "Техническая механика", "room": "П207"},
            {"time": "15:00-16:20", "subject": "", "room": ""},
        ],
        "СР": [
            {"time": "8:30-9:50", "subject": "Физическая культура", "room": "сп.зал"},
            {"time": "10:00-11:20", "subject": "МДК Устройство авт.", "room": "Г313"},
            {"time": "11:50-13:10", "subject": "", "room": ""},
        ],
        "ЧТ": [
            {"time": "8:30-9:50", "subject": "Инженерная графика", "room": "А111"},
            {"time": "10:00-11:20", "subject": "Психология общения", "room": "Г103"},
            {"time": "11:50-13:10", "subject": "ПБДД", "room": "Г313"},
        ],
        "ПТ": [
            {"time": "8:30-9:50", "subject": "МДК Устройство авт.", "room": "Г313"},
            {"time": "10:00-11:20", "subject": "МДК ТОРА", "room": "след.м"},
            {"time": "11:50-13:10", "subject": "Инженерная графика", "room": "А111"},
        ],
        "СБ": [
            {"time": "8:30-9:50", "subject": "Основы философии", "room": "А207"},
            {"time": "10:00-11:20", "subject": "МДК Материалы авт.", "room": "а203"},
            {"time": "11:50-13:10", "subject": "Электротехника", "room": "А402"},
            {"time": "13:20-14:40", "subject": "МДК Устройство авт.", "room": "Г313"},
        ],
    },
}


def _ensure_data_dir():
    """Ensure data directory exists"""
    os.makedirs(DATA_DIR, exist_ok=True)


def _get_irkutsk_now() -> datetime.datetime:
    """Get current time in Irkutsk"""
    return datetime.datetime.now(IRKUTSK_TZ)


# ==================== DIARY FUNCTIONS ====================


async def initialize_diary() -> Dict[str, Any]:
    """Initialize diary file with template if not exists"""
    try:
        _ensure_data_dir()

        if os.path.exists(DIARY_FILE):
            return {
                "status": "exists",
                "message": "Файл дневника уже существует",
                "filepath": DIARY_FILE,
            }

        template = """# 📓 МОЙ ДНЕВНИК

## Как пользоваться:
1. Каждый день добавляйте новую запись с датой: ## ГГГГ-ММ-ДД
2. Пишите о событиях дня, мыслях, планах
3. Используйте маркеры для структуры

## Пример записи:
## 2026-02-16
• Утром была пара по МДК ТОРА
• Днем работал над проектом
• Вечером занимался спортом
• Завтра нужно подготовиться к экзамену

---

"""

        await asyncio.to_thread(_write_file_sync, DIARY_FILE, template)

        return {
            "status": "created",
            "message": "Файл дневника создан с шаблоном",
            "filepath": DIARY_FILE,
        }
    except Exception as e:
        return {"status": "error", "message": f"Ошибка при создании дневника: {str(e)}"}


def _write_file_sync(filepath: str, content: str):
    """Synchronous file write helper"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _read_file_sync(filepath: str) -> str:
    """Synchronous file read helper"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


async def add_diary_entry(text: str) -> Dict[str, Any]:
    """Add entry to diary"""
    try:
        await initialize_diary()

        now = _get_irkutsk_now()
        current_date = now.strftime("%Y-%m-%d")
        entry = f"\n## {current_date}\n{text}\n"

        await asyncio.to_thread(_append_file_sync, DIARY_FILE, entry)

        return {
            "status": "success",
            "message": f"Запись добавлена за {current_date}",
            "date": current_date,
        }
    except Exception as e:
        return {"status": "error", "message": f"Ошибка при добавлении записи: {str(e)}"}


def _append_file_sync(filepath: str, content: str):
    """Synchronous file append helper"""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(content)


async def read_diary(date: Optional[str] = None) -> str:
    """Read diary entries, optionally filtered by date"""
    try:
        if not os.path.exists(DIARY_FILE):
            return "Дневник пуст. Используйте initialize_diary() для создания."

        content = await asyncio.to_thread(_read_file_sync, DIARY_FILE)

        if date:
            lines = content.split("\n")
            filtered = []
            capture = False
            for line in lines:
                if line.startswith(f"## {date}"):
                    capture = True
                    filtered.append(line)
                elif line.startswith("## ") and capture:
                    break
                elif capture:
                    filtered.append(line)
            return "\n".join(filtered) if filtered else f"Записей за {date} не найдено"

        # Return last 2000 chars if too long
        if len(content) > 2000:
            return content[-2000:] + "\n...(показано последние 2000 символов)"
        return content
    except Exception as e:
        return f"Ошибка при чтении дневника: {str(e)}"


async def get_diary_stats() -> Dict[str, Any]:
    """Get diary statistics"""
    try:
        if not os.path.exists(DIARY_FILE):
            return {"exists": False, "message": "Файл дневника не найден"}

        content = await asyncio.to_thread(_read_file_sync, DIARY_FILE)
        dates = [
            line[3:].strip() for line in content.split("\n") if line.startswith("## ")
        ]

        return {
            "exists": True,
            "file_size": os.path.getsize(DIARY_FILE),
            "entry_count": len(dates),
            "last_entry": dates[-1] if dates else "нет записей",
        }
    except Exception as e:
        return {"exists": False, "error": str(e)}


# ==================== SCHEDULE FUNCTIONS ====================


async def get_current_week_type() -> str:
    """Get current week type (числитель/знаменатель)"""
    try:
        _ensure_data_dir()
        if os.path.exists(SCHEDULE_FILE):
            content = await asyncio.to_thread(_read_file_sync, SCHEDULE_FILE)
            data = json.loads(content)
            return data.get("current_week_type", "числитель")
        return "числитель"
    except Exception:
        return "числитель"


async def set_week_type(week_type: str) -> str:
    """Set week type"""
    try:
        _ensure_data_dir()
        data = {"current_week_type": week_type}
        await asyncio.to_thread(
            _write_file_sync,
            SCHEDULE_FILE,
            json.dumps(data, ensure_ascii=False, indent=2),
        )
        return f"Установлена неделя: {week_type}"
    except Exception as e:
        return f"Ошибка: {str(e)}"


def _get_day_of_week_ru(dt: datetime.datetime) -> str:
    """Get Russian day of week abbreviation"""
    days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    return days[dt.weekday()]


async def get_today_schedule() -> Dict[str, Any]:
    """Get schedule for today"""
    try:
        now = _get_irkutsk_now()
        week_type = await get_current_week_type()
        day = _get_day_of_week_ru(now)

        if day == "ВС":
            return {
                "day": day,
                "week_type": week_type,
                "lessons": [],
                "message": "Сегодня воскресенье - выходной!",
            }

        schedule = BASE_SCHEDULE.get(week_type, {}).get(day, [])
        lessons = [l for l in schedule if l.get("subject", "").strip()]

        return {
            "day": day,
            "week_type": week_type,
            "lessons": lessons,
            "count": len(lessons),
        }
    except Exception as e:
        return {"error": str(e)}


async def get_tomorrow_schedule() -> Dict[str, Any]:
    """Get schedule for tomorrow"""
    try:
        now = _get_irkutsk_now()
        tomorrow = now + datetime.timedelta(days=1)
        week_type = await get_current_week_type()
        day = _get_day_of_week_ru(tomorrow)

        if day == "ВС":
            return {
                "day": day,
                "week_type": week_type,
                "lessons": [],
                "message": "Завтра воскресенье - выходной!",
            }

        schedule = BASE_SCHEDULE.get(week_type, {}).get(day, [])
        lessons = [l for l in schedule if l.get("subject", "").strip()]

        return {
            "day": day,
            "week_type": week_type,
            "lessons": lessons,
            "count": len(lessons),
        }
    except Exception as e:
        return {"error": str(e)}


def format_schedule_message(
    schedule_data: Dict[str, Any], title: str = "Расписание"
) -> str:
    """Format schedule data to readable message"""
    if not schedule_data.get("lessons"):
        return f"{title}: {schedule_data.get('message', 'Нет пар')}"

    lines = [f"📚 {title} ({schedule_data['week_type']}, {schedule_data['day']}):"]
    for i, lesson in enumerate(schedule_data["lessons"], 1):
        subject = lesson["subject"]
        time = lesson["time"]
        room = lesson.get("room", "")
        room_text = f" ({room})" if room else ""
        lines.append(f"{i}. {time} - {subject}{room_text}")

    lines.append(f"\nВсего пар: {schedule_data['count']}")
    return "\n".join(lines)


# ==================== REMINDER STATUS FUNCTIONS ====================


async def check_diary_reminder_status() -> Dict[str, Any]:
    """Check diary reminder status"""
    now = _get_irkutsk_now()
    current_hour, current_minute = now.hour, now.minute
    reminder_hour, reminder_minute = 20, 0

    if current_hour < reminder_hour or (
        current_hour == reminder_hour and current_minute < reminder_minute
    ):
        time_diff = (reminder_hour * 60 + reminder_minute) - (
            current_hour * 60 + current_minute
        )
        hours, minutes = time_diff // 60, time_diff % 60
        time_str = (
            f"через {hours} ч {minutes} мин" if hours > 0 else f"через {minutes} мин"
        )
    else:
        time_diff = (
            (24 * 60)
            - (current_hour * 60 + current_minute)
            + (reminder_hour * 60 + reminder_minute)
        )
        hours, minutes = time_diff // 60, time_diff % 60
        time_str = f"завтра через {hours} ч {minutes} мин"

    return {
        "reminder_time": "20:00",
        "current_time": now.strftime("%H:%M"),
        "next_reminder_in": time_str,
        "status": "active",
    }


async def get_all_reminders_summary() -> str:
    """Get summary of all reminders"""
    now = _get_irkutsk_now()
    diary_status = await check_diary_reminder_status()
    today_schedule = await get_today_schedule()
    tomorrow_schedule = await get_tomorrow_schedule()
    diary_stats = await get_diary_stats()

    lines = [
        "📋 СВОДКА ПО ВСЕМ НАПОМИНАНИЯМ:",
        f"• Текущее время: {now.strftime('%H:%M')}",
        "",
        "📓 НАПОМИНАНИЕ ДЛЯ ДНЕВНИКА:",
        f"   • Время: {diary_status['reminder_time']}",
        f"   • Следующее: {diary_status['next_reminder_in']}",
        "",
        "📚 НАПОМИНАНИЯ О РАСПИСАНИИ:",
        "   • Вечернее: 20:00 (о парах на завтра)",
        "   • Утренние: 06:00, 07:00, 08:00, 09:00 (о парах на сегодня)",
        "",
        "📅 РАСПИСАНИЕ:",
    ]

    if today_schedule.get("lessons"):
        lines.append(f"   • Сегодня пар: {len(today_schedule['lessons'])}")
        if today_schedule["lessons"]:
            first = today_schedule["lessons"][0]
            lines.append(f"   • Первая пара: {first['time']} - {first['subject']}")
    else:
        lines.append("   • Сегодня пар нет")

    if tomorrow_schedule.get("lessons"):
        lines.append(f"   • Завтра пар: {len(tomorrow_schedule['lessons'])}")
    else:
        lines.append("   • Завтра пар нет")

    lines.append("")
    lines.append("📊 СТАТИСТИКА ДНЕВНИКА:")
    if diary_stats.get("exists"):
        lines.append(f"   • Записей: {diary_stats['entry_count']}")
        lines.append(f"   • Последняя: {diary_stats['last_entry']}")
    else:
        lines.append(f"   • {diary_stats.get('message', 'Нет данных')}")

    return "\n".join(lines)


# ==================== TOOL REGISTRATION ====================


def register_tools(registry):
    """Register all reminder tools"""
    registry.register(
        "initialize_diary", initialize_diary, "Initialize diary file with template"
    )
    registry.register(
        "add_diary_entry", add_diary_entry, "Add entry to diary. Arguments: text (str)"
    )
    registry.register(
        "read_diary", read_diary, "Read diary entries. Arguments: date (str, optional)"
    )
    registry.register("get_diary_stats", get_diary_stats, "Get diary statistics")
    registry.register(
        "get_today_schedule", get_today_schedule, "Get today's class schedule"
    )
    registry.register(
        "get_tomorrow_schedule", get_tomorrow_schedule, "Get tomorrow's class schedule"
    )
    registry.register(
        "set_week_type",
        set_week_type,
        "Set week type (числитель/знаменатель). Arguments: week_type (str)",
    )
    registry.register(
        "get_current_week_type", get_current_week_type, "Get current week type"
    )
    registry.register(
        "check_diary_reminder_status",
        check_diary_reminder_status,
        "Check diary reminder status",
    )
    registry.register(
        "get_all_reminders_summary",
        get_all_reminders_summary,
        "Get summary of all reminders",
    )
