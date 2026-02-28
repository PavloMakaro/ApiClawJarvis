import json
import re
import asyncio
import logging
from core.llm import LLMService

logger = logging.getLogger(__name__)

# Лимиты обрезки результатов инструментов
TOOL_RESULT_LIMITS = {
    "tavily_deep_research": 5000,
    "read_file": 4000,
    "visit_page": 4000,
    "fetch_url": 4000,
    "execute_command": 3000,
}
DEFAULT_RESULT_LIMIT = 1500

# Порог для активации плана (кол-во шагов)
PLAN_MODE_THRESHOLD = 8

# Промпт для фазы планирования (вставляется как доп. system message)
PLANNING_PROMPT = (
    "Перед выполнением задачи выведи ТОЛЬКО нумерованный иерархический список шагов. "
    "Никаких инструментов, никаких пояснений. Только список:\n"
    "1. Главный шаг\n"
    "   1.1. Подшаг\n"
    "   1.2. Подшаг\n"
    "2. Главный шаг\n"
    "   2.1. Подшаг\n"
    "...\nЗатем остановись."
)

# Напоминание агенту о плане — вставляется в execution phase
_PLAN_REMINDER_TEMPLATE = (
    "Ты выполняешь план. При переходе к новому главному пункту пиши [ШАГ N] "
    "в начале своих мыслей (например [ШАГ 1], [ШАГ 2]).\n"
    "План:\n{plan_text}"
)


def _count_plan_steps(text):
    """Считает главные нумерованные шаги в тексте плана."""
    steps = re.findall(r'^\d+[.)]\s', text, re.MULTILINE)
    return len(steps) if steps else 0


def _parse_plan_steps(text):
    """
    Извлекает иерархию шагов из нумерованного списка.
    Возвращает список dict: {id, text, parent, status}
    """
    items = []
    for line in text.split('\n'):
        stripped = line.strip()
        # Подпункт: 1.1. или 1.1) — с отступом в исходной строке
        sub_m = re.match(r'^(\d+)\.(\d+)[.)]\s+(.+)', stripped)
        if sub_m:
            parent_id = sub_m.group(1)
            sub_num = sub_m.group(2)
            step_id = f"{parent_id}.{sub_num}"
            items.append({
                "id": step_id,
                "text": sub_m.group(3).strip(),
                "parent": parent_id,
                "status": "pending",
            })
            continue
        # Главный пункт: 1. или 1)
        main_m = re.match(r'^(\d+)[.)]\s+(.+)', stripped)
        if main_m:
            step_id = main_m.group(1)
            items.append({
                "id": step_id,
                "text": main_m.group(2).strip(),
                "parent": None,
                "status": "pending",
            })
    return items


class Agent:
    def __init__(self, tools_registry, system_prompt=None):
        self.llm = LLMService()
        self.tools = tools_registry

        if not system_prompt:
            try:
                with open("system_prompt.txt", "r", encoding="utf-8") as f:
                    self.system_prompt = f.read()
            except Exception as e:
                logger.error(f"Error loading system prompt: {e}")
                self.system_prompt = "You are a helpful AI agent. Speak Russian."
        else:
            self.system_prompt = system_prompt

    def _build_prompt(self, history, plan_steps_list=None):
        """Формирует сообщения для API. Если есть план — вставляет напоминание."""
        messages = [{"role": "system", "content": self.system_prompt}]

        if plan_steps_list:
            main_steps = [s for s in plan_steps_list if s["parent"] is None]
            plan_text = "\n".join(f"{s['id']}. {s['text']}" for s in main_steps)
            reminder = _PLAN_REMINDER_TEMPLATE.format(plan_text=plan_text)
            messages.append({"role": "system", "content": reminder})

        messages.extend(history)
        return messages

    async def run(self, user_input, history=None, tool_context=None, plan_mode=True):
        """
        Основной ReAct-цикл. Yields status updates асинхронно.
        """
        if history is None:
            history = []

        # Добавить user input если его нет
        if not history or history[-1].get("role") != "user":
            history.append({"role": "user", "content": user_input})

        max_turns = 25  # Разумный лимит (экономия токенов)
        turn = 0
        plan_step = 0
        total_steps = 0
        plan_steps_list = []
        current_plan_step_id = None

        definitions = self.tools.get_definitions()

        # ─── Фаза планирования (только если plan_mode=True) ───────────────────
        if plan_mode:
            yield {"status": "thinking", "message": "Составляю план..."}
            planning_messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "system", "content": PLANNING_PROMPT},
            ]
            planning_messages.extend(history)
            try:
                plan_response = await self.llm.generate(
                    planning_messages,
                    stream=False,
                    tools=None,        # Без схемы инструментов — чистый текст
                    temperature=0.2,
                    max_tokens=512
                )
                plan_text = plan_response.content if plan_response else ""
            except Exception as e:
                logger.warning(f"Plan phase failed: {e}")
                plan_text = ""

            if plan_text:
                plan_steps_list = _parse_plan_steps(plan_text)
                main_steps = [s for s in plan_steps_list if s["parent"] is None]
                total_steps = len(main_steps)
                # Активируем план если >= PLAN_MODE_THRESHOLD подпунктов или >= 3 главных с подпунктами
                sub_count = len(plan_steps_list) - len(main_steps)
                has_subs = sub_count > 0
                activate = (len(plan_steps_list) >= PLAN_MODE_THRESHOLD) or (len(main_steps) >= 3 and has_subs)
                if activate:
                    yield {
                        "status": "plan_ready",
                        "plan_steps": plan_steps_list,
                        "total_steps": total_steps,
                    }
                else:
                    # Задача простая — сбрасываем, выполняем обычным способом
                    plan_steps_list = []
                    total_steps = 0
        # ──────────────────────────────────────────────────────────────────────

        while turn < max_turns:
            turn += 1
            yield {"status": "thinking", "message": f"Анализирую... (шаг {turn})"}

            # 1. Вызов LLM со стримингом
            messages = self._build_prompt(history, plan_steps_list if plan_steps_list else None)

            try:
                stream_gen = await self.llm.generate(
                    messages,
                    stream=True,
                    tools=definitions,
                    temperature=0.3,
                    max_tokens=4096
                )
            except Exception as e:
                logger.error(f"LLM generate failed: {e}")
                yield {"status": "error", "message": f"Ошибка LLM: {e}"}
                yield {"status": "final", "content": f"Произошла ошибка при обращении к AI: {e}"}
                return

            response_content = ""
            tool_calls_buffer = []
            content_chunks = []  # Буфер текстовых чанков — отправим после стрима

            try:
                async for chunk in stream_gen:
                    delta = None
                    if hasattr(chunk, 'choices') and chunk.choices:
                        delta = chunk.choices[0].delta

                    if delta:
                        # Текстовый контент — буферизуем, не отправляем сразу
                        if delta.content:
                            response_content += delta.content
                            content_chunks.append(delta.content)

                        # Tool calls
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                if tc.index is not None:
                                    while len(tool_calls_buffer) <= tc.index:
                                        tool_calls_buffer.append({
                                            "id": "",
                                            "function": {"name": "", "arguments": ""},
                                            "type": "function"
                                        })

                                    current_tc = tool_calls_buffer[tc.index]
                                    if tc.id:
                                        current_tc["id"] += tc.id
                                    if tc.function:
                                        if tc.function.name:
                                            current_tc["function"]["name"] += tc.function.name
                                        if tc.function.arguments:
                                            current_tc["function"]["arguments"] += tc.function.arguments

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Stream error: {e}")

            # Определяем тип контента: промежуточные мысли или финальный ответ
            if response_content and tool_calls_buffer:
                # Есть tool calls → это промежуточные мысли агента
                yield {"status": "thinking_stream", "content": response_content}
                # Парсим [ШАГ N] для привязки к пункту плана
                if plan_steps_list:
                    step_match = re.search(r'\[ШАГ\s+(\d+(?:\.\d+)?)\]', response_content)
                    if step_match:
                        new_step_id = step_match.group(1)
                        if new_step_id != current_plan_step_id:
                            current_plan_step_id = new_step_id
                            step_text = next(
                                (s["text"] for s in plan_steps_list if s["id"] == current_plan_step_id),
                                ""
                            )
                            yield {
                                "status": "plan_step_start",
                                "step_id": current_plan_step_id,
                                "step_text": step_text,
                            }
            elif response_content and not tool_calls_buffer:
                # Нет tool calls → финальный ответ, стримим чанками
                for chunk_text in content_chunks:
                    yield {"status": "final_stream", "content": chunk_text}

            # Собираем assistant message
            assistant_msg = {"role": "assistant", "content": response_content}
            if tool_calls_buffer:
                assistant_msg["tool_calls"] = tool_calls_buffer
            history.append(assistant_msg)

            # Fallback: парсим шаги из первого ответа если planning phase не дала результата
            if total_steps == 0 and response_content:
                fallback_count = _count_plan_steps(response_content)
                if fallback_count > 0:
                    plan_steps_list = _parse_plan_steps(response_content)
                    main_steps = [s for s in plan_steps_list if s["parent"] is None]
                    total_steps = len(main_steps)

            # 2. Выполнение tool calls
            if tool_calls_buffer:
                tasks = []
                calls_metadata = []

                for tool_call in tool_calls_buffer:
                    func_name = tool_call["function"]["name"]
                    args_str = tool_call["function"]["arguments"]
                    call_id = tool_call["id"]

                    try:
                        args = json.loads(args_str)
                    except (json.JSONDecodeError, Exception):
                        args = {}

                    plan_step += 1
                    yield {
                        "status": "tool_use",
                        "tool": func_name,
                        "args": args,
                        "step": plan_step,
                        "total_steps": total_steps,
                        "plan_step_id": current_plan_step_id,
                    }
                    calls_metadata.append({"id": call_id, "name": func_name})

                    async def execute_tool_safe(name, arguments):
                        try:
                            if self.tools.is_async(name):
                                res = self.tools.execute(name, tool_context=tool_context, **arguments)
                                if asyncio.iscoroutine(res):
                                    return await asyncio.wait_for(res, timeout=120)
                                return res
                            else:
                                return await asyncio.wait_for(
                                    asyncio.to_thread(
                                        self.tools.execute, name, tool_context=tool_context, **arguments
                                    ),
                                    timeout=120
                                )
                        except asyncio.TimeoutError:
                            return f"Error: Tool '{name}' timed out after 120s"
                        except Exception as e:
                            return f"Error executing tool '{name}': {str(e)}"

                    tasks.append(execute_tool_safe(func_name, args))

                # Параллельное выполнение
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, result in enumerate(results):
                    meta = calls_metadata[i]
                    func_name = meta["name"]
                    call_id = meta["id"]

                    if isinstance(result, Exception):
                        result_str = f"Error: {str(result)}"
                    else:
                        result_str = str(result)

                    # Динамическая обрезка результатов
                    max_len = TOOL_RESULT_LIMITS.get(func_name, DEFAULT_RESULT_LIMIT)
                    if len(result_str) > max_len:
                        result_str = result_str[:max_len] + f"... (обрезано, было {len(result_str)} символов)"

                    history.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": result_str,
                        "name": func_name
                    })

                    yield {"status": "observation", "result": f"Tool '{func_name}':\n{result_str}"}

            else:
                # Нет tool calls = финальный ответ
                yield {"status": "final", "content": response_content}
                return

        yield {"status": "final", "content": "Ошибка: достигнут лимит итераций агента."}
