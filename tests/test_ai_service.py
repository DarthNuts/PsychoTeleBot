"""
Тесты для AI Service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from application.ai_service import AIService, generate_ai_reply


@pytest.fixture
def ai_service():
    """Создание AI сервиса для тестов"""
    return AIService(
        api_key="test_key",
        timeout=5,
        max_history=10
    )


class TestAIService:
    """Тесты для AIService"""
    
    def test_init_with_api_key(self):
        """Позитивный: инициализация с API ключом"""
        service = AIService(api_key="test_key_123")
        assert service.api_key == "test_key_123"
        assert service.max_tokens == 500
        assert service.temperature == 0.7
    
    def test_init_from_env(self):
        """Позитивный: инициализация из переменной окружения"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'env_key_456'}):
            service = AIService()
            assert service.api_key == "env_key_456"
    
    def test_init_no_api_key(self):
        """Позитивный: инициализация без API ключа"""
        with patch.dict('os.environ', {}, clear=True):
            service = AIService()
            assert service.api_key is None
    
    def test_build_messages_empty_history(self, ai_service):
        """Позитивный: построение сообщений с пустой историей"""
        messages = ai_service._build_messages([])
        
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert "психологической помощи" in messages[0]["content"]
    
    def test_build_messages_with_history(self, ai_service):
        """Позитивный: построение сообщений с историей"""
        history = [
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Здравствуйте"}
        ]
        
        messages = ai_service._build_messages(history)
        
        assert len(messages) == 3  # system + 2 history
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
    
    def test_build_messages_limits_history(self, ai_service):
        """Позитивный: ограничение истории до max_history"""
        ai_service.max_history = 4
        
        # 6 сообщений, должно остаться 4
        history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(6)
        ]
        
        messages = ai_service._build_messages(history)
        
        # system + последние 4 из истории
        assert len(messages) == 5
        assert messages[1]["content"] == "Message 2"  # Первое из последних 4
        assert messages[-1]["content"] == "Message 5"  # Последнее
    
    @pytest.mark.asyncio
    async def test_generate_reply_no_api_key(self):
        """Негативный: генерация без API ключа"""
        service = AIService(api_key=None)
        
        reply = await service.generate_reply("Test message", [])
        
        assert "технические сложности" in reply
    
    @pytest.mark.asyncio
    async def test_generate_reply_timeout(self, ai_service):
        """Негативный: таймаут при запросе"""
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            
            reply = await ai_service.generate_reply("Test", [])
            
            assert "слишком много времени" in reply
    
    @pytest.mark.asyncio
    async def test_generate_reply_http_error_429(self, ai_service):
        """Негативный: ошибка 429 (rate limit)"""
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Too many requests"
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "429", request=Mock(), response=mock_response
                )
            )
            
            reply = await ai_service.generate_reply("Test", [])
            
            assert "лимит запросов" in reply
    
    @pytest.mark.asyncio
    async def test_generate_reply_success(self, ai_service):
        """Позитивный: успешная генерация ответа"""
        import httpx
        
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Это тестовый ответ от AI"
                    }
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            reply = await ai_service.generate_reply("Привет", [])
            
            assert reply == "Это тестовый ответ от AI"
    
    @pytest.mark.asyncio
    async def test_generate_reply_empty_response(self, ai_service):
        """Негативный: пустой ответ от API"""
        import httpx
        
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": "   "  # Пустая строка с пробелами
                    }
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            reply = await ai_service.generate_reply("Test", [])
            
            assert "технические сложности" in reply


class TestGenerateAIReply:
    """Тесты для функции generate_ai_reply"""
    
    def test_generate_ai_reply_basic(self):
        """Позитивный: базовое использование"""
        with patch('application.ai_service.AIService') as mock_service:
            mock_instance = Mock()
            mock_instance.sync_generate_reply.return_value = "AI ответ"
            mock_service.return_value = mock_instance
            
            result = generate_ai_reply(123, "Привет", [])
            
            assert result == "AI ответ"
            mock_instance.sync_generate_reply.assert_called_once_with("Привет", [])
    
    def test_generate_ai_reply_with_history(self):
        """Позитивный: с историей диалога"""
        history = [
            {"role": "user", "content": "Первое сообщение"},
            {"role": "assistant", "content": "Первый ответ"}
        ]
        
        with patch('application.ai_service.AIService') as mock_service:
            mock_instance = Mock()
            mock_instance.sync_generate_reply.return_value = "Второй ответ"
            mock_service.return_value = mock_instance
            
            result = generate_ai_reply(456, "Второе сообщение", history)
            
            assert result == "Второй ответ"
    
    def test_generate_ai_reply_error_handling(self):
        """Негативный: обработка ошибки"""
        with patch('application.ai_service.AIService') as mock_service:
            mock_instance = Mock()
            mock_instance.sync_generate_reply.side_effect = Exception("Test error")
            mock_service.return_value = mock_instance
            mock_service.FALLBACK_RESPONSE = AIService.FALLBACK_RESPONSE
            
            result = generate_ai_reply(789, "Test", [])
            
            assert "технические сложности" in result or result == AIService.FALLBACK_RESPONSE


class TestSystemPrompt:
    """Тесты для system prompt"""
    
    def test_system_prompt_content(self):
        """Позитивный: проверка содержания system prompt"""
        prompt = AIService.SYSTEM_PROMPT
        
        assert "психологической помощи" in prompt
        assert "эмпатично" in prompt
        assert "по-русски" in prompt
        assert "диагнозы" in prompt
        assert "врачом" in prompt
        assert "кризиса" in prompt
        assert "специалист" in prompt
    
    def test_fallback_response(self):
        """Позитивный: проверка fallback ответа"""
        fallback = AIService.FALLBACK_RESPONSE
        
        assert "технические сложности" in fallback
        assert len(fallback) > 20


class TestEdgeCases:
    """Граничные случаи"""
    
    def test_very_long_history(self, ai_service):
        """Граничный: очень длинная история"""
        ai_service.max_history = 5
        
        long_history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(100)
        ]
        
        messages = ai_service._build_messages(long_history)
        
        # system + max 5 from history
        assert len(messages) <= 6
    
    def test_empty_user_message(self, ai_service):
        """Граничный: пустое сообщение пользователя"""
        result = generate_ai_reply(123, "", [])
        
        # Должно вернуть что-то (не упасть)
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_malformed_api_response(self, ai_service):
        """Негативный: некорректный формат ответа API"""
        import httpx
        
        mock_response_data = {
            "invalid": "structure"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            reply = await ai_service.generate_reply("Test", [])
            
            assert "технические сложности" in reply
