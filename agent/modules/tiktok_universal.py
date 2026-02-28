"""
TikTok Universal Module for AI Agent System
Provides async tools for downloading and analyzing TikTok content
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import yt_dlp

# Constants
TIKTOK_DATA_DIR = Path("data/tiktok")
TIKTOK_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from description text."""
    if not text:
        return []
    return re.findall(r'#(\w+)', text)


def _safe_get(data: Dict, *keys, default=None) -> Any:
    """Safely get nested dictionary values."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return default
    return data if data is not None else default


async def _run_ytdlp(params: Dict) -> Dict:
    """Run yt-dlp in executor to avoid blocking event loop."""
    loop = asyncio.get_event_loop()

    def _download():
        with yt_dlp.YoutubeDL(params) as ydl:
            return ydl.extract_info(params['url'], download=True)

    return await loop.run_in_executor(None, _download)


async def tiktok_get_metadata(url: str) -> Dict:
    """
    Get full metadata from TikTok video.

    Args:
        url: TikTok video URL

    Returns:
        Dict with metadata including:
        - id, description, upload_date, timestamp, uploader, uploader_id
        - duration, view_count, like_count, comment_count, repost_count
        - thumbnail, hashtags, webpage_url, extractor, ext, created_at
    """
    try:
        ydl_opts = {
            'url': url,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }

        info = await _run_ytdlp(ydl_opts)

        # Extract hashtags from description
        description = _safe_get(info, 'description', default='')
        hashtags = _extract_hashtags(description)

        # Prepare metadata
        metadata = {
            'id': _safe_get(info, 'id'),
            'description': description,
            'upload_date': _safe_get(info, 'upload_date'),
            'timestamp': _safe_get(info, 'timestamp'),
            'uploader': _safe_get(info, 'uploader'),
            'uploader_id': _safe_get(info, 'uploader_id'),
            'duration': _safe_get(info, 'duration'),
            'view_count': _safe_get(info, 'view_count'),
            'like_count': _safe_get(info, 'like_count'),
            'comment_count': _safe_get(info, 'comment_count'),
            'repost_count': _safe_get(info, 'repost_count'),
            'thumbnail': _safe_get(info, 'thumbnail'),
            'hashtags': hashtags,
            'webpage_url': _safe_get(info, 'webpage_url'),
            'extractor': _safe_get(info, 'extractor'),
            'ext': _safe_get(info, 'ext'),
            'created_at': datetime.now().isoformat(),
        }

        # Save metadata to file
        metadata_file = TIKTOK_DATA_DIR / f"{metadata['id']}_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return metadata

    except Exception as e:
        return {
            'error': str(e),
            'url': url,
            'created_at': datetime.now().isoformat()
        }


async def tiktok_download_video(url: str) -> Dict:
    """
    Download TikTok video to data/tiktok/ folder.

    Args:
        url: TikTok video URL

    Returns:
        Dict with:
        - file_path: path to downloaded video
        - metadata: video metadata
    """
    try:
        # First get metadata
        metadata = await tiktok_get_metadata(url)
        if 'error' in metadata:
            return metadata

        video_id = metadata['id']
        filename = f"{video_id}.mp4"
        filepath = TIKTOK_DATA_DIR / filename

        # Check if already downloaded
        if filepath.exists():
            return {
                'file_path': str(filepath),
                'metadata': metadata,
                'status': 'already_exists'
            }

        # Download video
        ydl_opts = {
            'url': url,
            'quiet': True,
            'no_warnings': True,
            'outtmpl': str(TIKTOK_DATA_DIR / '%(id)s.%(ext)s'),
            'format': 'mp4/best',
        }

        info = await _run_ytdlp(ydl_opts)

        # Verify download
        if filepath.exists():
            return {
                'file_path': str(filepath),
                'metadata': metadata,
                'file_size': filepath.stat().st_size,
                'status': 'downloaded'
            }
        else:
            return {
                'error': 'Video download failed',
                'metadata': metadata,
                'status': 'failed'
            }

    except Exception as e:
        return {
            'error': str(e),
            'url': url,
            'created_at': datetime.now().isoformat()
        }


async def tiktok_download_thumbnail(url: str) -> Dict:
    """
    Download TikTok video thumbnail.

    Args:
        url: TikTok video URL

    Returns:
        Dict with thumbnail info
    """
    try:
        # Get metadata first
        metadata = await tiktok_get_metadata(url)
        if 'error' in metadata:
            return metadata

        video_id = metadata['id']
        thumbnail_url = metadata.get('thumbnail')

        if not thumbnail_url:
            return {
                'error': 'No thumbnail available',
                'metadata': metadata
            }

        # Download thumbnail
        import urllib.request
        thumbnail_path = TIKTOK_DATA_DIR / f"{video_id}_thumbnail.jpg"

        def _download_thumb():
            urllib.request.urlretrieve(thumbnail_url, thumbnail_path)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _download_thumb)

        if thumbnail_path.exists():
            return {
                'file_path': str(thumbnail_path),
                'thumbnail_url': thumbnail_url,
                'metadata': metadata,
                'status': 'downloaded'
            }
        else:
            return {
                'error': 'Thumbnail download failed',
                'thumbnail_url': thumbnail_url,
                'metadata': metadata
            }

    except Exception as e:
        return {
            'error': str(e),
            'url': url,
            'created_at': datetime.now().isoformat()
        }


async def tiktok_download_subtitles(url: str) -> Dict:
    """
    Download subtitles and automatic captions if available.

    Args:
        url: TikTok video URL

    Returns:
        Dict with subtitles info
    """
    try:
        # Get metadata first
        metadata = await tiktok_get_metadata(url)
        if 'error' in metadata:
            return metadata

        video_id = metadata['id']

        # Try to get subtitles
        ydl_opts = {
            'url': url,
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'ru', 'auto'],
            'outtmpl': str(TIKTOK_DATA_DIR / f"{video_id}_subtitles" / '%(id)s_%(lang)s.%(ext)s'),
        }

        # Create subtitles directory
        subs_dir = TIKTOK_DATA_DIR / f"{video_id}_subtitles"
        subs_dir.mkdir(exist_ok=True)

        info = await _run_ytdlp(ydl_opts)

        # Check for downloaded subtitles
        subtitles = {}
        for ext in ['.vtt', '.srt', '.ttml', '.json']:
            for lang in ['en', 'ru', 'auto']:
                sub_file = subs_dir / f"{video_id}_{lang}{ext}"
                if sub_file.exists():
                    with open(sub_file, 'r', encoding='utf-8') as f:
                        subtitles[f"{lang}{ext}"] = f.read()

        result = {
            'video_id': video_id,
            'subtitles_dir': str(subs_dir),
            'available_subtitles': list(subtitles.keys()),
            'metadata': metadata,
        }

        if subtitles:
            # Save subtitles info
            subs_info_file = subs_dir / "subtitles_info.json"
            with open(subs_info_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            result['subtitles'] = subtitles
            result['status'] = 'downloaded'
        else:
            result['status'] = 'no_subtitles_available'

        return result

    except Exception as e:
        return {
            'error': str(e),
            'url': url,
            'created_at': datetime.now().isoformat()
        }


async def tiktok_get_comments(url: str) -> Dict:
    """
    Get comments from TikTok video.

    Args:
        url: TikTok video URL

    Returns:
        Dict with comments list
    """
    try:
        # Get metadata first
        metadata = await tiktok_get_metadata(url)
        if 'error' in metadata:
            return metadata

        video_id = metadata['id']

        # Try to extract comments (note: yt-dlp may not always get comments from TikTok)
        ydl_opts = {
            'url': url,
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'getcomments': True,
        }

        info = await _run_ytdlp(ydl_opts)

        comments = _safe_get(info, 'comments', default=[])

        # Process comments
        processed_comments = []
        for comment in comments:
            processed_comments.append({
                'author': _safe_get(comment, 'author'),
                'text': _safe_get(comment, 'text'),
                'like_count': _safe_get(comment, 'like_count'),
                'timestamp': _safe_get(comment, 'timestamp'),
            })

        result = {
            'video_id': video_id,
            'comment_count': len(processed_comments),
            'comments': processed_comments,
            'metadata': metadata,
        }

        # Save comments to file
        comments_file = TIKTOK_DATA_DIR / f"{video_id}_comments.json"
        with open(comments_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    except Exception as e:
        return {
            'error': str(e),
            'url': url,
            'created_at': datetime.now().isoformat()
        }


async def tiktok_get_all(url: str) -> Dict:
    """
    Complete pipeline: metadata + video + thumbnail + subtitles + comments.

    Args:
        url: TikTok video URL

    Returns:
        Dict with all data
    """
    try:
        # Get metadata first
        metadata = await tiktok_get_metadata(url)
        if 'error' in metadata:
            return {'metadata_error': metadata}

        video_id = metadata['id']

        # Run all operations in parallel
        video_task = tiktok_download_video(url)
        thumbnail_task = tiktok_download_thumbnail(url)
        subtitles_task = tiktok_download_subtitles(url)
        comments_task = tiktok_get_comments(url)

        video_result, thumbnail_result, subtitles_result, comments_result = await asyncio.gather(
            video_task, thumbnail_task, subtitles_task, comments_task,
            return_exceptions=True
        )

        # Handle exceptions
        def _handle_result(result):
            if isinstance(result, Exception):
                return {'error': str(result)}
            return result

        video_result = _handle_result(video_result)
        thumbnail_result = _handle_result(thumbnail_result)
        subtitles_result = _handle_result(subtitles_result)
        comments_result = _handle_result(comments_result)

        # Combine all results
        combined_result = {
            'video_id': video_id,
            'url': url,
            'metadata': metadata,
            'video': video_result,
            'thumbnail': thumbnail_result,
            'subtitles': subtitles_result,
            'comments': comments_result,
            'created_at': datetime.now().isoformat(),
        }

        # Save combined result
        combined_file = TIKTOK_DATA_DIR / f"{video_id}_complete.json"
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump(combined_result, f, ensure_ascii=False, indent=2)

        return combined_result

    except Exception as e:
        return {
            'error': str(e),
            'url': url,
            'created_at': datetime.now().isoformat()
        }


def register_tools(registry):
    """Register all TikTok tools with the registry."""

    registry.register(
        name="tiktok_get_metadata",
        func=tiktok_get_metadata,
        description="Get full metadata from TikTok video (id, description, stats, etc.)"
    )

    registry.register(
        name="tiktok_download_video",
        func=tiktok_download_video,
        description="Download TikTok video to data/tiktok/ folder"
    )

    registry.register(
        name="tiktok_download_thumbnail",
        func=tiktok_download_thumbnail,
        description="Download TikTok video thumbnail"
    )

    registry.register(
        name="tiktok_download_subtitles",
        func=tiktok_download_subtitles,
        description="Download subtitles and automatic captions from TikTok video"
    )

    registry.register(
        name="tiktok_get_comments",
        func=tiktok_get_comments,
        description="Get comments from TikTok video"
    )

    registry.register(
        name="tiktok_get_all",
        func=tiktok_get_all,
        description="Complete pipeline: metadata + video + thumbnail + subtitles + comments"
    )