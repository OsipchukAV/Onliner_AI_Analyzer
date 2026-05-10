import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class AdAIAnalyzer:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def analyze(self, raw_data):
        if "error" in raw_data: return raw_data

        # Самая стабильная и быстрая модель на данный момент
        model_name = "google/gemini-2.0-flash-001"

        prompt = f"""
        ИНСТРУКЦИЯ: Верни СТРОГО JSON. 
        Все значения в полях (summary, category, brand, model, condition) ДОЛЖНЫ БЫТЬ НА РУССКОМ ЯЗЫКЕ. 
        Даже если оригинал на английском — переведи суть на русский.

        ТОВАР ДЛЯ АНАЛИЗА:
        Заголовок: {raw_data.get('title')}
        Описание: {raw_data.get('description')}
        Цена: {raw_data.get('price')}

        ФОРМАТ JSON:
        {{
          "is_commercial": boolean (true если это компания/перекуп, false если частник),
          "category": "категория товара на русском",
          "brand": "бренд на русском или английском",
          "model": "модель",
          "condition": "состояние на русском",
          "summary": "краткое описание сути в 1 предложение на русском"
        }}
        """

        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system",
                         "content": "Ты - профессиональный аналитик объявлений. Отвечаешь только на русском языке в формате JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    timeout=20
                )
                res_content = json.loads(response.choices[0].message.content)
                return res_content[0] if isinstance(res_content, list) else res_content
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                    continue

                return {
                    "is_commercial": False,
                    "category": "Ошибка ИИ",
                    "brand": "—",
                    "model": "—",
                    "condition": "—",
                    "summary": f"Внимание: Не удалось проанализировать через API (Код {str(e)[:10]}). Данные сохранены без анализа."
                }