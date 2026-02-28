import asyncio
import logging
import html
from telegram import constants
from telegram.error import BadRequest, RetryAfter

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
#  Символы и константы
# ──────────────────────────────────────────────────────────────────────────────

_MOON    = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
_DONE    = "✓"
_PENDING = "·"
_DIVIDER = "─" * 16

# Telegram: ~20 правок/мин. 2.8s — безопасный интервал.
_REFRESH = 2.8


class TelegramRenderer:
    """Минималистичный UI-рендерер для Telegram."""

    def __init__(self, bot, chat_id):
        self.bot     = bot
        self.chat_id = chat_id

        self.status_msg_id = None
        self.final_msg_id  = None

        self.is_finished  = False
        self.final_text   = ""
        self.thought_text = ""
        self.display_mode = "status"   # "status" | "final"

        self.plan_items         = []   # список dict: {id, text, parent, status, subs:[]}
        self.current_step       = 0
        self.total_steps        = 0
        self.current_tool       = ""
        self.current_plan_step_id = None

        self.refresh_rate   = _REFRESH
        self.ui_task        = None
        self.last_sent_text = ""
        self._frame         = 0   # счётчик кадров — каждый refresh +1

    # ─── Public API ───────────────────────────────────────────────────────────

    async def start(self):
        try:
            msg = await self.bot.send_message(
                chat_id=self.chat_id,
                text=self._idle_frame(),
                parse_mode=constants.ParseMode.HTML,
            )
            self.status_msg_id = msg.message_id
            self.ui_task = asyncio.create_task(self._ui_loop())
        except Exception as e:
            logger.error(f"Renderer start error: {e}")

    async def stop(self):
        """Чистая остановка при отмене задачи."""
        self.is_finished = True
        if self.ui_task and not self.ui_task.done():
            self.ui_task.cancel()
            try:
                await self.ui_task
            except asyncio.CancelledError:
                pass
        await self._delete_status()

    async def set_plan(self, plan_items: list, total: int):
        """Предзаполнить чеклист шагов до начала выполнения.
        plan_items — список dict {id, text, parent, status} из agent._parse_plan_steps.
        """
        self.total_steps = total
        # Строим внутреннюю структуру: главные пункты с полем subs
        self.plan_items = []
        for item in plan_items:
            if item.get("parent") is None:
                self.plan_items.append({
                    "id":     item["id"],
                    "text":   item["text"],
                    "parent": None,
                    "status": "pending",
                    "subs":   [],
                })
            else:
                # Добавляем подпункт из плана к соответствующему главному пункту
                parent_id = item["parent"]
                for p in self.plan_items:
                    if p["id"] == parent_id:
                        p["subs"].append({
                            "id":     item["id"],
                            "text":   item["text"],
                            "status": "pending",
                        })
                        break
        await self._render_and_send()

    async def update(self, status_type, content):
        if self.is_finished:
            return

        if status_type == "thinking_stream":
            self.thought_text = content
        elif status_type == "plan_step_start":
            self._handle_plan_step_start(content if isinstance(content, str) else str(content))
        elif status_type == "tool_use":
            self._handle_tool_use(content)
        elif status_type == "observation":
            self._handle_observation()
        elif status_type == "final_stream":
            self.display_mode = "final"
            self.final_text += content
        elif status_type == "final":
            self.is_finished = True
            self.final_text = content or self.final_text
            await self._force_final_render()
        elif status_type == "error":
            self.is_finished = True
            await self._handle_error(content)

    # ─── Background Loop ──────────────────────────────────────────────────────

    async def _ui_loop(self):
        try:
            while not self.is_finished:
                await asyncio.sleep(self.refresh_rate)
                if self.is_finished:
                    break
                self._frame += 1
                await self._render_and_send()
        except asyncio.CancelledError:
            pass

    async def _render_and_send(self):
        if self.display_mode == "status":
            text = self._build_status_ui()
            if text != self.last_sent_text:
                await self._safe_edit(self.status_msg_id, text, constants.ParseMode.HTML)
                self.last_sent_text = text

        elif self.display_mode == "final":
            display = self._fix_markdown(self.final_text)[:4000]
            if display != self.last_sent_text:
                if not self.final_msg_id:
                    await self._delete_status()
                    msg = await self._safe_send(display or "…", constants.ParseMode.MARKDOWN)
                    if msg:
                        self.final_msg_id = msg.message_id
                else:
                    await self._safe_edit(self.final_msg_id, display, constants.ParseMode.MARKDOWN)
                self.last_sent_text = display

    async def _force_final_render(self):
        if self.ui_task:
            self.ui_task.cancel()
        await self._delete_status()

        display = self._fix_markdown(self.final_text)[:4000] or "Готово."
        if self.final_msg_id:
            await self._safe_edit(self.final_msg_id, display, constants.ParseMode.MARKDOWN)
        else:
            await self._safe_send(display, constants.ParseMode.MARKDOWN)

    async def handle_plan_step_start(self, step_id: str):
        """Публичный метод — вызывается из bot.py при получении plan_step_start события."""
        self._handle_plan_step_start(step_id)

    # ─── State ────────────────────────────────────────────────────────────────

    def _handle_plan_step_start(self, step_id: str):
        """Пометить пункт плана как running, предыдущий running → done."""
        self.current_plan_step_id = step_id
        for item in self.plan_items:
            if item["id"] == step_id:
                if item["status"] != "done":
                    item["status"] = "running"
            elif item["status"] == "running":
                item["status"] = "done"
                # Также завершаем все незавершённые подпункты
                for sub in item.get("subs", []):
                    if sub["status"] == "running":
                        sub["status"] = "done"

    def _handle_tool_use(self, content):
        if isinstance(content, dict):
            tool_name         = content.get("tool", "")
            step              = content.get("step", 0)
            total             = content.get("total_steps", 0)
            plan_step_id      = content.get("plan_step_id")
        else:
            tool_name    = str(content)
            step = total = 0
            plan_step_id = None

        self.current_tool = tool_name
        if step  > 0: self.current_step = step
        if total > 0: self.total_steps  = total

        if plan_step_id and self.plan_items:
            # Режим иерархического плана — добавляем tool как подпункт
            self._add_tool_subtask(plan_step_id, tool_name)
        elif self.current_step > 0:
            # Fallback: старый плоский режим
            self._update_plan(tool_name, self.current_step)

    def _handle_observation(self):
        if self.current_plan_step_id and self.plan_items:
            # Отмечаем последний running подпункт как done
            for item in self.plan_items:
                if item["id"] == self.current_plan_step_id:
                    for sub in reversed(item.get("subs", [])):
                        if sub["status"] == "running":
                            sub["status"] = "done"
                            break
                    break
        elif self.current_step > 0:
            self._mark_done(self.current_step)
        self.current_tool = ""

    async def _handle_error(self, content):
        if self.ui_task:
            self.ui_task.cancel()
        text = (
            f"<b>Ошибка</b>\n"
            f"{_DIVIDER}\n"
            f"<code>{html.escape(str(content)[:400])}</code>"
        )
        target = self.status_msg_id
        if target:
            await self._safe_edit(target, text, constants.ParseMode.HTML)
        else:
            await self._safe_send(text, constants.ParseMode.HTML)

    # ─── UI Builder ───────────────────────────────────────────────────────────

    def _moon(self) -> str:
        return _MOON[self._frame % len(_MOON)]

    def _idle_frame(self):
        return f"{_MOON[0]}  <b>ДЖАРВИС</b>\n{_DIVIDER}"

    def _build_status_ui(self):
        lines = []
        moon = self._moon()

        # Заголовок — одна луна, меняет фазу каждый refresh
        lines.append(f"{moon}  <b>ДЖАРВИС</b>")
        lines.append(_DIVIDER)

        # Монолог
        if self.thought_text:
            raw  = self.thought_text.strip().split("\n")
            snip = " ".join(raw[-2:])[:100]
            lines.append(f"<i>{html.escape(snip)}</i>")
            lines.append("")

        if self.plan_items:
            # ── Иерархический план ──
            # self.plan_items содержит только главные пункты; подпункты в item["subs"]
            done_count = sum(1 for s in self.plan_items if s["status"] == "done")
            total      = max(len(self.plan_items), self.total_steps)

            for item in self.plan_items:
                name = html.escape(item["text"])
                if item["status"] == "done":
                    lines.append(f"{_DONE}  <s>{name}</s>")
                elif item["status"] == "running":
                    lines.append(f"{moon}  <b>{name}</b>")
                else:
                    lines.append(f"{_PENDING}  <i>{name}</i>")

                # Подпункты (инструменты + подпункты из плана)
                for sub in item.get("subs", []):
                    sub_name = html.escape(sub["text"])
                    if sub["status"] == "done":
                        lines.append(f"   {_DONE}  <s>{sub_name}</s>")
                    elif sub["status"] == "running":
                        lines.append(f"   {moon}  {sub_name}")
                    else:
                        lines.append(f"   {_PENDING}  <i>{sub_name}</i>")

            if total > 0:
                pct = int(done_count / total * 100)
                filled = round(done_count / total * 10)
                bar = "▰" * filled + "▱" * (10 - filled)
                lines.append(f"\n<code>{bar}  {pct}%</code>")

        elif self.current_tool:
            lines.append(f"{moon}  <b>{html.escape(self.current_tool)}</b>")

        else:
            lines.append(f"{moon}  <i>Анализирую...</i>")

        return "\n".join(lines)

    # ─── Markdown fixer ───────────────────────────────────────────────────────

    @staticmethod
    def _fix_markdown(text: str) -> str:
        """Чистит текст для Telegram Markdown."""
        import re
        # Убираем markdown-заголовки (### ## #) — Telegram их не поддерживает
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # ** → * (Telegram использует одинарные звёздочки)
        text = text.replace("**", "*")
        # Закрываем незакрытые блоки кода
        if text.count("```") % 2 != 0:
            text += "\n```"
        elif text.count("`") % 2 != 0:
            text += "`"
        # Закрываем незакрытое форматирование
        if text.count("*") % 2 != 0:
            text += "*"
        if text.count("_") % 2 != 0:
            text += "_"
        return text

    # ─── Plan data ────────────────────────────────────────────────────────────

    def _add_tool_subtask(self, plan_step_id: str, tool_name: str):
        """Добавить tool call как подпункт к активному пункту плана."""
        for item in self.plan_items:
            if item["id"] == plan_step_id:
                # Убедиться что пункт активен
                if item["status"] != "done":
                    item["status"] = "running"
                item["subs"].append({"text": tool_name, "status": "running"})
                break

    def _update_plan(self, tool_name: str, step: int):
        """Fallback: плоский режим (план без иерархии)."""
        target = max(step, self.total_steps)
        while len(self.plan_items) < target:
            idx = len(self.plan_items) + 1
            self.plan_items.append({
                "id": str(idx), "text": "…", "parent": None,
                "status": "pending", "subs": [],
            })

        for i, s in enumerate(self.plan_items):
            if i < step - 1:
                if s["status"] != "done":
                    s["status"] = "done"
            elif i == step - 1:
                if s["text"] in ("…", "Ожидание"):
                    s["text"] = tool_name
                s["status"] = "running"

    def _mark_done(self, step: int):
        idx = step - 1
        if 0 <= idx < len(self.plan_items):
            self.plan_items[idx]["status"] = "done"

    # ─── Telegram API ─────────────────────────────────────────────────────────

    async def _delete_status(self):
        if self.status_msg_id:
            try:
                await self.bot.delete_message(
                    chat_id=self.chat_id, message_id=self.status_msg_id
                )
            except Exception:
                pass
            self.status_msg_id = None

    async def _safe_edit(self, msg_id, text, p_mode):
        if not msg_id:
            return
        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=msg_id,
                text=text,
                parse_mode=p_mode,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                try:
                    await self.bot.edit_message_text(
                        chat_id=self.chat_id, message_id=msg_id, text=text
                    )
                except Exception:
                    pass
        except RetryAfter as e:
            self.refresh_rate = max(self.refresh_rate, e.retry_after + 0.5)
        except Exception:
            pass

    async def _safe_send(self, text, p_mode):
        try:
            return await self.bot.send_message(
                chat_id=self.chat_id, text=text, parse_mode=p_mode
            )
        except Exception:
            try:
                return await self.bot.send_message(chat_id=self.chat_id, text=text)
            except Exception:
                return None
