"""
Scheduler tools — напоминания и запланированные задачи.
"""

import datetime
import pytz

IRKUTSK_TZ = pytz.timezone("Asia/Irkutsk")


def register_tools(registry):
    registry.register(
        "set_reminder",
        set_reminder,
        "Установить одноразовое напоминание. Args: seconds (int — через сколько секунд), message (str — текст напоминания).",
        requires_context=True
    )
    registry.register(
        "schedule_recurring_task",
        schedule_recurring_task,
        "Запланировать ежедневную задачу. Args: time (str — время в формате 'HH:MM' по Иркутску), prompt (str — задача для агента).",
        requires_context=True
    )


async def alarm(context):
    """Callback для напоминания."""
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"🔔 Напоминание: {job.data}")


async def set_reminder(seconds: int, message: str, job_queue=None, chat_id=None, **kwargs):
    """Установить одноразовое напоминание.

    Args:
        seconds: Через сколько секунд напомнить
        message: Текст напоминания
    """
    if not job_queue or not chat_id:
        return "Ошибка: нет доступа к JobQueue или ChatID."

    try:
        seconds = int(seconds)
        job_queue.run_once(alarm, seconds, chat_id=chat_id, data=message)
        mins = seconds // 60
        if mins > 0:
            return f"Напоминание установлено через {mins} мин: {message}"
        return f"Напоминание установлено через {seconds} сек: {message}"
    except Exception as e:
        return f"Ошибка: {str(e)}"


async def schedule_recurring_task(time: str = "08:00", prompt: str = "Проверь погоду",
                                  job_queue=None, chat_id=None, agent_runner=None, **kwargs):
    """Запланировать ежедневную задачу по времени Иркутска.

    Args:
        time: Время в формате 'HH:MM' (по Иркутску)
        prompt: Задача для агента
    """
    if not job_queue or not chat_id:
        return "Ошибка: нет доступа к JobQueue или ChatID."
    if not agent_runner:
        return "Ошибка: agent_runner не найден в контексте."

    try:
        hour, minute = map(int, time.split(":"))
        # Используем timezone Иркутска для корректного планирования
        t = datetime.time(hour=hour, minute=minute, tzinfo=IRKUTSK_TZ)

        job_name = f"recurring_{chat_id}_{int(datetime.datetime.now().timestamp())}"
        job_queue.run_daily(agent_runner, t, chat_id=chat_id, data=prompt, name=job_name)

        return f"Ежедневная задача запланирована на {time} (Иркутск): {prompt}"
    except Exception as e:
        return f"Ошибка: {str(e)}"
