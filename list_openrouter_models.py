"""
Скрипт для получения списка актуальных бесплатных моделей OpenRouter
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def get_available_models():
    """Получить список доступных моделей с OpenRouter"""
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ API ключ не найден!")
        return
    
    print("=" * 70)
    print("📋 Получение списка доступных моделей OpenRouter...")
    print("=" * 70)
    
    try:
        response = httpx.get(
            "https://openrouter.ai/api/v1/models",
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            
            # Фильтруем бесплатные или очень дешевые модели
            free_models = []
            cheap_models = []
            
            for model in models:
                model_id = model.get("id", "")
                pricing = model.get("pricing", {})
                prompt_price = float(pricing.get("prompt", "1"))
                completion_price = float(pricing.get("completion", "1"))
                
                # Бесплатные модели
                if ":free" in model_id or (prompt_price == 0 and completion_price == 0):
                    free_models.append({
                        "id": model_id,
                        "name": model.get("name", ""),
                        "context": model.get("context_length", 0)
                    })
                # Очень дешевые модели (< $0.0001 за 1K токенов)
                elif prompt_price < 0.0001 and completion_price < 0.0001:
                    cheap_models.append({
                        "id": model_id,
                        "name": model.get("name", ""),
                        "prompt": prompt_price,
                        "completion": completion_price,
                        "context": model.get("context_length", 0)
                    })
            
            print(f"\n🆓 БЕСПЛАТНЫЕ МОДЕЛИ (найдено: {len(free_models)}):")
            print("=" * 70)
            if free_models:
                for i, model in enumerate(free_models[:10], 1):  # Показываем топ-10
                    print(f"{i}. {model['id']}")
                    print(f"   Имя: {model['name']}")
                    print(f"   Контекст: {model['context']:,} токенов")
                    print()
            else:
                print("❌ Бесплатные модели не найдены")
            
            print(f"\n💰 ОЧЕНЬ ДЕШЕВЫЕ МОДЕЛИ (найдено: {len(cheap_models)}):")
            print("=" * 70)
            if cheap_models:
                # Сортируем по цене
                cheap_models.sort(key=lambda x: x['prompt'] + x['completion'])
                
                for i, model in enumerate(cheap_models[:10], 1):  # Показываем топ-10
                    total_cost = (model['prompt'] + model['completion']) / 2
                    print(f"{i}. {model['id']}")
                    print(f"   Имя: {model['name']}")
                    print(f"   Цена: ~${total_cost:.6f} за 1K токенов")
                    print(f"   Контекст: {model['context']:,} токенов")
                    print()
            else:
                print("❌ Дешевые модели не найдены")
            
            print("=" * 70)
            print("💡 РЕКОМЕНДАЦИИ:")
            print("=" * 70)
            
            if free_models:
                print(f"✅ Выберите модель из бесплатных и добавьте в .env:")
                print(f"   OPENROUTER_MODEL={free_models[0]['id']}")
            elif cheap_models:
                print(f"✅ Бесплатных нет, но есть очень дешевые модели:")
                print(f"   OPENROUTER_MODEL={cheap_models[0]['id']}")
                total_cost = (cheap_models[0]['prompt'] + cheap_models[0]['completion']) / 2
                print(f"   Стоимость: ~${total_cost:.6f} за 1K токенов")
                print(f"\n💳 Пополните баланс на https://openrouter.ai/credits")
                print(f"   Достаточно $1-5 для тестирования")
            else:
                print("❌ Не найдено подходящих моделей")
                print("   Посетите https://openrouter.ai/models для актуального списка")
            
            print("\n🔗 Полный список моделей: https://openrouter.ai/models")
            print("💳 Проверить баланс: https://openrouter.ai/credits")
            
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Ошибка при получении списка: {e}")


if __name__ == "__main__":
    get_available_models()
