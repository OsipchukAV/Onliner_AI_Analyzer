import streamlit as st
from app.online_parser import OnlinerParser
from app.ai_processor import AdAIAnalyzer
from app.vector_engine import VectorSearchEngine
from app.auto_manager import AutomationManager
from PIL import Image
import requests
from io import BytesIO
import json

st.set_page_config(page_title="Onliner AI Analyzer", layout="wide")


@st.cache_resource
def load_systems():
    p = OnlinerParser()
    ai = AdAIAnalyzer()
    v = VectorSearchEngine()
    m = AutomationManager(p, ai, v)
    return p, ai, v, m


parser, ai, vector_db, auto_manager = load_systems()

# Инициализация состояния сессии
if 'selected_ad' not in st.session_state:
    st.session_state.selected_ad = None


def display_ad_details(ad_data):
    """Отображение детальной информации в главном окне"""
    raw = ad_data['raw']
    structured = ad_data['structured']

    st.subheader(raw.get('title', 'Наименование отсутствует'))
    st.write(f"### Цена: {raw.get('price', 'Не указана')}")

    col_img, col_txt = st.columns([1, 2])
    with col_img:
        if raw.get('images'):
            try:
                response = requests.get(raw['images'][0], timeout=5)
                img = Image.open(BytesIO(response.content))
                st.image(img, use_container_width=True)
            except:
                st.error("Изображение недоступно")

    with col_txt:
        item = structured if isinstance(structured, dict) else structured[0]
        st.markdown(f"**Бренд:** {item.get('brand', '—')}")
        st.markdown(f"**Модель:** {item.get('model', '—')}")
        st.markdown(f"**Категория:** {item.get('category', '—')}")
        st.markdown(f"**Состояние:** {item.get('condition', '—')}")

        is_comm = item.get('is_commercial')
        st.markdown(f"**Тип:** {'Коммерческое' if is_comm else 'Частное'}")

        st.info(f"**Резюме:** {item.get('summary', '—')}")
        st.caption(f"[Открыть оригинал]({raw.get('source_url')})")


# --- ГЛАВНЫЙ ИНТЕРФЕЙС ---

col_main, col_registry = st.columns([0.7, 0.3])

with col_main:
    st.header("Анализ и структурирование")

    # Поле ввода ссылки
    manual_url = st.text_input("Введите ссылку для анализа:")
    if st.button("Выполнить анализ"):
        if manual_url:
            with st.spinner("Обработка..."):
                raw_data = parser.scrape_item(manual_url)
                if "error" not in raw_data:
                    structured_data = ai.analyze(raw_data)
                    st.session_state.selected_ad = {"raw": raw_data, "structured": structured_data}

                    # Сохранение в базу
                    summary = structured_data.get('summary', '') if isinstance(structured_data, dict) else \
                    structured_data[0].get('summary', '')
                    index_text = f"{raw_data['title']} {summary}"
                    vector_db.add_ad(
                        ad_id=manual_url,
                        text=index_text,
                        metadata={
                            "title": raw_data['title'],
                            "price": raw_data['price'],
                            "raw_data_json": json.dumps(raw_data),
                            "structured_json": json.dumps(structured_data)
                        },
                        image_url=raw_data['images'][0] if raw_data['images'] else None
                    )
                    st.rerun()

    # Отображение выбранного товара
    if st.session_state.selected_ad:
        st.divider()
        display_ad_details(st.session_state.selected_ad)

with col_registry:
    st.header("База данных")

    # Счётчик
    total_count = vector_db.get_total_count()
    st.metric("Всего записей", total_count)
    st.divider()

    # Список всех записей
    st.subheader("Реестр объектов")
    all_ads = vector_db.get_all_ads()

    if all_ads and all_ads['ids']:
        # Вывод списка в контейнере с прокруткой
        with st.container(height=600):
            for i in range(len(all_ads['ids'])):
                meta = all_ads['metadatas'][i]
                ad_id = all_ads['ids'][i]

                title = meta.get('title', 'Без названия')[:50]
                price = meta.get('price', '')

                if st.button(f"{title}\n{price}", key=f"reg_{ad_id}", use_container_width=True):
                    # При клике загружаем данные в сессию
                    st.session_state.selected_ad = {
                        "raw": json.loads(meta['raw_data_json']),
                        "structured": json.loads(meta['structured_json'])
                    }
                    st.rerun()
    else:
        st.write("База данных пуста")

# --- БОКОВАЯ ПАНЕЛЬ ---

st.sidebar.header("Поиск")
search_q = st.sidebar.text_input("Поиск по ключевым словам:")
if search_q:
    results = vector_db.search_similar(search_q, n=5)
    if results['ids'][0]:
        st.sidebar.write("Результаты поиска:")
        for i in range(len(results['ids'][0])):
            m = results['metadatas'][0][i]
            if st.sidebar.button(f"{m.get('title', '')[:30]}...", key=f"search_{results['ids'][0][i]}"):
                st.session_state.selected_ad = {
                    "raw": json.loads(m['raw_data_json']),
                    "structured": json.loads(m['structured_json'])
                }
                st.rerun()

st.sidebar.divider()
st.sidebar.header("Автоматизация")
c_lim = st.sidebar.slider("Категории:", 1, 10, 3)
a_lim = st.sidebar.slider("Объявления:", 5, 30, 10)

if st.sidebar.button("Запустить сбор"):
    status = st.sidebar.empty()
    with st.spinner("Сбор данных..."):
        auto_manager.run_global_sync(c_lim, a_lim, lambda m: status.text(m))
    st.rerun()

if st.sidebar.button("Очистить базу"):
    vector_db.clear_all()
    st.session_state.selected_ad = None
    st.rerun()