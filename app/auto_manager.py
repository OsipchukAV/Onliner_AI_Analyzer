import time
import json


class AutomationManager:
    def __init__(self, parser, ai, vector_db):
        self.parser = parser
        self.ai = ai
        self.vector_db = vector_db

    def run_global_sync(self, category_limit=5, ads_per_category=10, progress_callback=None):
        if progress_callback: progress_callback("Поиск активных категорий...")
        categories = self.parser.get_all_categories()
        categories = categories[:category_limit]

        total_added = 0

        for cat_idx, cat in enumerate(categories):
            if progress_callback:
                progress_callback(f"Категория {cat_idx + 1}/{len(categories)}: {cat['name']}")

            links = self.parser.get_category_links(cat['url'], limit=ads_per_category)

            for link in links:
                # Проверка на дубликат
                if self.vector_db.exists(link):
                    continue

                try:
                    # 1. ПАРСИНГ
                    raw_data = self.parser.scrape_item(link)

                    # Если ошибка в парсере, создаем заглушку, чтобы ИИ мог ее описать
                    if "error" in raw_data:
                        raw_data = {
                            "title": f"Ошибка доступа: {link}",
                            "price": "—",
                            "description": f"Парсер не смог получить данные: {raw_data['error']}",
                            "images": [],
                            "source_url": link
                        }

                    # 2. АНАЛИЗ
                    structured_data = self.ai.analyze(raw_data)

                    # 3. ФОРМИРОВАНИЕ ИНДЕКСА
                    summary = structured_data.get('summary', 'Нет описания')
                    # Если ИИ вернул ошибку, summary будет содержать текст ошибки
                    index_text = f"Товар: {raw_data['title']}. Суть: {summary}"

                    # 4. СОХРАНЕНИЕ
                    self.vector_db.add_ad(
                        ad_id=link,
                        text=index_text,
                        metadata={
                            "title": raw_data['title'],
                            "price": raw_data['price'],
                            "raw_data_json": json.dumps(raw_data),
                            "structured_json": json.dumps(structured_data)
                        },
                        image_url=raw_data['images'][0] if raw_data['images'] else None
                    )
                    total_added += 1
                    time.sleep(1)

                except Exception as e:
                    print(f"Критический сбой ссылки {link}: {e}")
                    self.vector_db.add_ad(
                        ad_id=link,
                        text=f"Критическая ошибка {link}",
                        metadata={
                            "title": "Критический сбой",
                            "price": "—",
                            "raw_data_json": json.dumps({"title": "Ошибка", "source_url": link, "images": []}),
                            "structured_json": json.dumps({"category": "Сбой", "summary": str(e)})
                        }
                    )
                    continue

        return total_added