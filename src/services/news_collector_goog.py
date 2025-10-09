import logging
from gnews import GNews

logging.getLogger('gnews').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ИЗМЕНЕНИЕ: Функция теперь принимает список тем для поиска
def gather_strategic_news(topics: list[str]) -> list[dict]:
    """
    Собирает новости по списку тем, используя только заголовки и описания из GNews.
    """
    logger.info("Инициализация GNews...")
    gnews_instance = GNews(language='en', country='US', period='12h')

    all_articles = []
    seen_urls = set()

    logger.info(f"Начинаю сбор новостей по {len(topics)} темам (только заголовки и описания)...")

    for topic in topics:
        logger.info(f"  -> Запрашиваю тему: {topic}")
        try:
            news_by_topic = gnews_instance.get_news_by_topic(topic)
            if not news_by_topic:
                logger.info(f"     (не найдено новостей по теме {topic})")
                continue

            added_count = 0
            for article_summary in news_by_topic:
                url = article_summary['url']
                if url not in seen_urls and article_summary.get('description'):
                    all_articles.append({
                        'title': article_summary['title'],
                        'text': article_summary['description'],
                        'url': url,
                        'publisher': article_summary['publisher']['title']
                    })
                    seen_urls.add(url)
                    added_count += 1
            if added_count > 0:
                logger.info(f"     + Добавлено {added_count} уникальных статей.")
        except Exception as e:
            logger.error(f"Ошибка при сборе новостей по теме '{topic}': {e}")

    logger.info(f"Сбор завершен. Всего собрано {len(all_articles)} уникальных новостей.")
    return all_articles

def prepare_digest_for_ai(articles: list) -> str:
    """
    Формирует из списка статей единый текстовый дайджест для отправки в AI.
    """
    if not articles:
        return "Нет новостей для анализа."

    digest_parts = ["Вот дайджест свежих новостей для анализа:\n"]
    for i, article in enumerate(articles):
        digest_parts.append(f"\n--- Статья #{i + 1} ---\n")
        digest_parts.append(f"Источник: {article['publisher']}\n")
        digest_parts.append(f"Заголовок: {article['title']}\n")
        digest_parts.append("Краткий текст:\n")
        digest_parts.append(article['text'])

    return "".join(digest_parts)