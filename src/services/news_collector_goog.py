import logging
from gnews import GNews

# Отключаем лишние логи от gnews, чтобы не мешали
logging.getLogger('gnews').setLevel(logging.WARNING)

# Создаем логгер для этого модуля
logger = logging.getLogger(__name__)


def gather_strategic_news() -> list[dict]:
    """
    Собирает новости по списку стратегически важных тем, используя только заголовки и описания из GNews.
    """
    logger.info("Инициализация GNews...")
    gnews_instance = GNews(language='en', country='US', period='24h')

    STRATEGIC_TOPICS = [
        'WORLD', 'BUSINESS', 'TECHNOLOGY', 'ECONOMY', 'FINANCE',
        'ENERGY', 'DIGITAL CURRENCIES', 'INTERNET SECURITY'
    ]

    all_articles = []
    seen_urls = set()

    logger.info(f"Начинаю сбор новостей по {len(STRATEGIC_TOPICS)} темам (только заголовки и описания)...")

    for topic in STRATEGIC_TOPICS:
        logger.info(f"  -> Запрашиваю тему: {topic}")
        news_by_topic = gnews_instance.get_news_by_topic(topic)

        if not news_by_topic:
            logger.info(f"     (не найдено новостей по теме {topic})")
            continue

        added_count = 0
        for article_summary in news_by_topic:
            url = article_summary['url']
            # Проверяем на дубликаты и на наличие описания
            if url not in seen_urls and article_summary.get('description'):
                logger.info(f"      -> Добавляю: {article_summary['title']}")

                # ИСПОЛЬЗУЕМ ДАННЫЕ НАПРЯМУЮ, БЕЗ ПАРСИНГА
                all_articles.append({
                    'title': article_summary['title'],
                    'text': article_summary['description'],  # Используем краткое описание
                    'url': url,
                    'publisher': article_summary['publisher']['title']
                })
                seen_urls.add(url)
                added_count += 1

        if added_count > 0:
            logger.info(f"     + Добавлено {added_count} уникальных статей.")

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
        # digest_parts.append(f"URL: {article['url']}\n")
        # Указываем, что это краткое описание
        digest_parts.append("ТЕКСТ (краткое описание):\n")
        digest_parts.append(article['text'])

    return "".join(digest_parts)


if __name__ == "__main__":
    # Этот блок для автономного тестирования файла
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    collected_articles = gather_strategic_news()
    final_digest = prepare_digest_for_ai(collected_articles)

    logger.info(f"\n--- Итог: {len(collected_articles)} статей готовы для анализа ИИ ---")
    if collected_articles:
        logger.info("\n--- Готовый дайджест для отправки в AI-модель (начало) ---")
        logger.info(final_digest[:2000] + "\n...")
        with open("digest_gnews_only.txt", "w", encoding='utf-8') as f:
            f.write(final_digest)
        logger.info("\nПолный дайджест сохранен в файл 'digest_gnews_only.txt'")