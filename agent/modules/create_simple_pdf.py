#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def create_pdf():
    # Регистрируем шрифт с поддержкой кириллицы
    try:
        # Пробуем использовать стандартный шрифт
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase import pdfmetrics

        # Используем стандартный шрифт ReportLab
        from reportlab.lib.fonts import addMapping
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        from reportlab.lib import colors
    except:
        pass

    # Чтение статьи
    with open('статья_пасхалки.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # Создаём PDF
    output_path = 'пасхалки_в_видеоиграх.pdf'
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    # Текущая позиция Y
    y_position = height - 50

    # Заголовок
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, y_position, "ТАЙНЫЕ СОКРОВИЩА ГЕЙМИНГА")
    y_position -= 25

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, y_position, "История и лучшие пасхалки в видеоиграх")
    y_position -= 30

    # Автор и дата
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width/2, y_position, f"Автор: Джарвис AI | Дата: {datetime.now().strftime('%d.%m.%Y')}")
    y_position -= 40

    # Разделяем контент
    paragraphs = content.split('\n\n')

    # Основной текст
    c.setFont("Helvetica", 11)

    page_num = 1

    for para in paragraphs:
        if not para.strip():
            continue

        # Очищаем текст от маркдауна
        clean_text = para.replace('# ', '').replace('## ', '').replace('### ', '').replace('*', '').strip()

        if not clean_text:
            continue

        # Разбиваем длинные строки
        words = clean_text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            line_text = ' '.join(current_line)

            # Проверяем длину строки
            if c.stringWidth(line_text, "Helvetica", 11) > width - 100:
                # Сохраняем предыдущую строку
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]

        # Добавляем последнюю строку
        if current_line:
            lines.append(' '.join(current_line))

        # Выводим строки
        for line in lines:
            if y_position < 50:  # Конец страницы
                c.showPage()
                page_num += 1
                y_position = height - 50
                c.setFont("Helvetica", 11)

            c.drawString(50, y_position, line[:100])  # Ограничиваем длину строки
            y_position -= 15

        y_position -= 5  # Отступ между параграфами

    # Номер страницы на каждой странице
    c.setFont("Helvetica", 8)
    for i in range(1, page_num + 1):
        c.drawRightString(width - 50, 30, f"Страница {i}")
        if i < page_num:
            c.showPage()

    # Сохраняем PDF
    c.save()

    return output_path

if __name__ == '__main__':
    try:
        pdf_path = create_pdf()
        print(f'PDF создан: {pdf_path}')

        if os.path.exists(pdf_path):
            size = os.path.getsize(pdf_path)
            print(f'Размер файла: {size} байт')
    except Exception as e:
        print(f'Ошибка: {e}')

        # Создаём самый простой текстовый файл как запасной вариант
        with open('пасхалки_статья.txt', 'w', encoding='utf-8') as f:
            f.write("ТАЙНЫЕ СОКРОВИЩА ГЕЙМИНГА\n")
            f.write("История и лучшие пасхалки в видеоиграх\n\n")

            with open('статья_пасхалки.md', 'r', encoding='utf-8') as src:
                f.write(src.read())

        print('Создан текстовый файл: пасхалки_статья.txt')