"""
Media processing module — video download and audio transcription.
OCR/Vision перенесён в groq_vision_ocr.py.
"""

import asyncio
import os
import yt_dlp
from groq import Groq
import config


async def download_video(url: str) -> str:
    """Download video using yt-dlp.

    Args:
        url: URL видео для скачивания (YouTube, TikTok и т.д.)
    """
    try:
        os.makedirs("downloads", exist_ok=True)

        ydl_opts = {
            "outtmpl": "downloads/%(title)s.%(ext)s",
            "format": "best",
            "noplaylist": True,
            "quiet": True,
        }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        filename = await asyncio.to_thread(_download)
        return f"Video downloaded to: {filename}"
    except Exception as e:
        return f"Error downloading video: {str(e)}"


async def transcribe_audio(filepath: str) -> str:
    """Transcribe audio/voice file using Groq Whisper.

    Args:
        filepath: Локальный путь к аудиофайлу (.ogg, .mp3, .wav и т.д.)
    """
    try:
        if not os.path.exists(filepath):
            return "Error: File not found."

        client = Groq(api_key=config.GROQ_API_KEY)

        def _transcribe():
            with open(filepath, "rb") as file:
                result = client.audio.transcriptions.create(
                    file=(os.path.basename(filepath), file.read()),
                    model="whisper-large-v3",
                    response_format="text",
                )
                return str(result) if result else ""

        transcription = await asyncio.to_thread(_transcribe)
        return transcription
    except Exception as e:
        return f"Error transcribing audio: {str(e)}"


def register_tools(registry):
    """Register media tools — only video download and audio transcription."""
    registry.register(
        "download_video",
        download_video,
        "Скачать видео по URL (YouTube, TikTok и др.). Args: url (str)",
    )
    registry.register(
        "transcribe_audio",
        transcribe_audio,
        "Транскрибировать аудио/голосовой файл через Groq Whisper. Args: filepath (str)",
    )
