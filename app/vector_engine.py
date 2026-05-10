import chromadb
from sentence_transformers import SentenceTransformer
from PIL import Image
import requests
from io import BytesIO

class VectorSearchEngine:
    def __init__(self):
        # Инициализация векторной БД
        self.chroma_client = chromadb.PersistentClient(path="./db_vector")
        self.collection = self.chroma_client.get_or_create_collection(name="onliner_ads")

        # Загрузка модели CLIP
        self.model = SentenceTransformer('clip-ViT-B-32')

    def create_embedding(self, text, image_url=None):
        """Создание вектора на основе текста и изображения"""
        text_emb = self.model.encode(text)

        if image_url:
            try:
                response = requests.get(image_url, timeout=5)
                img = Image.open(BytesIO(response.content))
                img_emb = self.model.encode(img)
                # Усреднение векторов для повышения точности
                final_emb = (text_emb + img_emb) / 2
                return final_emb.tolist()
            except:
                return text_emb.tolist()

        return text_emb.tolist()

    def add_ad(self, ad_id, text, metadata, image_url=None):
        """Добавление объявления в базу"""
        vector = self.create_embedding(text, image_url)
        self.collection.add(
            ids=[str(ad_id)],
            embeddings=[vector],
            metadatas=[metadata]
        )

    def search_similar(self, query_text, n=3):
        """Поиск похожих объектов по тексту"""
        query_vector = self.model.encode(query_text).tolist()
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=n
        )
        return results

    def exists(self, ad_id):
        """Проверка существования записи по ID"""
        try:
            result = self.collection.get(ids=[str(ad_id)])
            return len(result['ids']) > 0
        except:
            return False

    def clear_all(self):
        """Полная очистка базы данных"""
        all_data = self.collection.get()
        if all_data['ids']:
            self.collection.delete(ids=all_data['ids'])

    def get_total_count(self):
        """Возвращает общее количество записей в коллекции"""
        return self.collection.count()

    def get_all_ads(self):
        """Возвращает метаданные всех записей (лимит 100 для производительности)"""
        return self.collection.get(limit=100)