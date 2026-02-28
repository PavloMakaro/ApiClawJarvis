#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fpdf import FPDF
import os
from datetime import datetime

# Настройка шрифтов для поддержки кириллицы
class PDFArticle(FPDF):
    def __init__(self):
        super().__init__()
        # Добавляем поддержку кириллицы
        self.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        self.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
        self.add_font('DejaVu', 'I', 'DejaVuSans-Oblique.ttf', uni=True)

    def header(self):
        # Логотип (проверяем наличие файла)
        logo_path = '../downloads/images/5193621219/video_game_east_0.jpg'
        if os.path.exists(logo_path):
            try:
                self.image(logo_path, 10, 8, 33)
            except:
                pass  # Пропускаем если не удалось загрузить изображение

        # Шрифт
        self.set_font('DejaVu', 'B', 15)
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
        self.set_font('DejaVu', 'I', 8)
        # Номер страницы
        self.cell(0, 10, f'Страница {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        # Шрифт
        self.set_font('DejaVu', 'B', 12)
        # Цвет фона
        self.set_fill_color(200, 220, 255)
        # Заголовок главы
        self.cell(0, 6, title, 0, 1, 'L', 1)
        # Перенос строки
        self.ln(4)

    def chapter_body(self, body):
        # Шрифт
        self.set_font('DejaVu', '', 11)
        # Вывод текста
        self.multi_cell(0, 5, body)
        # Перенос строки
        self.ln()

    def add_image(self, image_path, caption=None):
        # Проверяем наличие файла
        if not os.path.exists(image_path):
            return

        try:
            # Добавление изображения
            self.image(image_path, x=10, w=190)
            if caption:
                self.set_font('DejaVu', 'I', 9)
                self.cell(0, 5, caption, 0, 1, 'C')
                self.ln(5)
        except:
            pass  # Пропускаем если не удалось загрузить изображение

def create_simple_pdf():
    """Создаём упрощённый PDF без сложного форматирования"""

    # Чтение статьи
    with open('статья_пасхалки.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # Создаём PDF
    pdf = FPDF()
    pdf.add_page()

    # Устанавливаем шрифт по умолчанию (без кириллицы, но с базовой поддержкой)
    pdf.set_font("Arial", size=12)

    # Заголовок
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="ТАЙНЫЕ СОКРОВИЩА ГЕЙМИНГА", ln=1, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="История и лучшие пасхалки в видеоиграх", ln=1, align='C')
    pdf.ln(10)

    # Автор и дата
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 5, txt=f"Автор: Джарвис AI | Дата: {datetime.now().strftime('%d.%m.%Y')}", ln=1, align='C')
    pdf.ln(10)

    # Разделяем контент на абзацы
    paragraphs = content.split('\n\n')

    # Добавляем контент
    pdf.set_font("Arial", size=11)

    for para in paragraphs:
        if not para.strip():
            continue

        # Убираем заголовки маркдауна
        clean_para = para.replace('# ', '').replace('## ', '').replace('### ', '').strip()

        if clean_para:
            # Для длинных параграфов используем multi_cell
            if len(clean_para) > 100:
                pdf.multi_cell(0, 5, txt=clean_para)
                pdf.ln(5)
            else:
                pdf.cell(0, 5, txt=clean_para, ln=1)

    # Добавляем информацию об источниках
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="ИСТОЧНИКИ И РЕСУРСЫ", ln=1, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", size=11)
    sources = [
        "1. Pashalki.ru - Что такое пасхалка?",
        "2. Knife.media - Сахарок для своих: история пасхалок",
        "3. Playground.ru - Отсылка, пасхалка и заимствование",
        "4. Championat.com - Лучшие пасхалки в играх",
        "5. Gamer.ru - Пасхалки и интересности",
        "6. Eeggs.com - Video Game Easter Eggs",
        "7. GTA Wiki - Secrets and Easter Eggs in GTA V"
    ]

    for source in sources:
        pdf.cell(0, 5, txt=source, ln=1)

    # Сохраняем PDF
    output_path = 'пасхалки_в_играх.pdf'
    pdf.output(output_path)

    return output_path

if __name__ == '__main__':
    try:
        pdf_path = create_simple_pdf()
        print(f'PDF успешно создан: {pdf_path}')

        # Проверяем размер файла
        if os.path.exists(pdf_path):
            size = os.path.getsize(pdf_path)
            print(f'Размер файла: {size} байт')
    except Exception as e:
        print(f'Ошибка при создании PDF: {e}')