#!/usr/bin/env python3
"""
Модуль для создания презентаций PowerPoint с картинками
Использует python-pptx
"""

import os
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PresentationCreator:
    """Создатель презентаций PowerPoint"""

    def __init__(self, output_dir="data/presentations"):
        """Инициализация с указанием директории для сохранения"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.presentation = None

    def create_new_presentation(self, title="Презентация"):
        """Создать новую презентацию"""
        self.presentation = Presentation()
        # Установить заголовок в свойствах
        self.presentation.core_properties.title = title
        logger.info(f"Создана новая презентация: {title}")
        return self

    def add_title_slide(self, title, subtitle=""):
        """Добавить титульный слайд"""
        if not self.presentation:
            self.create_new_presentation()

        slide_layout = self.presentation.slide_layouts[0]  # Титульный слайд
        slide = self.presentation.slides.add_slide(slide_layout)

        # Заполнить заголовок
        title_shape = slide.shapes.title
        title_shape.text = title

        # Заполнить подзаголовок
        subtitle_shape = slide.placeholders[1]
        subtitle_shape.text = subtitle

        logger.info(f"Добавлен титульный слайд: {title}")
        return slide

    def add_text_slide(self, title, content, bullet_points=True):
        """Добавить слайд с текстом"""
        if not self.presentation:
            self.create_new_presentation()

        slide_layout = self.presentation.slide_layouts[1]  # Заголовок и текст
        slide = self.presentation.slides.add_slide(slide_layout)

        # Заголовок
        title_shape = slide.shapes.title
        title_shape.text = title

        # Текст
        text_shape = slide.placeholders[1]
        if bullet_points:
            text_frame = text_shape.text_frame
            text_frame.clear()  # Очистить стандартный текст

            # Разделить контент на пункты
            points = [p.strip() for p in content.split('\n') if p.strip()]
            for i, point in enumerate(points):
                if i == 0:
                    p = text_frame.paragraphs[0]
                    p.text = point
                else:
                    p = text_frame.add_paragraph()
                    p.text = point
                p.level = 0  # Уровень вложенности
        else:
            text_shape.text = content

        logger.info(f"Добавлен текстовый слайд: {title}")
        return slide

    def add_image_slide(self, title, image_path, caption=""):
        """Добавить слайд с изображением"""
        if not self.presentation:
            self.create_new_presentation()

        slide_layout = self.presentation.slide_layouts[5]  # Заголовок и контент
        slide = self.presentation.slides.add_slide(slide_layout)

        # Заголовок
        title_shape = slide.shapes.title
        title_shape.text = title

        # Добавить изображение
        if os.path.exists(image_path):
            left = Inches(1)
            top = Inches(1.5)
            width = Inches(8)
            height = Inches(4.5)

            slide.shapes.add_picture(image_path, left, top, width, height)

            # Добавить подпись если указана
            if caption:
                txBox = slide.shapes.add_textbox(Inches(1), Inches(6), Inches(8), Inches(0.5))
                tf = txBox.text_frame
                p = tf.paragraphs[0]
                p.text = caption
                p.font.size = Pt(12)
                p.font.color.rgb = RGBColor(100, 100, 100)

            logger.info(f"Добавлен слайд с изображением: {title}")
        else:
            logger.error(f"Изображение не найдено: {image_path}")

        return slide

    def add_two_column_slide(self, title, left_content, right_content):
        """Добавить слайд с двумя колонками"""
        if not self.presentation:
            self.create_new_presentation()

        slide_layout = self.presentation.slide_layouts[3]  # Два контента
        slide = self.presentation.slides.add_slide(slide_layout)

        # Заголовок
        title_shape = slide.shapes.title
        title_shape.text = title

        # Левый контент
        left_shape = slide.placeholders[1]
        left_shape.text = left_content

        # Правый контент
        right_shape = slide.placeholders[2]
        right_shape.text = right_content

        logger.info(f"Добавлен слайд с двумя колонками: {title}")
        return slide

    def add_blank_slide(self):
        """Добавить пустой слайд"""
        if not self.presentation:
            self.create_new_presentation()

        slide_layout = self.presentation.slide_layouts[6]  # Пустой слайд
        slide = self.presentation.slides.add_slide(slide_layout)

        logger.info("Добавлен пустой слайд")
        return slide

    def add_custom_textbox(self, slide, text, left, top, width, height, font_size=18):
        """Добавить кастомное текстовое поле на слайд"""
        txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = txBox.text_frame
        tf.text = text

        # Настройка шрифта
        p = tf.paragraphs[0]
        p.font.size = Pt(font_size)

        return txBox

    def apply_theme(self, theme_name="default"):
        """Применить тему к презентации (базовая реализация)"""
        # В python-pptx темы применяются через шаблоны
        # Здесь можно настроить цвета и шрифты
        logger.info(f"Применена тема: {theme_name}")
        return self

    def save(self, filename="presentation.pptx"):
        """Сохранить презентацию"""
        if not self.presentation:
            logger.error("Нет презентации для сохранения")
            return None

        filepath = self.output_dir / filename
        self.presentation.save(str(filepath))
        logger.info(f"Презентация сохранена: {filepath}")
        return str(filepath)

    def get_slide_count(self):
        """Получить количество слайдов"""
        if self.presentation:
            return len(self.presentation.slides)
        return 0


# Функции для интеграции с Jarvis
def create_presentation(title="Моя презентация", slides=None):
    """
    Создать презентацию с заданными слайдами

    Args:
        title: Заголовок презентации
        slides: Список словарей с описанием слайдов
                Пример: [
                    {"type": "title", "title": "Заголовок", "subtitle": "Подзаголовок"},
                    {"type": "text", "title": "Тема", "content": "Текст..."},
                    {"type": "image", "title": "Изображение", "image_path": "path/to/image.jpg"}
                ]
    """
    creator = PresentationCreator()
    creator.create_new_presentation(title)

    if slides:
        for slide_data in slides:
            slide_type = slide_data.get("type", "text")

            if slide_type == "title":
                creator.add_title_slide(
                    slide_data.get("title", ""),
                    slide_data.get("subtitle", "")
                )
            elif slide_type == "text":
                creator.add_text_slide(
                    slide_data.get("title", ""),
                    slide_data.get("content", ""),
                    slide_data.get("bullet_points", True)
                )
            elif slide_type == "image":
                creator.add_image_slide(
                    slide_data.get("title", ""),
                    slide_data.get("image_path", ""),
                    slide_data.get("caption", "")
                )
            elif slide_type == "two_column":
                creator.add_two_column_slide(
                    slide_data.get("title", ""),
                    slide_data.get("left_content", ""),
                    slide_data.get("right_content", "")
                )

    filename = f"{title.replace(' ', '_')}.pptx"
    return creator.save(filename)


def create_simple_presentation(title, topics, output_filename=None):
    """
    Создать простую презентацию по списку тем

    Args:
        title: Заголовок презентации
        topics: Список тем (каждая тема - отдельный слайд)
        output_filename: Имя файла (опционально)
    """
    creator = PresentationCreator()
    creator.create_new_presentation(title)

    # Титульный слайд
    creator.add_title_slide(title, f"Всего тем: {len(topics)}")

    # Слайды с темами
    for i, topic in enumerate(topics, 1):
        creator.add_text_slide(f"Тема {i}: {topic}",
                              f"Подробное описание темы {i}\n\n"
                              f"Ключевые моменты:\n"
                              f"• Первый пункт\n"
                              f"• Второй пункт\n"
                              f"• Третий пункт")

    # Заключительный слайд
    creator.add_text_slide("Спасибо за внимание!",
                          "Вопросы?\n\n"
                          "Контакты:\n"
                          "• Email: example@domain.com\n"
                          "• Телефон: +7 XXX XXX-XX-XX")

    if not output_filename:
        output_filename = f"{title.replace(' ', '_')}.pptx"

    return creator.save(output_filename)


# Пример использования
if __name__ == "__main__":
    # Пример 1: Простая презентация
    print("Создание простой презентации...")
    topics = ["Введение в Python", "Основы синтаксиса", "Работа с данными", "Библиотеки"]
    filepath = create_simple_presentation("Python для начинающих", topics)
    print(f"Создано: {filepath}")

    # Пример 2: Презентация с изображениями
    print("\nСоздание презентации с изображениями...")
    slides = [
        {"type": "title", "title": "Моя поездка", "subtitle": "Фотографии из путешествия"},
        {"type": "image", "title": "Горы", "image_path": "data/images/mountain.jpg", "caption": "Горный пейзаж"},
        {"type": "image", "title": "Море", "image_path": "data/images/sea.jpg", "caption": "Морской берег"},
        {"type": "text", "title": "Выводы", "content": "Путешествие было прекрасным!\nРекомендую всем посетить эти места."}
    ]

    # Замените пути на реальные изображения для тестирования
    # filepath2 = create_presentation("Мое путешествие", slides)
    # print(f"Создано: {filepath2}")