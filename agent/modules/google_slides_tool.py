import os
import sys
import pickle
from pathlib import Path

# Add modules to path
sys.path.append(str(Path(__file__).parent))

try:
    from google_slides_auth import get_google_slides_service, create_presentation, add_slide
    GOOGLE_SLIDES_AVAILABLE = True
except ImportError as e:
    GOOGLE_SLIDES_AVAILABLE = False
    print(f"Google Slides not available: {e}")

def google_slides_auth():
    """Authenticate with Google Slides API."""
    if not GOOGLE_SLIDES_AVAILABLE:
        return "Google Slides API not configured. Please install required packages."

    try:
        service = get_google_slides_service()
        return "✅ Google Slides API успешно авторизован! Теперь можно создавать презентации."
    except Exception as e:
        return f"❌ Ошибка авторизации: {str(e)}"

def google_slides_create(title="Моя презентация", slides=None):
    """Create Google Slides presentation."""
    if not GOOGLE_SLIDES_AVAILABLE:
        return "Google Slides API not configured."

    try:
        presentation_id = create_presentation(title)

        # Add slides if provided
        if slides:
            for i, slide_data in enumerate(slides):
                slide_title = slide_data.get('title', f'Слайд {i+1}')
                slide_content = slide_data.get('content', '')
                add_slide(presentation_id, slide_title, slide_content)

        url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
        return f"✅ Презентация создана!\nСсылка: {url}\nID: {presentation_id}"

    except Exception as e:
        return f"❌ Ошибка создания презентации: {str(e)}"

def google_slides_quick_presentation():
    """Create a quick test presentation."""
    slides = [
        {'title': 'Титульный слайд', 'content': 'Моя первая презентация\nСоздано с помощью Jarvis AI'},
        {'title': 'Введение', 'content': '• Тема презентации\n• Цели и задачи\n• Актуальность'},
        {'title': 'Основная часть', 'content': '• Ключевые моменты\n• Примеры\n• Данные и факты'},
        {'title': 'Заключение', 'content': '• Выводы\n• Рекомендации\n• Перспективы'},
        {'title': 'Спасибо!', 'content': 'Вопросы?'}
    ]

    return google_slides_create("Тестовая презентация от Jarvis", slides)

if __name__ == '__main__':
    # Test
    print(google_slides_auth())
    print(google_slides_quick_presentation())