import requests
import os
from pathlib import Path

def download_torrent(url, filename=None):
    """
    Скачивает торрент-файл по URL

    Args:
        url (str): URL торрент-файла
        filename (str, optional): Имя файла для сохранения

    Returns:
        dict: Результат операции
    """
    try:
        # Создаем папку для загрузок
        download_dir = Path('downloads/torrents')
        download_dir.mkdir(parents=True, exist_ok=True)

        # Определяем имя файла
        if not filename:
            filename = url.split('/')[-1]
            if not filename.endswith('.torrent'):
                filename = 'game.torrent'

        filepath = download_dir / filename

        # Скачиваем файл
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        # Сохраняем файл
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return {
            'success': True,
            'message': f'Торрент скачан: {filepath}',
            'filepath': str(filepath),
            'size': os.path.getsize(filepath)
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Ошибка при скачивании торрента: {e}'
        }

def register_tools(registry):
    """Регистрирует инструменты для скачивания торрентов"""
    registry.register(
        "download_torrent",
        download_torrent,
        "Скачивает торрент-файл по URL. Аргументы: url (str), filename (str, optional)"
    )

# Пример использования:
# result = download_torrent('https://byxatab.com/index.php?do=download&id=17832', 'manor_lords.torrent')
# print(result)