"""
AI Service для интеграции с OpenRouter API
"""
import os
import json
import logging
import threading
import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import deque
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

MEMORY_LAST_MESSAGES_LIMIT = int(os.getenv("MEMORY_LAST_MESSAGES", "8"))
SUMMARY_UPDATE_EVERY = int(os.getenv("MEMORY_SUMMARY_EVERY", "12"))
MEMORY_STORE_PATH = os.getenv("MEMORY_STORE_PATH")

RATE_LIMIT_MESSAGE = "Подожди пару секунд, я ещё отвечаю 🙂"
MIN_INTERVAL_SECONDS = float(os.getenv("RATE_MIN_INTERVAL_SECONDS", "4"))
MAX_PER_MINUTE = int(os.getenv("RATE_MAX_PER_MINUTE", "12"))
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "1200"))
MAX_RESPONSE_LENGTH = int(os.getenv("MAX_RESPONSE_LENGTH", "1200"))
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes")
if "PYTEST_CURRENT_TEST" in os.environ:
    RATE_LIMIT_ENABLED = False


@dataclass
class UserMemory:
    summary: str = ""
    last_messages: List[Dict[str, str]] = field(default_factory=list)
    message_count: int = 0


@dataclass
class RateState:
    last_request_at: float = 0.0
    window: deque = field(default_factory=deque)
    last_message: str = ""
    last_response: str = ""


_MEMORY_STORE: Dict[str, UserMemory] = {}
_MEMORY_LOADED = False
_RATE_STATE: Dict[str, RateState] = {}

SMALL_TALK = {
    "привет",
    "приветик",
    "привет!",
    "здорово",
    "здарова",
    "здравствуй",
    "здравствуйте",
    "добрый день",
    "добрый вечер",
    "доброе утро",
    "ку",
    "куку",
    "ку-ку",
    "ку!",
    "ку-ку!",
    "хай",
    "hello",
    "hi",
    "hey",
    "йо",
    "салют",
    "спасибо",
    "спс",
    "спасиб",
    "благодарю",
    "мерси",
    "thx",
    "thanks",
    "ок",
    "окей",
    "окей!",
    "ок))",
    "ок.",
    "ок!",
    "ok",
    "okay",
    "k",
    "понял",
    "поняла",
    "понятно",
    "ясно",
    "хорошо",
    "ладно",
    "ага",
    "угу",
    "мм",
    "ммм",
    "мяу",
    "мяу!",
    "мяу-мяу",
    "мяу мяу",
    "мяу?",
    "=)",
    ":)",
    ":-)",
    ":D",
    ":-D",
    "😉",
    "😅",
    "😊",
    "🙂",
    "🙃",
    "🥺",
    "👍"
}

SMALL_TALK_REPLIES = [
    "Спасибо! Я рядом 🙂",
    "Хорошо, я на связи.",
    "Понял. Хочешь рассказать подробнее?",
    "Ок. Если нужна поддержка — напиши.",
    "Привет! Как ты сейчас себя чувствуешь?"
]

CRISIS_KEYWORDS = [
    "покончу с собой",
    "покончить с собой",
    "хочу покончить с собой",
    "хочу умереть",
    "хочу уйти из жизни",
    "хочу исчезнуть навсегда",
    "нет смысла жить",
    "нет смысла жить дальше",
    "жить не хочу",
    "не хочу жить",
    "лучше умереть",
    "лучше бы умер",
    "лучше бы умерла",
    "не вижу смысла жить",
    "все бессмысленно",
    "всё бессмысленно",
    "мне конец",
    "хочу навредить себе",
    "хочу причинить себе вред",
    "сделаю себе больно",
    "порезаться",
    "порежусь",
    "перережу",
    "суицид",
    "суицидальные мысли",
    "суицидальный",
    "свести счёты с жизнью",
    "свести счеты с жизнью",
    "устал жить",
    "устала жить",
    "не могу так больше",
    "сил больше нет",
    "роскомнадзорнуться"
]

CRISIS_RESPONSE = (
    "Мне очень жаль, что ты чувствуешь себя так плохо. Я понимаю, что сейчас тебе очень тяжело "
    "и кажется, что выхода нет. Но я хочу сказать, что ты не одинок и есть люди, которые готовы "
    "тебя поддержать.\n\n"
    "Важно помнить, что кризисные состояния проходят, даже если сейчас это кажется невозможным. "
    "Ты заслуживаешь поддержки и помощи.\n\n"
    "Если ты находишься в России, можешь позвонить на бесплатную горячую линию по телефону "
    "8-800-2000-122. Они работают круглосуточно и помогут тебе найти поддержку.\n\n"
    "Если ты в другой стране, можешь найти экстренные контакты здесь: https://findahelpline.com\n\n"
    "Пожалуйста, не оставляй эту ситуацию без внимания. Позвони кому-то из близких или специалисту, "
    "кто сможет помочь тебе прямо сейчас. Ты важен и твоя жизнь имеет ценность."
)


def _normalize_message(text: str) -> str:
    cleaned = text.strip().lower()
    for ch in ["!", ".", ",", "?", "…", ":", ";"]:
        cleaned = cleaned.replace(ch, "")
    return cleaned


def _is_crisis_message(text: str) -> bool:
    normalized = _normalize_message(text)
    return any(phrase in normalized for phrase in CRISIS_KEYWORDS)


def _load_memory_store() -> None:
    global _MEMORY_LOADED
    if _MEMORY_LOADED or not MEMORY_STORE_PATH:
        return

    if not os.path.exists(MEMORY_STORE_PATH):
        _MEMORY_LOADED = True
        return

    try:
        with open(MEMORY_STORE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for user_id, data in raw.items():
            _MEMORY_STORE[user_id] = UserMemory(
                summary=data.get("summary", ""),
                last_messages=data.get("last_messages", []),
                message_count=data.get("message_count", 0)
            )
        _MEMORY_LOADED = True
    except Exception as e:
        logger.error(f"Failed to load memory store: {type(e).__name__} - {str(e)[:200]}")
        _MEMORY_LOADED = True


def _save_memory_store() -> None:
    if not MEMORY_STORE_PATH:
        return

    try:
        data = {
            user_id: {
                "summary": memory.summary,
                "last_messages": memory.last_messages,
                "message_count": memory.message_count
            }
            for user_id, memory in _MEMORY_STORE.items()
        }
        with open(MEMORY_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save memory store: {type(e).__name__} - {str(e)[:200]}")


def get_user_memory(user_id: str) -> UserMemory:
    _load_memory_store()
    user_id = str(user_id)
    if user_id not in _MEMORY_STORE:
        _MEMORY_STORE[user_id] = UserMemory()
    return _MEMORY_STORE[user_id]


def clear_user_memory(user_id: str) -> None:
    _load_memory_store()
    user_id = str(user_id)
    if user_id in _MEMORY_STORE:
        _MEMORY_STORE[user_id] = UserMemory()
        _save_memory_store()


def clear_user_rate_state(user_id: str) -> None:
    user_id = str(user_id)
    if user_id in _RATE_STATE:
        _RATE_STATE[user_id] = RateState()


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
Если пользователь пишет о самоповреждении или суицидальных намерениях, ответь коротко и эмпатично, порекомендуй обратиться к специалисту или на горячую линию помощи и не пытайся решать медицинские проблемы.
"""
    
    FALLBACK_RESPONSE = """Извините, сейчас возникли технические сложности с подключением к AI-ассистенту. 
Пожалуйста, попробуйте позже или выберите другую опцию в меню."""

    TIMEOUT_RESPONSE = "Сейчас отвечаю медленнее обычного. Попробуй написать ещё раз через минуту."

    SUMMARY_PROMPT = """Ты делаешь краткое резюме разговора с пользователем.
Сожми информацию до 3–5 коротких предложений.
Сохраняй факты о пользователе, его состоянии, предпочтениях и важных событиях.
Не добавляй выдуманных деталей.
Пиши по-русски, кратко и нейтрально."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = "https://openrouter.ai/api/v1/chat/completions",
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        timeout: int = 10,
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
        self.timeout = int(os.getenv("AI_TIMEOUT_SECONDS", str(timeout)))
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
        history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None
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
        
        history = history or []

        if user_id is not None:
            memory = get_user_memory(user_id)
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT}
            ]
            if memory.summary:
                messages.append({
                    "role": "system",
                    "content": f"Краткая память о пользователе: {memory.summary}"
                })
            if memory.last_messages:
                messages.extend(memory.last_messages[-MEMORY_LAST_MESSAGES_LIMIT:])
            messages.append({"role": "user", "content": user_message})
        else:
            # Добавляем текущее сообщение пользователя
            current_history = history + [{"role": "user", "content": user_message}]
            messages = self._build_messages(current_history)
        
        try:
            ai_reply = await self._call_llm(messages, self.max_tokens, self.temperature)

            if MAX_RESPONSE_LENGTH > 0 and len(ai_reply) > MAX_RESPONSE_LENGTH:
                ai_reply = ai_reply[:MAX_RESPONSE_LENGTH].rstrip() + "…"

            if user_id is not None:
                memory = get_user_memory(user_id)
                memory.last_messages.extend([
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": ai_reply}
                ])
                memory.last_messages = memory.last_messages[-MEMORY_LAST_MESSAGES_LIMIT:]
                memory.message_count += 1

                if SUMMARY_UPDATE_EVERY > 0 and (memory.message_count % SUMMARY_UPDATE_EVERY == 0):
                    new_summary = await self._generate_summary(memory.summary, memory.last_messages)
                    if new_summary:
                        memory.summary = new_summary
                _save_memory_store()

            return ai_reply
                    
        except httpx.TimeoutException:
            logger.error(f"AI API timeout after {self.timeout}s")
            return self.TIMEOUT_RESPONSE
            
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

    async def _generate_summary(self, current_summary: str, last_messages: List[Dict[str, str]]) -> str:
        if not last_messages:
            return current_summary

        formatted_dialog = "\n".join(
            [f"{m['role']}: {m['content']}" for m in last_messages]
        )

        summary_request = (
            f"Текущее резюме: {current_summary or 'нет'}\n\n"
            f"Последние сообщения:\n{formatted_dialog}\n\n"
            f"Сделай обновленное краткое резюме пользователя."
        )

        messages = [
            {"role": "system", "content": self.SUMMARY_PROMPT},
            {"role": "user", "content": summary_request}
        ]

        return await self._call_llm(messages, max_tokens=200, temperature=0.2)

    async def _call_llm(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float) -> str:
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
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )

            response.raise_for_status()
            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                raw_content = data["choices"][0]["message"]["content"]
                ai_reply = raw_content.strip() if raw_content else ""
                if not ai_reply:
                    logger.warning("AI returned empty response")
                    return self.FALLBACK_RESPONSE
                return ai_reply

            logger.error(f"Unexpected API response structure: {data}")
            return self.FALLBACK_RESPONSE
    
    def sync_generate_reply(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None
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
            return _run_in_new_thread(self.generate_reply(user_message, history, user_id))
        except RuntimeError:
            # Нет активного loop — можно безопасно выполнить синхронно
            return asyncio.run(self.generate_reply(user_message, history, user_id))



def generate_ai_reply(user_id: str, user_message: str, history: List[Dict[str, str]] = None) -> str:
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

    user_id = str(user_id)
    message_text = user_message or ""
    normalized = _normalize_message(message_text)

    # Проверка длины сообщения
    if len(message_text) > MAX_MESSAGE_LENGTH:
        return f"Сообщение слишком длинное. Пожалуйста, сократите до {MAX_MESSAGE_LENGTH} символов."

    # Инициализируем состояние пользователя
    rate_state = _RATE_STATE.get(user_id) or RateState()
    _RATE_STATE[user_id] = rate_state

    # Кризисные сообщения — отвечаем сразу, без LLM
    if _is_crisis_message(message_text):
        rate_state.last_message = message_text
        rate_state.last_response = CRISIS_RESPONSE
        return CRISIS_RESPONSE

    # Ограничение частоты запросов
    if RATE_LIMIT_ENABLED:
        now = time.time()
        # Минимальная пауза между сообщениями
        if rate_state.last_request_at and (now - rate_state.last_request_at) < MIN_INTERVAL_SECONDS:
            return RATE_LIMIT_MESSAGE

        # Лимит сообщений в минуту
        while rate_state.window and (now - rate_state.window[0]) > 60:
            rate_state.window.popleft()
        if len(rate_state.window) >= MAX_PER_MINUTE:
            return RATE_LIMIT_MESSAGE

        rate_state.last_request_at = now
        rate_state.window.append(now)

    # Быстрые ответы на короткие/служебные сообщения
    if normalized in SMALL_TALK:
        reply = random.choice(SMALL_TALK_REPLIES)
        rate_state.last_message = message_text
        rate_state.last_response = reply
        return reply

    # Кэш последнего ответа на повторный вопрос
    if rate_state.last_message and rate_state.last_message == message_text and rate_state.last_response:
        return rate_state.last_response
    
    ai_service = AIService()
    
    try:
        reply = ai_service.sync_generate_reply(user_message, history, user_id)
        # Обновляем кэш последнего ответа
        if reply and reply != AIService.FALLBACK_RESPONSE and reply != RATE_LIMIT_MESSAGE:
            rate_state.last_message = message_text
            rate_state.last_response = reply
        return reply
    except Exception as e:
        logger.error(f"Error generating AI reply for user {user_id}: {type(e).__name__}")
        return AIService.FALLBACK_RESPONSE
