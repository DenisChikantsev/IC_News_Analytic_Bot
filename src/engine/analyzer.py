import logging
import sys
from datetime import datetime

from src.services.gemini_client import GeminiClient
from src.config import OUTPUT_DIR, prompt_1, NEWS_SOURCE  # Добавили импорт NEWS_SOURCE

# --- Настройка логгирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run_full_analysis():
    """
    Полный цикл: сбор новостей, подготовка дайджеста и анализ с помощью Gemini.
    Источник новостей управляется переменной NEWS_SOURCE в config.py.
    """
    try:
        # --- Этап 1: Сбор новостей в зависимости от конфига ---
        articles = []
        prepare_digest_for_ai = None

        if NEWS_SOURCE == "google":
            from src.services.news_collector_goog import gather_strategic_news, prepare_digest_for_ai
            logger.info("--- Этап 1: Сбор новостей из Google News (заголовки и описания) ---")
            articles = gather_strategic_news()
        elif NEWS_SOURCE == "newsapi":
            from src.services.news_collector import get_news_with_newsapi, prepare_digest_for_ai
            STRATEGIC_TOPICS = [
                'WORLD', 'BUSINESS', 'TECHNOLOGY', 'ECONOMY', 'FINANCE',
                'ENERGY', 'DIGITAL CURRENCIES', 'INTERNET SECURITY'
            ]
            logger.info("--- Этап 1: Сбор новостей из NewsAPI (заголовки и описания) ---")
            articles = get_news_with_newsapi(topics=STRATEGIC_TOPICS)
        else:
            raise ValueError(f"Неизвестный источник новостей в config.py: '{NEWS_SOURCE}'")

        if not articles:
            logger.warning("Не удалось собрать новости. Анализ прерван.")
            return

        logger.info(f"--- Собрано {len(articles)} уникальных статей. ---")

        # --- Этап 2: Подготовка дайджеста для AI ---
        logger.info("--- Этап 2: Подготовка дайджеста для AI ---")
        digest = prepare_digest_for_ai(articles)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        digest_path = OUTPUT_DIR / f"digest_for_gemini_{timestamp}.txt"
        # with open(digest_path, "w", encoding='utf-8') as f:
        #     f.write(digest)
        logger.info(f"Дайджест сохранен в файл '{digest_path}'")

        # --- Этап 3: Двухэтапный анализ в Gemini ---
        logger.info("--- Этап 3: Анализ в Gemini ---")
        client = GeminiClient()
        # digest="проверка работы нейросети"
        analysis_result = client.run_two_stage_analysis(digest=digest)

        logger.info("\n\n--- ГОТОВЫЙ АНАЛИЗ ОТ GEMINI ---")
        for line in analysis_result.splitlines():
            logger.info(line)

        analysis_path = OUTPUT_DIR / f"gemini_analysis_{timestamp}.txt"
        with open(analysis_path, "w", encoding='utf-8') as f:
            f.write(analysis_result)
        logger.info(f"--- Анализ сохранен в файл '{analysis_path}' ---")

    except Exception as e:
        logger.error(f"--- Произошла критическая ошибка: {e} ---", exc_info=True)


if __name__ == '__main__':
    run_full_analysis()