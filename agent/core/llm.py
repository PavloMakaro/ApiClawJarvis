import asyncio
import random
import logging
from openai import AsyncOpenAI
from typing import AsyncGenerator, Union, List, Dict, Any
import config

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_CODES = ("429", "502", "503", "rate_limit", "overloaded", "timeout")


class LLMService:
    def __init__(self):
        # DeepSeek — основной LLM для текста
        self.deepseek_client = AsyncOpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )

    async def get_embedding(self, text: str) -> List[float]:
        """
        Embeddings не поддерживаются DeepSeek API.
        Возвращаем пустой список — сигнал для keyword-поиска.
        """
        return []

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        provider: str = "deepseek",
        temperature: float = 0.7,
        stream: bool = False,
        tools: List[Dict[str, Any]] = None,
        max_tokens: int = None,
    ) -> Union[Any, AsyncGenerator[Any, None]]:
        """
        Генерация ответа через DeepSeek API.
        Возвращает message object (non-stream) или async generator chunks (stream).
        """
        client = self.deepseek_client

        if model == "default":
            model = "deepseek-chat"

        # Формируем kwargs
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        # Retry с экспоненциальным backoff
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.chat.completions.create(**kwargs)

                if stream:
                    async def stream_generator() -> AsyncGenerator[Any, None]:
                        async for chunk in response:
                            yield chunk
                    return stream_generator()
                else:
                    return response.choices[0].message

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_retryable = any(code in error_str for code in RETRY_CODES)

                if attempt < MAX_RETRIES - 1 and is_retryable:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"LLM API error (attempt {attempt + 1}): {e}. Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    continue

                # Последняя попытка или не-retryable ошибка
                logger.error(f"LLM API error (final): {e}")
                if stream:
                    async def error_gen() -> AsyncGenerator[Any, None]:
                        return
                        yield  # make it a generator
                    return error_gen()
                raise

        # Shouldn't reach here, but just in case
        raise last_error
