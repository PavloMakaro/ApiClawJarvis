import asyncio
import json
import logging
from aiohttp import web

from bot import process_agent_loop_api

logger = logging.getLogger(__name__)

async def chat_endpoint(request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Invalid JSON")

    chat_id = data.get("chat_id")
    message = data.get("message")

    if not chat_id or not message:
        return web.Response(status=400, text="Missing chat_id or message")

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

    try:
        # process_agent_loop_api will yield events that we write to the response
        async for event in process_agent_loop_api(str(chat_id), message):
            if isinstance(event, dict):
                # Ensure correct SSE formatting
                event_data = json.dumps(event, ensure_ascii=False)
                await response.write(f"data: {event_data}\n\n".encode('utf-8'))
            else:
                await response.write(f"data: {event}\n\n".encode('utf-8'))
    except asyncio.CancelledError:
        logger.info("Client disconnected from SSE stream")
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        error_event = json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
        await response.write(f"data: {error_event}\n\n".encode('utf-8'))

    return response

async def init_app():
    app = web.Application()
    app.router.add_post('/chat', chat_endpoint)

    # Handle CORS preflight
    async def options_handler(request):
        return web.Response(headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        })
    app.router.add_options('/chat', options_handler)

    return app

async def start_api_server(host='0.0.0.0', port=8080):
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"API server started on http://{host}:{port}")
