"""
AI Service для интеграции с OpenRouter API
"""
import os
import logging
from typing import List, Dict, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class AIService:
    """Сервис для работы с AI через OpenRouter API"""
    
    SYSTEM_PROMPT = """Ты ассистент эмоциональной и психологической поддержки.

Твоя задача — помочь пользователю почувствовать понимание и поддержку.

Правила ответа:
- всегда отвечай по-русски;
- сначала покажи понимание чувств пользователя;
- отвечай спокойно и доброжелательно;
- не ставь диагнозы;
- не говори, что ты врач или психолог;
- не давай категоричных советов;
- предлагай мягкие способы самопомощи;
- отвечай кратко и понятно;
- не перегружай длинными текстами;
- поддерживай диалог вопросами, если уместно;
- в кризисных ситуациях мягко советуй обратиться к специалисту или в службу помощи.
"""
    
    FALLBACK_RESPONSE = """Извините, сейчас возникли технические сложности с подключением к AI-ассистенту. 
Пожалуйста, попробуйте позже или выберите другую опцию в меню."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = "https://openrouter.ai/api/v1/chat/completions",
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        timeout: int = 30,
        max_history: int = 10
    ):
        """
        Инициализация AI сервиса
        
        Args:
            api_key: API ключ OpenRouter (если None, берется из OPENROUTER_API_KEY)
            api_url: URL API endpoint
            model: Модель для использования
            max_tokens: Максимальная длина ответа
            temperature: Temperature для генерации (0-1)
            timeout: Таймаут запроса в секундах
            max_history: Максимальное количество сообщений в истории
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.api_url = api_url
        self.model = model or os.getenv("OPENROUTER_MODEL", "google/gemini-flash-1.5")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.max_history = max_history
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not found in environment variables")
    
    def _build_messages(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Построить список сообщений для API
        
        Args:
            history: История диалога
            
        Returns:
            Список сообщений с system prompt
        """
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        
        # Ограничиваем историю
        recent_history = history[-self.max_history:] if len(history) > self.max_history else history
        
        messages.extend(recent_history)
        return messages
    
    async def generate_reply(
        self,
        user_message: str,
        history: List[Dict[str, str]]
    ) -> str:
        """
        Сгенерировать ответ от AI
        
        Args:
            user_message: Сообщение пользователя
            history: История диалога (список словарей с role и content)
            
        Returns:
            Ответ AI или fallback сообщение при ошибке
        """
        if not self.api_key:
            logger.error("Cannot generate AI reply: API key not configured")
            return self.FALLBACK_RESPONSE
        
        # Добавляем текущее сообщение пользователя
        current_history = history + [{"role": "user", "content": user_message}]
        messages = self._build_messages(current_history)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/PsychoTeleBot",
                        "X-Title": "PsychoTeleBot"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Извлекаем ответ
                if "choices" in data and len(data["choices"]) > 0:
                    ai_reply = data["choices"][0]["message"]["content"].strip()
                    
                    if not ai_reply:
                        logger.warning("AI returned empty response")
                        return self.FALLBACK_RESPONSE
                    
                    return ai_reply
                else:
                    logger.error(f"Unexpected API response structure: {data}")
                    return self.FALLBACK_RESPONSE
                    
        except httpx.TimeoutException:
            logger.error(f"AI API timeout after {self.timeout}s")
            return "Извините, ответ AI занимает слишком много времени. Пожалуйста, попробуйте еще раз."
            
        except httpx.HTTPStatusError as e:
            logger.error(f"AI API HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            
            if e.response.status_code == 429:
                return "Превышен лимит запросов к AI. Пожалуйста, попробуйте через несколько минут."
            elif e.response.status_code == 401:
                return self.FALLBACK_RESPONSE
            else:
                return self.FALLBACK_RESPONSE
                
        except httpx.RequestError as e:
            logger.error(f"AI API request error: {type(e).__name__} - {str(e)[:200]}")
            return self.FALLBACK_RESPONSE
            
        except Exception as e:
            logger.error(f"Unexpected error in AI service: {type(e).__name__} - {str(e)[:200]}")
            return self.FALLBACK_RESPONSE
    
    def sync_generate_reply(
        self,
        user_message: str,
        history: List[Dict[str, str]]
    ) -> str:
        """
        Синхронная версия generate_reply (для совместимости)
        
        Args:
            user_message: Сообщение пользователя
            history: История диалога
            
        Returns:
            Ответ AI
        """
        import asyncio
        import threading

        def _run_in_new_thread(coro):
            result_container = {}
            error_container = {}

            def runner():
                try:
                    result_container["result"] = asyncio.run(coro)
                except Exception as exc:
                    error_container["error"] = exc

            thread = threading.Thread(target=runner)
            thread.start()
            thread.join()

            if "error" in error_container:
                raise error_container["error"]
            return result_container.get("result", self.FALLBACK_RESPONSE)

        try:
            asyncio.get_running_loop()
            # Если есть running loop, выполняем корутину в отдельном потоке
            return _run_in_new_thread(self.generate_reply(user_message, history))
        except RuntimeError:
            # Нет активного loop — можно безопасно выполнить синхронно
            return asyncio.run(self.generate_reply(user_message, history))



def generate_ai_reply(user_id: int, user_message: str, history: List[Dict[str, str]] = None) -> str:
    """
    Функция-обертка для генерации AI ответа
    
    Args:
        user_id: ID пользователя (для логирования)
        user_message: Сообщение пользователя
        history: История диалога (опционально)
        
    Returns:
        Ответ AI
    """
    if history is None:
        history = []
    
    ai_service = AIService()
    
    try:
        return ai_service.sync_generate_reply(user_message, history)
    except Exception as e:
        logger.error(f"Error generating AI reply for user {user_id}: {type(e).__name__}")
        return AIService.FALLBACK_RESPONSE
