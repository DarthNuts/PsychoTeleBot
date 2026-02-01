"""
Скрипт для проверки подключения к OpenRouter API
"""
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_openrouter_setup():
    """Проверка настройки OpenRouter"""
    
    print("=" * 60)
    print("🔍 Проверка настройки OpenRouter")
    print("=" * 60)
    
    # Проверка API ключа
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        print(f"✅ API ключ найден: {api_key[:15]}...{api_key[-10:]}")
    else:
        print("❌ API ключ НЕ НАЙДЕН в .env файле!")
        print("   Добавьте OPENROUTER_API_KEY=ваш_ключ в .env")
        return False
    
    # Проверка модели
    model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
    print(f"✅ Модель: {model}")
    
    # Проверка наличия :free в названии
    if ":free" in model:
        print("✅ Используется БЕСПЛАТНАЯ модель")
    else:
        print("⚠️  ВНИМАНИЕ: Модель может быть платной!")
        print("   Рекомендуемые бесплатные модели:")
        print("   - google/gemini-2.0-flash-exp:free")
        print("   - qwen/qwen-2-7b-instruct:free")
        print("   - meta-llama/llama-3.2-3b-instruct:free")
    
    # Тестовый запрос к API
    print("\n" + "=" * 60)
    print("🌐 Проверка подключения к OpenRouter API...")
    print("=" * 60)
    
    try:
        from application.ai_service import AIService
        
        ai_service = AIService()
        print(f"✅ AI-сервис инициализирован")
        print(f"   Модель: {ai_service.model}")
        print(f"   Max tokens: {ai_service.max_tokens}")
        print(f"   Temperature: {ai_service.temperature}")
        
        # Попытка отправить тестовый запрос
        print("\n📤 Отправка тестового запроса...")
        print("   (это может занять несколько секунд)")
        
        response = ai_service.sync_generate_reply(
            user_message="Привет! Это тестовое сообщение.",
            history=[]
        )
        
        if "технические сложности" in response:
            print("❌ Ошибка подключения к API")
            print(f"   Ответ: {response}")
            return False
        else:
            print("✅ Успешный ответ от API!")
            print(f"\n📨 Ответ AI:")
            print(f"   {response[:200]}{'...' if len(response) > 200 else ''}")
            
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
    print("=" * 60)
    print("\n🚀 Бот готов к запуску:")
    print("   .\\run_telegram.bat")
    print("\n📚 Подробнее: см. OPENROUTER_SETUP.md")
    
    return True


if __name__ == "__main__":
    try:
        success = check_openrouter_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Проверка прервана пользователем")
        sys.exit(1)
