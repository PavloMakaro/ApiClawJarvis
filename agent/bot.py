import logging
import asyncio
import os
import time
import json
import traceback
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
import config
from core.agent import Agent
from core.tools import ToolRegistry
from core.watcher import ModuleWatcher
from core.ui.telegram_renderer import TelegramRenderer
from core.ui.api_renderer import ApiRenderer

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Initialize Tools
registry = ToolRegistry()
registry.load_modules()

# Initialize Watcher
watcher = ModuleWatcher(registry)
watcher.start()

# Initialize Agent
agent = Agent(registry)

from core.state import (
    user_sessions,
    user_usage,
    session_summarized_at,
    session_lock,
    running_tasks,
    save_sessions,
    DOWNLOADS_DIR
)

# Token counting — лёгкая аппроксимация без tiktoken
# ~1 токен на 3.5 символа для русского/смешанного текста (точнее чем //4)
def count_tokens(text):
    if not text:
        return 0
    s = str(text)
    # Для русского текста ~3.5 символа на токен, для английского ~4
    return max(1, int(len(s) / 3.5))


async def summarize_history(history_slice):
    """Summarizes a slice of conversation history via DeepSeek."""
    try:
        prompt = "Кратко суммаризуй следующий диалог в 2-3 предложениях, сохранив ключевые факты и контекст:"
        msgs = [{"role": "system", "content": prompt}]
        for m in history_slice:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            msgs.append({"role": "user", "content": f"{role}: {content}"})

        response_msg = await agent.llm.generate(
            msgs, stream=False, max_tokens=512, temperature=0.3
        )
        if response_msg and response_msg.content:
            return response_msg.content
    except Exception as e:
        logging.error(f"Summarization failed: {e}")
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    async with session_lock:
        user_sessions[chat_id] = []
        save_sessions()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Здравствуйте, сэр. Джарвис к вашим услугам.",
    )


async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    async with session_lock:
        user_sessions[chat_id] = []
        save_sessions()
    user_usage.pop(chat_id, None)
    await context.bot.send_message(chat_id=chat_id, text="Память очищена, сэр.")


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id in running_tasks:
        task = running_tasks[chat_id]
        if not task.done():
            task.cancel()
            await context.bot.send_message(chat_id=chat_id, text="Остановлено.")
        else:
            await context.bot.send_message(chat_id=chat_id, text="Ничего не выполняется.")
    else:
        await context.bot.send_message(chat_id=chat_id, text="Ничего не выполняется.")


async def save_user_file(file_obj, chat_id, original_filename=None):
    """Downloads a file and returns the local path."""
    timestamp = int(time.time())

    user_dir = os.path.join(DOWNLOADS_DIR, str(chat_id))
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    if original_filename:
        filename = f"{timestamp}_{original_filename}"
    else:
        ext = ".bin"
        if hasattr(file_obj, "file_path") and file_obj.file_path:
            _, ext = os.path.splitext(file_obj.file_path)
        filename = f"{timestamp}_file{ext}"

    filepath = os.path.join(user_dir, filename)
    await file_obj.download_to_drive(filepath)
    return filepath


async def _run_task(chat_id, user_input, context):
    """Wrapper to run agent loop and clean up running_tasks."""
    try:
        await process_agent_loop(chat_id, user_input, context)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logging.error(f"Task failed for {chat_id}: {e}")
    finally:
        task = running_tasks.get(str(chat_id))
        if task and task.done():
            running_tasks.pop(str(chat_id), None)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    chat_id = str(update.effective_chat.id)

    # Cancel previous task if running
    if chat_id in running_tasks:
        task = running_tasks[chat_id]
        if not task.done():
            task.cancel()

    task = asyncio.create_task(_run_task(chat_id, user_input, context))
    running_tasks[chat_id] = task


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    status_msg = await context.bot.send_message(
        chat_id=chat_id, text="Принимаю голосовое сообщение..."
    )

    try:
        file = await update.message.voice.get_file()
        filepath = await save_user_file(file, chat_id, f"voice.ogg")
        caption = update.message.caption or ""

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text="Голос получен. Транскрибирую...",
        )

        # Формируем prompt с путём файла (без дублирования в историю)
        prompt = f"Транскрибируй голосовое сообщение из файла: {filepath}"
        if caption:
            prompt += f" Контекст: {caption}"

        if chat_id in running_tasks:
            task = running_tasks[chat_id]
            if not task.done():
                task.cancel()

        task = asyncio.create_task(_run_task(chat_id, prompt, context))
        running_tasks[chat_id] = task

    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id, text=f"Ошибка обработки голосового: {str(e)}"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        filepath = await save_user_file(file, chat_id, f"image.jpg")
        caption = update.message.caption or ""

        prompt = f"[Изображение: {filepath}]. {caption if caption else 'Проанализируй изображение.'}"

        if chat_id in running_tasks:
            task = running_tasks[chat_id]
            if not task.done():
                task.cancel()

        task = asyncio.create_task(_run_task(chat_id, prompt, context))
        running_tasks[chat_id] = task

    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id, text=f"Ошибка обработки изображения: {str(e)}"
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    try:
        doc = update.message.document
        file = await doc.get_file()
        filepath = await save_user_file(file, chat_id, doc.file_name)
        caption = update.message.caption or ""

        prompt = f"[Файл: {filepath}]. {caption if caption else 'Проанализируй файл.'}"

        if chat_id in running_tasks:
            task = running_tasks[chat_id]
            if not task.done():
                task.cancel()

        task = asyncio.create_task(_run_task(chat_id, prompt, context))
        running_tasks[chat_id] = task

    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id, text=f"Ошибка обработки файла: {str(e)}"
        )


async def process_agent_loop_api(chat_id_str, user_input):
    """
    Parallel version of process_agent_loop that does not rely on Telegram bot context.
    Yields events via ApiRenderer for HTTP responses.
    """

    # 1. Check Usage Quota
    current_usage = user_usage.get(chat_id_str, 0)
    if current_usage > 50000:
        yield {"status": "error", "message": "Лимит токенов сессии превышен (50,000). Используйте /clear для сброса."}
        return

    async with session_lock:
        if chat_id_str not in user_sessions:
            user_sessions[chat_id_str] = []

        # 2. Smart Context Summarization
        hist = user_sessions[chat_id_str]
        total_tokens = sum(count_tokens(m.get("content", "")) for m in hist)

        already_at = session_summarized_at.get(chat_id_str, 0)
        need_summarize = (len(hist) > 20 or total_tokens > 8000) and (len(hist) - already_at) >= 6

        if need_summarize:
            if len(hist) > 8:
                to_summarize = hist[:-8]
                kept_history = hist[-8:]

                yield {"status": "thinking", "message": "Оптимизирую память..."}

                summary = await summarize_history(to_summarize)

                if summary:
                    new_hist = [
                        {"role": "system", "content": f"[Краткое содержание предыдущего разговора]: {summary}"}
                    ] + kept_history
                    user_sessions[chat_id_str] = new_hist
                    save_sessions()
                    session_summarized_at[chat_id_str] = len(new_hist)
                    logging.info(f"Summarized history for {chat_id_str}")

        session_history_start = list(user_sessions[chat_id_str])

    current_history = list(session_history_start)

    renderer = ApiRenderer(chat_id_str)
    async for e in renderer.start():
        yield e

    final_response = ""

    # Mock tool_context since there's no telegram context
    tool_ctx = {
        "bot": None,
        "chat_id": chat_id_str,
        "job_queue": None,
        "registry": registry,
        "agent_runner": None,
    }

    try:
        async for update_data in agent.run(
            user_input, history=current_history, tool_context=tool_ctx, plan_mode=True
        ):
            status = update_data.get("status")

            if status == "thinking":
                message = update_data.get("message", "")
                if message:
                    async for e in renderer.update("thinking", message): yield e

            elif status == "plan_ready":
                async for e in renderer.set_plan(
                    update_data.get("plan_steps", []),
                    update_data.get("total_steps", 0)
                ): yield e

            elif status == "plan_step_start":
                async for e in renderer.handle_plan_step_start(update_data.get("step_id", "")): yield e

            elif status == "thinking_stream":
                content = update_data.get("content", "")
                if content:
                    async for e in renderer.update("thinking_stream", content): yield e

            elif status == "tool_use":
                async for e in renderer.update("tool_use", update_data): yield e

            elif status == "observation":
                result = update_data.get("result")
                async for e in renderer.update("observation", result): yield e

            elif status == "final_stream":
                content = update_data.get("content")
                async for e in renderer.update("final_stream", content): yield e

            elif status == "final":
                final_response = update_data.get("content")
                async for e in renderer.update("final", final_response): yield e

            elif status == "error":
                error_msg = update_data.get("message", "Неизвестная ошибка")
                async for e in renderer.update("error", error_msg): yield e

    except asyncio.CancelledError:
        async for e in renderer.stop(): yield e
        return
    except Exception as e:
        final_response = f"Ошибка в цикле агента: {str(e)}"
        logging.error(f"Agent loop error: {e}")
        async for e in renderer.update("error", final_response): yield e

    async for e in renderer.stop():
        yield e

    # Post-processing
    if final_response:
        # Update usage
        input_tokens = count_tokens(user_input)
        output_tokens = count_tokens(final_response)
        turn_usage = input_tokens + output_tokens + 500
        user_usage[chat_id_str] = user_usage.get(chat_id_str, 0) + turn_usage

        # Update history
        new_history = list(session_history_start)
        new_history.append({"role": "user", "content": user_input})
        new_history.append({"role": "assistant", "content": final_response})

        async with session_lock:
            user_sessions[chat_id_str] = new_history
            save_sessions()


async def process_agent_loop(chat_id, user_input, context):
    chat_id_str = str(chat_id)

    # 1. Check Usage Quota
    current_usage = user_usage.get(chat_id_str, 0)
    if current_usage > 50000:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Лимит токенов сессии превышен (50,000). Используйте /clear для сброса."
        )
        return

    async with session_lock:
        if chat_id_str not in user_sessions:
            user_sessions[chat_id_str] = []

        # 2. Smart Context Summarization (повышенные пороги + защита от повтора)
        hist = user_sessions[chat_id_str]
        total_tokens = sum(count_tokens(m.get("content", "")) for m in hist)

        already_at = session_summarized_at.get(chat_id_str, 0)
        need_summarize = (len(hist) > 20 or total_tokens > 8000) and (len(hist) - already_at) >= 6

        if need_summarize:
            if len(hist) > 8:
                to_summarize = hist[:-8]
                kept_history = hist[-8:]

                status_msg = await context.bot.send_message(
                    chat_id=chat_id, text="🔄 Оптимизирую память..."
                )

                summary = await summarize_history(to_summarize)

                if summary:
                    new_hist = [
                        {"role": "system", "content": f"[Краткое содержание предыдущего разговора]: {summary}"}
                    ] + kept_history
                    user_sessions[chat_id_str] = new_hist
                    save_sessions()
                    session_summarized_at[chat_id_str] = len(new_hist)
                    logging.info(f"Summarized history for {chat_id_str}")

                try:
                    await context.bot.delete_message(
                        chat_id=chat_id, message_id=status_msg.message_id
                    )
                except Exception:
                    pass

        session_history_start = list(user_sessions[chat_id_str])

    current_history = list(session_history_start)

    # Use TelegramRenderer for beautiful display
    renderer = TelegramRenderer(context.bot, chat_id)
    await renderer.start()

    final_response = ""

    tool_ctx = {
        "bot": context.bot,
        "chat_id": chat_id,
        "job_queue": context.job_queue,
        "registry": registry,
        "agent_runner": scheduled_task_callback,
    }

    try:
        async for update_data in agent.run(
            user_input, history=current_history, tool_context=tool_ctx, plan_mode=True
        ):
            status = update_data.get("status")

            if status == "thinking":
                message = update_data.get("message", "")
                if message:
                    await renderer.update("thinking", message)

            elif status == "plan_ready":
                await renderer.set_plan(
                    update_data.get("plan_steps", []),
                    update_data.get("total_steps", 0)
                )

            elif status == "plan_step_start":
                await renderer.handle_plan_step_start(update_data.get("step_id", ""))

            elif status == "thinking_stream":
                content = update_data.get("content", "")
                if content:
                    await renderer.update("thinking_stream", content)

            elif status == "tool_use":
                await renderer.update("tool_use", update_data)

            elif status == "observation":
                result = update_data.get("result")
                await renderer.update("observation", result)

            elif status == "final_stream":
                content = update_data.get("content")
                await renderer.update("final_stream", content)

            elif status == "final":
                final_response = update_data.get("content")
                await renderer.update("final", final_response)

            elif status == "error":
                error_msg = update_data.get("message", "Неизвестная ошибка")
                await renderer.update("error", error_msg)

    except asyncio.CancelledError:
        await renderer.stop()
        await context.bot.send_message(chat_id=chat_id, text="Остановлено.")
        return
    except Exception as e:
        final_response = f"Ошибка в цикле агента: {str(e)}"
        logging.error(f"Agent loop error: {e}")
        await renderer.update("error", final_response)

    # Post-processing
    if final_response:
        # Handle long response overflow (renderer показывает последние 4000 символов)
        if len(final_response) > 4000:
            remaining = final_response[4000:]
            if remaining.strip():
                chunks = [remaining[i: i + 4096] for i in range(0, len(remaining), 4096)]
                for chunk in chunks:
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id, text=chunk, parse_mode="Markdown"
                        )
                    except Exception:
                        await context.bot.send_message(chat_id=chat_id, text=chunk)

        # Update usage
        input_tokens = count_tokens(user_input)
        output_tokens = count_tokens(final_response)
        turn_usage = input_tokens + output_tokens + 500
        user_usage[chat_id_str] = user_usage.get(chat_id_str, 0) + turn_usage

        # Update history
        new_history = list(session_history_start)
        new_history.append({"role": "user", "content": user_input})
        new_history.append({"role": "assistant", "content": final_response})

        async with session_lock:
            user_sessions[chat_id_str] = new_history
            save_sessions()


async def scheduled_task_callback(context: ContextTypes.DEFAULT_TYPE):
    """Callback for scheduled recurring tasks."""
    job = context.job
    chat_id = job.chat_id
    prompt = job.data

    await context.bot.send_message(chat_id=chat_id, text=f"⏰ Запланированная задача: {prompt}")
    await process_agent_loop(chat_id, prompt, context)


async def main():
    from api import start_api_server

    # Start the API server in background
    await start_api_server()

    # Start Telegram bot
    application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_memory))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    )
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("JarvisClaw and API are running...")

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # Keep running
    stop_signal = asyncio.Event()
    await stop_signal.wait()

if __name__ == "__main__":
    asyncio.run(main())
