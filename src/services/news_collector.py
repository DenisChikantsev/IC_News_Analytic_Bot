import os
import logging
from newsapi import NewsApiClient
from dotenv import load_dotenv

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Загружаем переменные окружения (включая ключ API)
load_dotenv()

def get_news_with_newsapi(topics: list[str], language: str = 'en') -> list[dict]:
    """
    Собирает новости с помощью NewsAPI. Просто, легко и без Selenium.
    """
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        logging.error("Ключ NEWSAPI_KEY не найден в .env файле! Получите его на newsapi.org.")
        return []

    logging.info("Инициализация клиента NewsAPI...")
    newsapi = NewsApiClient(api_key=api_key)

    all_articles = []
    seen_urls = set()

    logging.info(f"Сбор новостей по темам: {', '.join(topics)}")

    # NewsAPI предпочитает один запрос с несколькими ключевыми словами
    query = " OR ".join(topics)

    try:
        # Выполняем главный запрос
        top_headlines = newsapi.get_top_headlines(
            q=query,
            language=language,
            page_size=40  # Запросим побольше, чтобы было из чего выбрать
        )

        articles_from_api = top_headlines.get('articles', [])
        logging.info(f"Получено {len(articles_from_api)} статей от NewsAPI.")

        for article in articles_from_api:
            # Проверяем на дубликаты и на наличие контента
            if article['url'] not in seen_urls and article.get('content'):
                all_articles.append({
                    'title': article['title'],
                    # NewsAPI часто возвращает часть статьи в поле 'content'
                    'text': article['content'],
                    'url': article['url'],
                    'publisher': article['source']['name']
                })
                seen_urls.add(article['url'])

    except Exception as e:
        logging.error(f"Произошла ошибка при запросе к NewsAPI: {e}")
        logging.error("Возможные причины: неверный API ключ, превышение лимитов бесплатного тарифа.")

    logging.info(f"Сбор завершен. Собрано {len(all_articles)} статей с контентом.")
    return all_articles


def prepare_digest_for_ai(articles: list) -> str:
    """
    Формирует дайджест для AI. Код остается таким же, но данные теперь другие.
    """
    if not articles:
        return "Нет новостей для анализа."

    digest_parts = ["Вот дайджест свежих новостей для анализа:\n"]
    for i, article in enumerate(articles):
        digest_parts.append(f"\n--- Статья #{i + 1} ---\n")
        digest_parts.append(f"Источник: {article['publisher']}\n")
        digest_parts.append(f"Заголовок: {article['title']}\n")
        digest_parts.append(f"URL: {article['url']}\n")
        # Теперь здесь будет не полный текст, а выдержка от NewsAPI
        digest_parts.append("ТЕКСТ (выдержка):\n")
        digest_parts.append(article['text'])

    return "".join(digest_parts)


if __name__ == "__main__":
    # Темы можно взять из твоего файла gnews.notes
    STRATEGIC_TOPICS = [
        'WORLD', 'BUSINESS', 'TECHNOLOGY', 'ECONOMY',
        'FINANCE', 'ENERGY', 'DIGITAL CURRENCIES'
    ]

    # 1. Запускаем наш новый, легкий сборщик
    collected_articles = get_news_with_newsapi(topics=STRATEGIC_TOPICS)

    # 2. Готовим дайджест
    final_digest = prepare_digest_for_ai(collected_articles)

    # 3. Выводим результат
    logging.info(f"\n--- Итог: {len(collected_articles)} статей готовы для анализа ИИ ---")
    if collected_articles:
        print("\n--- Готовый дайджест для отправки в AI-модель (начало) ---")
        print(final_digest[:2000] + "\n...")