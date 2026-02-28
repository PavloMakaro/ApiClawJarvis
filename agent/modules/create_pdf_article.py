#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fpdf import FPDF
import os
from datetime import datetime

class PDFArticle(FPDF):
    def header(self):
        # Логотип
        self.image('downloads/images/5193621219/video_game_east_0.jpg', 10, 8, 33)
        # Шрифт
        self.set_font('Arial', 'B', 15)
        # Перемещение вправо
        self.cell(80)
        # Заголовок
        self.cell(30, 10, 'Тайные сокровища гейминга', 0, 0, 'C')
        # Перенос строки
        self.ln(20)

    def footer(self):
        # Позиция в 1.5 см от нижнего края
        self.set_y(-15)
        # Шрифт
        self.set_font('Arial', 'I', 8)
        # Номер страницы
        self.cell(0, 10, f'Страница {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        # Шрифт
        self.set_font('Arial', 'B', 12)
        # Цвет фона
        self.set_fill_color(200, 220, 255)
        # Заголовок главы
        self.cell(0, 6, title, 0, 1, 'L', 1)
        # Перенос строки
        self.ln(4)

    def chapter_body(self, body):
        # Шрифт
        self.set_font('Arial', '', 11)
        # Вывод текста
        self.multi_cell(0, 5, body)
        # Перенос строки
        self.ln()

    def add_image(self, image_path, caption=None):
        # Добавление изображения
        self.image(image_path, x=10, w=190)
        if caption:
            self.set_font('Arial', 'I', 9)
            self.cell(0, 5, caption, 0, 1, 'C')
            self.ln(5)

def create_pdf_article():
    # Чтение статьи
    with open('статья_пасхалки.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # Разделение на секции
    sections = content.split('## ')
    intro = sections[0].replace('# ', '')
    main_sections = sections[1:]

    # Создание PDF
    pdf = PDFArticle()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Заголовок
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Тайные сокровища гейминга:', 0, 1, 'C')
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'История и лучшие пасхалки в видеоиграх', 0, 1, 'C')
    pdf.ln(10)

    # Автор и дата
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(0, 5, f'Автор: Джарвис AI | Дата: {datetime.now().strftime("%d.%m.%Y")}', 0, 1, 'C')
    pdf.ln(15)

    # Введение
    pdf.set_font('Arial', '', 11)
    intro_lines = intro.strip().split('\n')
    for line in intro_lines:
        if line.strip():
            pdf.multi_cell(0, 5, line.strip())
    pdf.ln(10)

    # Добавление изображения
    if os.path.exists('downloads/images/5193621219/video_game_east_1.jpg'):
        pdf.add_image('downloads/images/5193621219/video_game_east_1.jpg', 'Пример пасхалки в видеоигре')

    # Основные разделы
    for i, section in enumerate(main_sections):
        if not section.strip():
            continue

        # Разделение заголовка и содержимого
        lines = section.split('\n', 1)
        if len(lines) < 2:
            continue

        title = lines[0].strip()
        body = lines[1].strip()

        # Добавление новой страницы для каждого второго раздела
        if i > 0 and i % 2 == 0:
            pdf.add_page()

        # Заголовок раздела
        pdf.chapter_title(title)

        # Содержимое
        pdf.chapter_body(body)

        # Добавление изображений через каждые 2 раздела
        if i % 2 == 0 and i < 4:
            img_index = i + 2  # Начинаем с третьего изображения
            img_path = f'downloads/images/5193621219/video_game_east_{img_index}.jpg'
            if os.path.exists(img_path):
                pdf.add_image(img_path, f'Иллюстрация: {title}')

    # Заключительная страница
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Заключение', 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font('Arial', '', 11)
    conclusion = """Пасхалки в видеоиграх — это уникальное явление, объединяющее разработчиков и игроков.
Они превращают игровой процесс в настоящее приключение, где каждый уголок может скрывать сюрприз.

От первой пасхалки в 1977 году до современных сложных секретов — эти скрытые жемчужины продолжают
радовать и удивлять геймеров по всему миру.

Ищите, исследуйте и находите — ведь настоящая магия игр часто прячется там, где её меньше всего ждут."""

    pdf.multi_cell(0, 5, conclusion)
    pdf.ln(10)

    # Последнее изображение
    if os.path.exists('downloads/images/5193621219/video_game_east_4.jpg'):
        pdf.add_image('downloads/images/5193621219/video_game_east_4.jpg', 'Мир игровых секретов ждёт своих исследователей')

    # Сохранение PDF
    output_path = 'пасхалки_в_играх_статья.pdf'
    pdf.output(output_path)

    return output_path

if __name__ == '__main__':
    pdf_path = create_pdf_article()
    print(f'PDF создан: {pdf_path}')