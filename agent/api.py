import asyncio
import json
import logging
from aiohttp import web

from bot import process_agent_loop_api, user_sessions, session_lock, save_sessions, user_usage, running_tasks

logger = logging.getLogger(__name__)

import os
import time

DOWNLOADS_DIR = "downloads"

async def chat_endpoint(request):
    chat_id = None
    message = ""
    file_path = None
    caption = ""
    file_type = None

    if request.content_type == 'multipart/form-data':
        reader = await request.multipart()

        while True:
            part = await reader.next()
            if part is None:
                break

            if part.name == 'chat_id':
                chat_id = await part.text()
            elif part.name == 'message' or part.name == 'caption':
                message = await part.text()
                if part.name == 'caption':
                    caption = message
            elif part.name == 'file':
                file_type = part.headers.get("Content-Type", "")

                # Setup user directory
                if not chat_id:
                    chat_id = "default_api_user"

                user_dir = os.path.join(DOWNLOADS_DIR, str(chat_id))
                if not os.path.exists(user_dir):
                    os.makedirs(user_dir)

                filename = part.filename or f"{int(time.time())}_upload"
                file_path = os.path.join(user_dir, f"{int(time.time())}_{filename}")

                with open(file_path, 'wb') as f:
                    while True:
                        chunk = await part.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)
    else:
        try:
            data = await request.json()
        except Exception:
            return web.Response(status=400, text="Invalid JSON or missing multipart/form-data")

        chat_id = data.get("chat_id")
        message = data.get("message")

    if not chat_id:
        return web.Response(status=400, text="Missing chat_id")

    if not message and not file_path:
        return web.Response(status=400, text="Missing message or file")

    # Construct prompt if file is uploaded
    prompt = message
    if file_path:
        if "audio" in file_type or "voice" in file_type or file_path.endswith(('.ogg', '.mp3', '.wav')):
            prompt = f"Транскрибируй голосовое сообщение из файла: {file_path}"
            if caption:
                prompt += f" Контекст: {caption}"
        elif "image" in file_type or file_path.endswith(('.jpg', '.png', '.jpeg')):
            prompt = f"[Изображение: {file_path}]. {caption if caption else 'Проанализируй изображение.'}"
        else:
            prompt = f"[Файл: {file_path}]. {caption if caption else 'Проанализируй файл.'}"

    response = web.StreamResponse(
        status=200,
        reason='OK',
        headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )

    await response.prepare(request)

    # Manage tasks to allow stopping
    chat_id_str = str(chat_id)
    if chat_id_str in running_tasks:
        task = running_tasks[chat_id_str]
        if not task.done():
            task.cancel()

    async def _run_agent_stream():
        try:
            # process_agent_loop_api will yield events that we write to the response
            async for event in process_agent_loop_api(chat_id_str, prompt):
                if isinstance(event, dict):
                    # Ensure correct SSE formatting
                    event_data = json.dumps(event, ensure_ascii=False)
                    await response.write(f"data: {event_data}\n\n".encode('utf-8'))
                else:
                    await response.write(f"data: {event}\n\n".encode('utf-8'))
        except asyncio.CancelledError:
            logger.info("Client disconnected from SSE stream")
            raise
        except Exception as e:
            logger.error(f"Error in chat endpoint: {e}")
            error_event = json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
            await response.write(f"data: {error_event}\n\n".encode('utf-8'))
            raise

    task = asyncio.create_task(_run_agent_stream())
    running_tasks[chat_id_str] = task

    try:
        await task
    except asyncio.CancelledError:
        pass
    finally:
        if running_tasks.get(chat_id_str) == task:
            running_tasks.pop(chat_id_str, None)

    return response

async def clear_endpoint(request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Invalid JSON")

    chat_id = data.get("chat_id")
    if not chat_id:
        return web.Response(status=400, text="Missing chat_id")

    chat_id_str = str(chat_id)
    async with session_lock:
        user_sessions[chat_id_str] = []
        save_sessions()
    user_usage.pop(chat_id_str, None)

    return web.json_response({"status": "success", "message": "Память очищена, сэр."})

async def stop_endpoint(request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Invalid JSON")

    chat_id = data.get("chat_id")
    if not chat_id:
        return web.Response(status=400, text="Missing chat_id")

    chat_id_str = str(chat_id)
    if chat_id_str in running_tasks:
        task = running_tasks[chat_id_str]
        if not task.done():
            task.cancel()
            return web.json_response({"status": "success", "message": "Остановлено."})
        else:
            return web.json_response({"status": "success", "message": "Ничего не выполняется."})
    else:
        return web.json_response({"status": "success", "message": "Ничего не выполняется."})

async def init_app():
    app = web.Application()
    app.router.add_post('/chat', chat_endpoint)
    app.router.add_post('/clear', clear_endpoint)
    app.router.add_post('/stop', stop_endpoint)

    # Handle CORS preflight
    async def options_handler(request):
        return web.Response(headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        })
    app.router.add_options('/chat', options_handler)
    app.router.add_options('/clear', options_handler)
    app.router.add_options('/stop', options_handler)

    return app

async def start_api_server(host='0.0.0.0', port=8080):
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"API server started on http://{host}:{port}")
