import requests
from bs4 import BeautifulSoup


class OnlinerParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def scrape_item(self, url: str):
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            # Заголовок
            title_tag = soup.select_one(".m-title-i.title") or soup.select_one("h1.title")
            title_text = title_tag.get_text(strip=True) if title_tag else "Заголовок не найден"

            # Цена
            price_tag = soup.select_one(".price-primary")
            torg_tag = soup.select_one(".torg")
            price_text = price_tag.get_text(strip=True) if price_tag else "Цена не указана"
            if torg_tag: price_text += " (Торг)"

            # Описание
            content_div = soup.find("div", class_="content")
            description_text = content_div.get_text(separator=" ", strip=True) if content_div else ""

            # КАРТИНКИ: Агрессивный сбор
            images = []
            # Ищем все возможные теги картинок в теле поста
            img_tags = soup.select("img.msgpost-img, img.fast-img, .content img, .img-va img")

            for img in img_tags:

                src = img.get("src") or img.get("data-src") or img.get("data-original")

                if src:
                    # Чистим ссылку
                    if src.startswith("//"): src = "https:" + src
                    if src.startswith("/"): src = "https://baraholka.onliner.by" + src

                    # Исключаем мелкие иконки и смайлики
                    if "icon" not in src and "static" not in src and src not in images:
                        images.append(src)

            return {
                "title": title_text, "price": price_text,
                "description": description_text, "images": images, "source_url": url
            }
        except Exception as e:
            return {"error": str(e)}

    def get_all_categories(self):
        base_url = "https://baraholka.onliner.by/"
        try:
            response = requests.get(base_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, "lxml")
            categories = []
            category_lists = soup.find_all("ul", class_="b-cm-list")
            for ul in category_lists:
                links = ul.find_all("a", href=True)
                for link in links:
                    href = link['href']
                    if "viewforum.php?f=" in href:
                        clean_href = href.lstrip('./')
                        full_url = "https://baraholka.onliner.by/" + clean_href
                        categories.append({"name": link.get_text(strip=True), "url": full_url})
            return categories
        except:
            return []

    def get_category_links(self, category_url: str, limit: int = 20):
        try:
            response = requests.get(category_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, "lxml")
            links = []
            items = soup.find_all("h2", class_="wraptxt")
            for h2 in items:
                a_tag = h2.find("a", href=True)
                if a_tag:
                    href = a_tag['href'].lstrip('./').split('&')[0]
                    full_url = "https://baraholka.onliner.by/" + href
                    if full_url not in links: links.append(full_url)
                if len(links) >= limit: break
            return links
        except:
            return []