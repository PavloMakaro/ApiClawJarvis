import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

BASE_URL = "https://kudikina.ru/irk"


def get_bus_schedule(bus_number: str, direction: str = "A") -> dict:
    """
    Парсит расписание автобуса с kudikina.ru

    Args:
        bus_number: номер автобуса (например "55")
        direction: направление A или B (по умолчанию A)

    Returns:
        dict с расписанием или сообщением об ошибке
    """
    url = f"{BASE_URL}/bus/{bus_number}/{direction}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")

        title_elem = soup.find("h1")
        bus_name = (
            title_elem.get_text(strip=True) if title_elem else f"Автобус {bus_number}"
        )

        schedule_data = {
            "bus_number": bus_number,
            "name": bus_name,
            "direction": direction,
            "stops": [],
            "last_updated": datetime.now().strftime("%H:%M %d.%m.%Y"),
        }

        rows = soup.find_all("div", class_="row")
        seen_stops = set()

        for row in rows:
            bus_stop = row.find("div", class_="bus-stop")
            if not bus_stop:
                continue

            stop_name_elem = bus_stop.find("a")
            if not stop_name_elem:
                continue

            stop_name = stop_name_elem.get_text(strip=True)

            if stop_name in seen_stops:
                continue
            seen_stops.add(stop_name)

            right_col = row.find("div", class_="text-right")
            times_container = None
            if right_col:
                times_container = right_col.find("div", class_="stop-times")

            times = []
            if times_container:
                time_spans = times_container.find_all("span")
                for span in time_spans:
                    time_text = span.get_text(strip=True)
                    if re.match(r"\d{2}:\d{2}", time_text):
                        times.append(time_text)

            schedule_data["stops"].append(
                {"name": stop_name, "times": times[:10], "interval": ""}
            )

        return schedule_data

    except requests.RequestException as e:
        return {"error": f"Ошибка сети: {str(e)}"}
    except Exception as e:
        return {"error": f"Ошибка парсинга: {str(e)}"}


def get_stop_schedule(stop_name: str) -> dict:
    """
    Парсит расписание для конкретной остановки

    Args:
        stop_name: название остановки

    Returns:
        dict с расписанием для остановки
    """
    url = f"{BASE_URL}/search"
    params = {"a": stop_name}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        routes = soup.find_all("div", class_="route")

        for route in routes[:10]:
            route_name_elem = route.find("span", class_="name")
            if route_name_elem:
                route_name = route_name_elem.get_text(strip=True)

                times_elem = route.find("div", class_="times")
                times = []
                if times_elem:
                    time_spans = times_elem.find_all("span")
                    for span in time_spans:
                        time_text = span.get_text(strip=True)
                        if re.match(r"\d{2}:\d{2}", time_text):
                            times.append(time_text)

                direction_elem = route.find("div", class_="direction")
                direction = (
                    direction_elem.get_text(strip=True) if direction_elem else ""
                )

                results.append(
                    {"route": route_name, "direction": direction, "times": times[:6]}
                )

        return {
            "stop": stop_name,
            "routes": results,
            "last_updated": datetime.now().strftime("%H:%M %d.%m.%Y"),
        }

    except requests.RequestException as e:
        return {"error": f"Ошибка сети: {str(e)}"}
    except Exception as e:
        return {"error": f"Ошибка парсинга: {str(e)}"}


def format_bus_schedule(schedule: dict) -> str:
    """Форматирует расписание автобуса для вывода"""
    if "error" in schedule:
        return f"❌ {schedule['error']}"

    result = f"🚌 **Автобус №{schedule['bus_number']}** — {schedule['name']}\n"
    result += f"Обновлено: {schedule['last_updated']}\n\n"

    if not schedule["stops"]:
        return result + "Не удалось загрузить расписание"

    result += "**Остановки и время прибытия:**\n"

    for i, stop in enumerate(schedule["stops"][:8]):
        result += f"\n{i + 1}. **{stop['name']}**\n"
        if stop["times"]:
            times_str = " | ".join(stop["times"])
            result += f"   Время: {times_str}\n"
        elif stop["interval"]:
            result += f"   {stop['interval']}\n"

    if len(schedule["stops"]) > 8:
        result += f"\n... и ещё {len(schedule['stops']) - 8} остановок"

    return result


def format_stop_schedule(schedule: dict) -> str:
    """Форматирует расписание для остановки"""
    if "error" in schedule:
        return f"❌ {schedule['error']}"

    result = f"🚏 **Остановка: {schedule['stop']}**\n"
    result += f"Обновлено: {schedule['last_updated']}\n\n"

    if not schedule["routes"]:
        return result + "Маршруты не найдены"

    result += "**Маршруты:**\n"

    for route in schedule["routes"]:
        result += f"\n🚌 {route['route']}\n"
        result += f"   Направление: {route['direction']}\n"
        if route["times"]:
            times_str = " | ".join(route["times"])
            result += f"   Время: {times_str}\n"

    return result


def get_6_microdistrict_schedule() -> str:
    """
    Получает расписание для 6-го микрорайона Ново-Ленино
    Основные автобусы: 10, 13, 14, 42, 55
    """
    buses = [
        ("55", "A", "6-й микрорайон → Областная больница"),
        ("55", "B", "Областная больница → 6-й микрорайон"),
        ("10", "A", "Завод нерудных материалов → Берёзовый (через 6-й мкр)"),
        ("14", "A", "Кольцевой через 6-й микрорайон"),
        ("42", "A", "Аэропорт → 6-й микрорайон"),
        ("42", "B", "6-й микрорайон → Аэропорт"),
    ]

    result = "🚏 **Расписание для 6-го микрорайона Ново-Ленино**\n"
    result += f"Обновлено: {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"

    for bus_num, direction, desc in buses:
        schedule = get_bus_schedule(bus_num, direction)

        result += f"\n--- 🚌 Автобус №{bus_num} ---\n"
        result += f"{desc}\n"

        if "error" in schedule:
            result += f"❌ Ошибка: {schedule['error']}\n"
            continue

        for i, stop in enumerate(schedule["stops"][:5]):
            if stop["times"]:
                times_str = " | ".join(stop["times"][:4])
                result += f"  {i + 1}. {stop['name']}: {times_str}\n"

        if len(schedule["stops"]) > 5:
            result += f"  ... всего остановок: {len(schedule['stops'])}\n"

    return result


def register_tools(registry):
    """Регистрирует инструменты для работы с транспортом Иркутска"""
    registry.register(
        "irkutsk_bus_schedule",
        get_bus_schedule,
        "Получить расписание автобуса в Иркутске. Аргументы: bus_number (номер автобуса, например 55), direction (A или B).",
    )
    registry.register(
        "irkutsk_stop_schedule",
        get_stop_schedule,
        "Получить расписание для остановки в Иркутске. Аргумент: stop_name (название остановки, например '6-й микрорайон').",
    )
    registry.register(
        "irkutsk_6_microdistrict",
        get_6_microdistrict_schedule,
        "Получить расписание автобусов для 6-го микрорайона Ново-Ленино в Иркутске (основные маршруты: 10, 14, 42, 55).",
    )
