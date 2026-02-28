import asyncio
import time
import logging
from telegram import constants
from telegram.error import BadRequest, RetryAfter

logger = logging.getLogger(__name__)


class TelegramRenderer:
    """Красивый анимированный UI-рендерер для Telegram.

    ОДНО сообщение которое постоянно обновляется:
    - Мысли агента с анимацией
    - Чеклист шагов плана (✅ / 🌕 / ⏳)
    - Анимация луны пока инструмент работает
    - Прогресс-бар
    В финале — сообщение удаляется, отправляется чистый ответ.
    """

    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id

        # Единственное статусное сообщение
        self.status_msg_id = None
        self.final_msg_id = None

        # Состояние
        self.is_finished = False
        self.final_text = ""

        # Мысли агента (промежуточный текст LLM)
        self.thought_text = ""

        # Чеклист плана
        # [{"name": str, "step": int, "status": "done"|"running"|"pending"}]
        self.plan_steps = []
        self.current_step = 0
        self.total_steps = 0
        self.current_tool = ""

        # Анимации
        self.moon = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
        self.think_anim = ["🧠", "💭", "✨", "⚡", "🔮", "💡"]
        self.search_anim = ["🔍", "🔎", "🌍", "🌐", "📡"]
        self.code_anim = ["💻", "⌨️", "🖥", "⚙️", "🔧"]
        self.file_anim = ["📂", "📁", "📄", "📤", "📥"]
        self.memory_anim = ["🧠", "💾", "📝", "🗃", "💡"]
        self.web_anim = ["🌐", "🔗", "📶", "🛰", "🌍"]
        self.media_anim = ["🎬", "🎵", "📸", "🎤", "📹"]

        # Троттлинг
        self.last_edit_time = 0
        self.min_interval = 1.2
        self.anim_task = None

    # ─── Public API ───────────────────────────────────────

    async def start(self):
        """Начальное статусное сообщение."""
        try:
            moon = self.moon[0]
            msg = await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"{moon} *Инициализация...*",
                parse_mode=constants.ParseMode.MARKDOWN,
            )
            self.status_msg_id = msg.message_id
            self.last_edit_time = time.time()
        except Exception as e:
            logger.error(f"Renderer start error: {e}")

    async def update(self, status_type, content):
        """Главный диспетчер."""
        if self.is_finished:
            return

        if status_type == "thinking":
            await self._handle_thinking(content)
        elif status_type == "thinking_stream":
            await self._handle_thinking_stream(content)
        elif status_type == "tool_use":
            await self._handle_tool_use(content)
        elif status_type == "observation":
            await self._handle_observation(content)
        elif status_type == "final_stream":
            await self._handle_final_stream(content)
        elif status_type == "final":
            await self._handle_final(content)
        elif status_type == "error":
            await self._handle_error(content)

    # ─── Handlers ─────────────────────────────────────────

    async def _handle_thinking(self, content):
        """Уведомление 'Анализирую...' — обновляем статус."""
        text = self._render()
        await self._throttled_edit(text)

    async def _handle_thinking_stream(self, content):
        """Промежуточные мысли LLM (перед tool calls)."""
        if not content:
            return
        self.thought_text = content
        text = self._render()
        await self._throttled_edit(text)

    async def _handle_tool_use(self, content):
        """Инструмент запущен — добавляем в чеклист, запускаем анимацию."""
        # Стоп предыдущую анимацию
        if self.anim_task:
            self.anim_task.cancel()
            self.anim_task = None

        if isinstance(content, dict):
            tool_name = content.get("tool", "Unknown")
            step = content.get("step", 0)
            total = content.get("total_steps", 0)
        else:
            tool_name = str(content)
            step = 0
            total = 0

        self.current_tool = tool_name
        if step > 0:
            self.current_step = step
        if total > 0:
            self.total_steps = total

        # Обновляем чеклист
        if self.current_step > 0:
            self._update_plan(tool_name, self.current_step)

        # Рендер и запуск анимации
        text = self._render()
        await self._force_edit(text)
        self.anim_task = asyncio.create_task(self._animate())

    async def _handle_observation(self, content):
        """Инструмент завершён — помечаем шаг как done."""
        if self.anim_task:
            self.anim_task.cancel()
            self.anim_task = None

        # Помечаем текущий шаг
        if self.current_step > 0:
            self._mark_done(self.current_step)

        self.current_tool = ""
        text = self._render()
        await self._force_edit(text)

    async def _handle_final_stream(self, content):
        """Стриминг финального ответа — переходим на отдельное сообщение."""
        self.final_text += content

        if not self.final_msg_id:
            # Удаляем статусное сообщение
            await self._delete_status()
            msg = await self._safe_send(self.final_text[-4000:] or "...")
            if msg:
                self.final_msg_id = msg.message_id
                self.last_edit_time = time.time()
        else:
            now = time.time()
            if now - self.last_edit_time > self.min_interval:
                await self._safe_edit(self.final_msg_id, self.final_text[-4000:])
                self.last_edit_time = now

    async def _handle_final(self, content):
        """Финал — удаляем статус, отправляем чистый ответ."""
        self.final_text = content or self.final_text
        self.is_finished = True

        if self.anim_task:
            self.anim_task.cancel()
            self.anim_task = None

        await self._delete_status()

        display = self.final_text[-4000:] if self.final_text else "Готово."

        if self.final_msg_id:
            await self._safe_edit(self.final_msg_id, display)
        else:
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=display,
                    parse_mode=constants.ParseMode.MARKDOWN,
                )
            except Exception:
                try:
                    await self.bot.send_message(chat_id=self.chat_id, text=display)
                except Exception:
                    pass

    async def _handle_error(self, content):
        """Ошибка."""
        if self.anim_task:
            self.anim_task.cancel()
            self.anim_task = None

        text = f"⚠️ *Ошибка:* {self._esc(str(content)[:500])}"
        if self.status_msg_id:
            await self._safe_edit(self.status_msg_id, text)
        else:
            await self._safe_send(text)

    # ─── Render ───────────────────────────────────────────

    def _render(self):
        """Рендер единого статусного сообщения.

        Структура:
        ┌─ Мысли агента (если есть)
        ├─ Чеклист шагов
        ├─ Текущий инструмент с анимацией
        └─ Прогресс-бар
        """
        lines = []
        now = time.time()

        # ── Мысли агента ──
        if self.thought_text:
            think_icon = self.think_anim[int(now * 1.5) % len(self.think_anim)]
            # Берём последние 3 строки мыслей, обрезаем
            thought_lines = self.thought_text.strip().split("\n")
            # Показываем макс 5 строк чтобы не раздувать
            display_lines = thought_lines[-5:]
            thought_display = "\n".join(display_lines)
            if len(thought_display) > 500:
                thought_display = thought_display[-500:]
            lines.append(f"{think_icon} *Размышления:*")
            lines.append(f"```\n{thought_display}\n```")

        # ── Чеклист плана ──
        if self.plan_steps:
            lines.append("")
            lines.append("📋 *План:*")
            for s in self.plan_steps:
                if s["status"] == "done":
                    lines.append(f"  ✅ ~Шаг {s['step']}: {s['name']}~")
                elif s["status"] == "running":
                    tool_frames = self._get_tool_frames(s["name"])
                    frame = tool_frames[int(now * 2) % len(tool_frames)]
                    lines.append(f"  {frame} *Шаг {s['step']}: {s['name']}...*")
                else:
                    lines.append(f"  ⏳ Шаг {s['step']}: {s['name']}")

            # Прогресс-бар
            done = sum(1 for s in self.plan_steps if s["status"] == "done")
            total = max(len(self.plan_steps), self.total_steps)
            if total > 0:
                pct = int(done / total * 100)
                filled = int(done / total * 10)
                bar = "▓" * filled + "░" * (10 - filled)
                lines.append(f"\n`[{bar}]` {pct}%")

        # ── Если нет шагов и нет мыслей — просто анимация ──
        if not lines:
            moon = self.moon[int(now * 2) % len(self.moon)]
            lines.append(f"{moon} *Обрабатываю...*")

        # ── Если есть шаги но нет running и нет мыслей — формируем ответ ──
        has_running = any(s["status"] == "running" for s in self.plan_steps)
        if self.plan_steps and not has_running and not self.current_tool:
            moon = self.moon[int(now * 2) % len(self.moon)]
            lines.append(f"\n{moon} *Формирую ответ...*")

        return "\n".join(lines)

    def _update_plan(self, tool_name, step):
        """Добавить/обновить шаг в чеклисте."""
        # Расширяем
        target = max(step, self.total_steps)
        while len(self.plan_steps) < target:
            idx = len(self.plan_steps) + 1
            self.plan_steps.append({"name": "...", "step": idx, "status": "pending"})

        # Помечаем предыдущие как done
        for i in range(len(self.plan_steps)):
            if i < step - 1 and self.plan_steps[i]["status"] != "done":
                self.plan_steps[i]["status"] = "done"
            elif i == step - 1:
                self.plan_steps[i]["name"] = tool_name
                self.plan_steps[i]["status"] = "running"

    def _mark_done(self, step):
        """Пометить шаг как выполненный."""
        idx = step - 1
        if 0 <= idx < len(self.plan_steps):
            self.plan_steps[idx]["status"] = "done"

    # ─── Animation ────────────────────────────────────────

    async def _animate(self):
        """Анимация статусного сообщения пока инструмент работает."""
        try:
            while not self.is_finished and self.current_tool:
                await asyncio.sleep(1.0)
                if self.is_finished or not self.current_tool:
                    break
                text = self._render()
                await self._force_edit(text)
        except asyncio.CancelledError:
            pass

    def _get_tool_frames(self, tool_name):
        """Подбор анимации по типу инструмента."""
        t = tool_name.lower()
        if any(k in t for k in ("search", "tavily", "find", "google")):
            return self.search_anim
        if any(k in t for k in ("command", "execute", "python", "code", "terminal")):
            return self.code_anim
        if any(k in t for k in ("file", "read", "write", "list", "download", "upload", "send")):
            return self.file_anim
        if any(k in t for k in ("memory", "profile", "diary", "reminder", "note")):
            return self.memory_anim
        if any(k in t for k in ("visit", "fetch", "url", "web", "page")):
            return self.web_anim
        if any(k in t for k in ("video", "audio", "image", "ocr", "transcribe", "photo")):
            return self.media_anim
        return self.moon

    # ─── Helpers ──────────────────────────────────────────

    async def _throttled_edit(self, text):
        """Редактирование с троттлингом."""
        now = time.time()
        if now - self.last_edit_time < self.min_interval:
            return
        await self._force_edit(text)

    async def _force_edit(self, text):
        """Принудительное обновление статусного сообщения."""
        if self.status_msg_id:
            await self._safe_edit(self.status_msg_id, text)
            self.last_edit_time = time.time()

    async def _delete_status(self):
        """Удаляет статусное сообщение."""
        if self.status_msg_id:
            try:
                await self.bot.delete_message(
                    chat_id=self.chat_id, message_id=self.status_msg_id
                )
            except Exception:
                pass
            self.status_msg_id = None

    async def _safe_edit(self, msg_id, text, parse_mode=constants.ParseMode.MARKDOWN):
        """Безопасное редактирование."""
        if not msg_id:
            return
        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=msg_id,
                text=text[:4096],
                parse_mode=parse_mode,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                try:
                    await self.bot.edit_message_text(
                        chat_id=self.chat_id,
                        message_id=msg_id,
                        text=text[:4096],
                    )
                except Exception:
                    pass
        except RetryAfter as e:
            await asyncio.sleep(min(e.retry_after, 5))
        except Exception:
            pass

    async def _safe_send(self, text):
        """Безопасная отправка."""
        try:
            return await self.bot.send_message(
                chat_id=self.chat_id,
                text=text[:4096],
                parse_mode=constants.ParseMode.MARKDOWN,
            )
        except Exception:
            try:
                return await self.bot.send_message(
                    chat_id=self.chat_id, text=text[:4096]
                )
            except Exception:
                return None

    @staticmethod
    def _esc(text):
        """Экранирование Markdown спецсимволов."""
        for ch in ["_", "*", "`", "["]:
            text = text.replace(ch, "\\" + ch)
        return text
