#!/usr/bin/env python3
"""
Интерфейс презентаций для Jarvis - команды для пользователя
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional

# Импорт модуля презентаций
try:
    from modules.presentation_module import (
        presentation_create_simple,
        presentation_create_custom,
        presentation_list,
        presentation_get_template,
        presentation_help
    )
    PRESENTATION_AVAILABLE = True
except ImportError:
    PRESENTATION_AVAILABLE = False


class PresentationInterface:
    """Интерфейс для работы с презентациями через Jarvis"""

    @staticmethod
    def create_from_text(text: str, title: str = None) -> Optional[str]:
        """
        Создать презентацию из текста

        Args:
            text: Текст для преобразования в слайды
            title: Заголовок презентации (опционально)

        Returns:
            Путь к файлу или None
        """
        if not PRESENTATION_AVAILABLE:
            return "❌ Модуль презентаций недоступен"

        # Простой алгоритм: разбить текст на абзацы
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        if not title and paragraphs:
            title = paragraphs[0][:50] + "..."

        # Создать слайды из абзацев
        slides = []
        if paragraphs:
            slides.append({"type": "title", "title": title or "Презентация",
                          "subtitle": f"Создано из текста, {len(paragraphs)} слайдов"})

            for i, para in enumerate(paragraphs[:10]):  # Максимум 10 слайдов
                slide_title = f"Слайд {i+1}"
                if len(para) > 100:
                    # Взять первые слова как заголовок
                    words = para.split()[:5]
                    slide_title = " ".join(words) + "..."

                slides.append({
                    "type": "text",
                    "title": slide_title,
                    "content": para[:500]  # Ограничить длину
                })

        if len(slides) > 1:
            filepath = presentation_create_custom(slides)
            if filepath:
                return f"✅ Презентация создана: {filepath}\n📊 Слайдов: {len(slides)}"
            else:
                return "❌ Не удалось создать презентацию"
        else:
            return "❌ Недостаточно текста для создания презентации"

    @staticmethod
    def create_from_topics(topics: List[str], title: str = "Презентация") -> str:
        """
        Создать презентацию из списка тем

        Args:
            topics: Список тем
            title: Заголовок презентации

        Returns:
            Результат создания
        """
        if not PRESENTATION_AVAILABLE:
            return "❌ Модуль презентаций недоступен"

        if not topics:
            return "❌ Список тем пуст"

        filepath = presentation_create_simple(title, topics)
        if filepath:
            return f"✅ Презентация создана: {filepath}\n📊 Тем: {len(topics)}"
        else:
            return "❌ Не удалось создать презентацию"

    @staticmethod
    def create_from_template(template_name: str = "default", custom_title: str = None) -> str:
        """
        Создать презентацию из шаблона

        Args:
            template_name: Имя шаблона (default, business, educational)
            custom_title: Кастомный заголовок (опционально)

        Returns:
            Результат создания
        """
        if not PRESENTATION_AVAILABLE:
            return "❌ Модуль презентаций недоступен"

        template = presentation_get_template(template_name)
        if not template:
            return f"❌ Шаблон '{template_name}' не найден"

        # Обновить заголовок если указан
        if custom_title and template and template[0]["type"] == "title":
            template[0]["title"] = custom_title

        filepath = presentation_create_custom(template)
        if filepath:
            return f"✅ Презентация создана из шаблона '{template_name}': {filepath}"
        else:
            return "❌ Не удалось создать презентацию"

    @staticmethod
    def list_presentations() -> str:
        """Показать список презентаций"""
        if not PRESENTATION_AVAILABLE:
            return "❌ Модуль презентаций недоступен"

        presentations = presentation_list()
        if presentations:
            result = "📁 Созданные презентации:\n"
            for i, pres in enumerate(presentations, 1):
                result += f"{i}. {pres}\n"
            return result
        else:
            return "📭 Презентаций пока нет"

    @staticmethod
    def get_help() -> str:
        """Получить справку"""
        if not PRESENTATION_AVAILABLE:
            return "❌ Модуль презентаций недоступен"

        return presentation_help()

    @staticmethod
    def create_custom_presentation(slides_json: str) -> str:
        """
        Создать кастомную презентацию из JSON

        Args:
            slides_json: JSON строка со слайдами

        Returns:
            Результат создания
        """
        if not PRESENTATION_AVAILABLE:
            return "❌ Модуль презентаций недоступен"

        try:
            slides = json.loads(slides_json)
            if not isinstance(slides, list):
                return "❌ Неверный формат: ожидается список слайдов"

            filepath = presentation_create_custom(slides)
            if filepath:
                return f"✅ Кастомная презентация создана: {filepath}"
            else:
                return "❌ Не удалось создать презентацию"

        except json.JSONDecodeError as e:
            return f"❌ Ошибка в JSON: {e}"
        except Exception as e:
            return f"❌ Ошибка: {e}"


# Глобальный экземпляр для использования
presentation = PresentationInterface()


# Функции для прямого вызова из Jarvis
def create_presentation_from_text(text: str, title: str = None) -> str:
    """Создать презентацию из текста (для вызова из Jarvis)"""
    return presentation.create_from_text(text, title)


def create_presentation_from_topics(topics: List[str], title: str = "Презентация") -> str:
    """Создать презентацию из списка тем (для вызова из Jarvis)"""
    return presentation.create_from_topics(topics, title)


def create_presentation_from_template(template_name: str = "default", custom_title: str = None) -> str:
    """Создать презентацию из шаблона (для вызова из Jarvis)"""
    return presentation.create_from_template(template_name, custom_title)


def list_all_presentations() -> str:
    """Показать все презентации (для вызова из Jarvis)"""
    return presentation.list_presentations()


def presentation_guide() -> str:
    """Показать руководство по презентациям (для вызова из Jarvis)"""
    return presentation.get_help()


# Пример использования
if __name__ == "__main__":
    print("🎯 Тестирование интерфейса презентаций...\n")

    # Тест 1: Справка
    print("1. Справка:")
    print(presentation_guide())

    # Тест 2: Создание из тем
    print("\n2. Создание из тем:")
    topics = ["Искусственный интеллект", "Машинное обучение", "Нейронные сети", "Применение ИИ"]
    result = create_presentation_from_topics(topics, "Введение в ИИ")
    print(result)

    # Тест 3: Список
    print("\n3. Список презентаций:")
    print(list_all_presentations())

    # Тест 4: Из шаблона
    print("\n4. Создание из шаблона:")
    result = create_presentation_from_template("business", "Мой бизнес-план")
    print(result)

    print("\n✅ Тестирование завершено!")