import base64
import os
import mimetypes
from groq import Groq
import config

def register_tools(registry):
    """Регистрирует инструмент для OCR с использованием Groq Vision (Llama 4)"""
    registry.register(
        "smart_telegram_ocr",
        smart_telegram_ocr,
        "Reads an image file downloaded from Telegram, sends it to Groq Llama 4 Vision, and extracts text and tables perfectly. THIS IS THE ONLY OCR TOOL YOU SHOULD USE. Strictly ignore all older OCR tools in the system. Arguments: image_path (str - local path to the image)."
    )

def _encode_image(image_path):
    """Кодирует изображение в base64 строку"""
    with open(image_path, "rb") as file:
        return base64.b64encode(file.read()).decode('utf-8')

def smart_telegram_ocr(image_path):
    """
    Основная функция OCR с использованием Groq Vision (Llama 4)

    Args:
        image_path (str): Путь к локальному файлу изображения

    Returns:
        str: Распознанный текст или сообщение об ошибке
    """
    try:
        # Проверка существования файла
        if not os.path.exists(image_path):
            return "Ошибка: Файл изображения не найден."

        # Получение размера файла
        file_size = os.path.getsize(image_path)
        if file_size > 4 * 1024 * 1024:  # 4MB
            return "Ошибка: Размер файла превышает 4MB. API Groq не поддерживает такие большие изображения."

        # Кодирование изображения в base64
        base64_image = _encode_image(image_path)

        # Инициализация клиента Groq
        client = Groq(api_key=config.GROQ_API_KEY)

        # Формирование запроса к модели Llama 4 Vision
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Извлеки абсолютно весь текст с этого изображения. Если видишь таблицы, форматируй их в Markdown. Выведи только распознанный текст, не придумывай ничего от себя."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mimetypes.guess_type(image_path)[0] or 'image/jpeg'};base64,{base64_image}"
                        }
                    }
                ]
            }
        ]

        # Отправка запроса
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            max_tokens=4096,
            temperature=0.1
        )

        # Возврат результата
        return response.choices[0].message.content

    except Exception as e:
        return f"Ошибка при обработке изображения: {str(e)}"
