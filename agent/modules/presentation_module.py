#!/usr/bin/env python3
"""
Модуль презентаций для Jarvis - интерфейсные функции
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
import logging

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импорт основного модуля
try:
    from presentation_tool import PresentationCreator, create_presentation, create_simple_presentation
    PRESENTATION_AVAILABLE = True
except ImportError as e:
    PRESENTATION_AVAILABLE = False
    logging.warning(f"Модуль presentation_tool не найден: {e}")

# Настройка
PRESENTATIONS_DIR = Path("data/presentations")
PRESENTATIONS_DIR.mkdir(parents=True, exist_ok=True)


def presentation_create_simple(title: str, topics: List[str]) -> Optional[str]:
    """
    Создать простую презентацию

    Args:
        title: Заголовок презентации
        topics: Список тем для слайдов

    Returns:
        Путь к созданному файлу или None при ошибке
    """
    if not PRESENTATION_AVAILABLE:
        logging.error("Модуль презентаций недоступен")
        return None

    try:
        filename = f"{title.replace(' ', '_')[:50]}.pptx"
        filepath = create_simple_presentation(title, topics, filename)

        if filepath and os.path.exists(filepath):
            file_size = os.path.getsize(filepath) / 1024  # KB
            logging.info(f"Презентация создана: {filepath} ({file_size:.1f} KB)")
            return filepath
        else:
            logging.error("Не удалось создать презентацию")
            return None

    except Exception as e:
        logging.error(f"Ошибка при создании презентации: {e}")
        return None


def presentation_create_custom(slides: List[Dict]) -> Optional[str]:
    """
    Создать кастомную презентацию

    Args:
        slides: Список слайдов в формате:
                [
                    {"type": "title", "title": "...", "subtitle": "..."},
                    {"type": "text", "title": "...", "content": "..."},
                    {"type": "image", "title": "...", "image_path": "...", "caption": "..."}
                ]

    Returns:
        Путь к созданному файлу
    """
    if not PRESENTATION_AVAILABLE:
        logging.error("Модуль презентаций недоступен")
        return None

    try:
        # Извлечь заголовок из первого слайда
        title = "Презентация"
        if slides and slides[0].get("type") == "title":
            title = slides[0].get("title", "Презентация")

        filepath = create_presentation(title, slides)

        if filepath and os.path.exists(filepath):
            file_size = os.path.getsize(filepath) / 1024  # KB
            logging.info(f"Презентация создана: {filepath} ({file_size:.1f} KB)")
            return filepath
        else:
            logging.error("Не удалось создать презентацию")
            return None

    except Exception as e:
        logging.error(f"Ошибка при создании презентации: {e}")
        return None


def presentation_list() -> List[str]:
    """
    Получить список созданных презентаций

    Returns:
        Список файлов презентаций
    """
    presentations = []

    if PRESENTATIONS_DIR.exists():
        for file in PRESENTATIONS_DIR.glob("*.pptx"):
            file_size = file.stat().st_size / 1024  # KB
            presentations.append(f"{file.name} ({file_size:.1f} KB)")

    return presentations


def presentation_get_template(template_name: str = "default") -> Dict:
    """
    Получить шаблон презентации

    Args:
        template_name: Имя шаблона

    Returns:
        Шаблон в виде списка слайдов
    """
    templates = {
        "default": [
            {"type": "title", "title": "Презентация", "subtitle": "Создано с помощью Jarvis AI"},
            {"type": "text", "title": "Введение", "content": "Цели и задачи презентации"},
            {"type": "text", "title": "Основная часть", "content": "Ключевые моменты и информация"},
            {"type": "text", "title": "Заключение", "content": "Выводы и рекомендации"}
        ],
        "business": [
            {"type": "title", "title": "Бизнес-отчет", "subtitle": "Ежеквартальный отчет"},
            {"type": "text", "title": "Ключевые показатели", "content": "• Выручка\n• Прибыль\n• Рост клиентов"},
            {"type": "two_column", "title": "Анализ рынка",
             "left_content": "Сильные стороны:\n• Качество\n• Бренд\n• Команда",
             "right_content": "Слабые стороны:\n• Конкуренция\n• Затраты\n• Риски"},
            {"type": "text", "title": "Планы на следующий квартал",
             "content": "Основные цели и задачи"}
        ],
        "educational": [
            {"type": "title", "title": "Учебный материал", "subtitle": "Тема занятия"},
            {"type": "text", "title": "Цели обучения", "content": "Что студенты должны узнать"},
            {"type": "text", "title": "Теоретическая часть", "content": "Основные понятия и определения"},
            {"type": "text", "title": "Практическая часть", "content": "Примеры и упражнения"},
            {"type": "text", "title": "Домашнее задание", "content": "Задания для самостоятельной работы"}
        ]
    }

    return templates.get(template_name, templates["default"])


def presentation_help() -> str:
    """
    Получить справку по модулю презентаций

    Returns:
        Текст справки
    """
    help_text = """
📊 МОДУЛЬ ПРЕЗЕНТАЦИЙ JARVIS

Доступные функции:
1. Создание простой презентации по списку тем
2. Создание кастомной презентации со слайдами разных типов
3. Использование готовых шаблонов
4. Просмотр списка созданных презентаций

Типы слайдов:
• title - титульный слайд (title, subtitle)
• text - текстовый слайд (title, content)
• image - слайд с изображением (title, image_path, caption)
• two_column - слайд с двумя колонками (title, left_content, right_content)

Пример использования:
slides = [
    {"type": "title", "title": "Моя презентация", "subtitle": "Введение"},
    {"type": "text", "title": "Тема 1", "content": "Описание темы..."},
    {"type": "image", "title": "Диаграмма", "image_path": "data/chart.png"}
]
"""
    return help_text


# Тестовые функции
def test_presentation_module():
    """Тестирование модуля презентаций"""
    if not PRESENTATION_AVAILABLE:
        print("❌ Модуль презентаций недоступен")
        return False

    try:
        print("🧪 Тестирование модуля презентаций...")

        # Тест 1: Создание простой презентации
        print("1. Создание простой презентации...")
        topics = ["Введение", "Основная часть", "Заключение"]
        filepath = presentation_create_simple("Тестовая презентация", topics)

        if filepath and os.path.exists(filepath):
            print(f"✅ Создано: {filepath}")
        else:
            print("❌ Не удалось создать презентацию")
            return False

        # Тест 2: Просмотр списка
        print("\n2. Список презентаций:")
        presentations = presentation_list()
        for pres in presentations:
            print(f"   • {pres}")

        # Тест 3: Получение шаблона
        print("\n3. Шаблоны:")
        template = presentation_get_template("business")
        print(f"   Шаблон 'business' содержит {len(template)} слайдов")

        print("\n✅ Все тесты пройдены успешно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False


if __name__ == "__main__":
    test_presentation_module()