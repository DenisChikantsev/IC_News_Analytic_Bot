import logging
import sys
from datetime import datetime
from src.services.gemini_client import GeminiClient
from src.config import OUTPUT_DIR, TOPIC_CONFIGS # Убедимся, что импортируем TOPIC_CONFIGS
from src.services.news_collector_goog import gather_strategic_news, prepare_digest_for_ai

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run_full_analysis(analysis_config: dict) -> str:
    """
    Полный цикл: сбор новостей, анализ и возврат ТОЛЬКО второй (технической) части.
    При этом полный отчет сохраняется в файл.
    """
    try:
        news_source = analysis_config['news_source']
        news_topics = analysis_config['news_topics']
        prompt_template = analysis_config['prompt']

        # --- Этап 1: Сбор новостей ---
        logger.info(f"--- Этап 1: Сбор новостей из {news_source} по темам: {news_topics} ---")
        articles = gather_strategic_news(topics=news_topics)

        if not articles:
            warning_msg = "Не удалось собрать новости. Анализ прерван."
            logger.warning(warning_msg)
            return warning_msg

        logger.info(f"--- Собрано {len(articles)} уникальных статей. ---")

        # --- Этап 2: Подготовка дайджеста для AI ---
        logger.info("--- Этап 2: Подготовка дайджеста для AI ---")
        digest = prepare_digest_for_ai(articles)

        # --- Этап 3: Двухэтапный анализ в Gemini ---
        logger.info("--- Этап 3: Анализ в Gemini ---")
        client = GeminiClient()
        # ИЗМЕНЕНИЕ: Получаем словарь с частями анализа
        analysis_parts = client.run_two_stage_analysis(digest=digest, prompt_template=prompt_template)

        stage1_report = analysis_parts.get("stage1", "[ОШИБКА: Первая часть анализа отсутствует]")
        stage2_report = analysis_parts.get("stage2", "") # По умолчанию пустая строка

        # ИЗМЕНЕНИЕ: Собираем полный отчет для сохранения в файл
        full_report = (
            f"{stage1_report}\n\n"
            "========================================\n"
            f"{stage2_report}" if stage2_report else stage1_report
        )

        logger.info("\n\n--- ГОТОВЫЙ АНАЛИЗ ОТ GEMINI (ПОЛНЫЙ) ---")
        for line in full_report.splitlines():
            logger.info(line)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_path = OUTPUT_DIR / f"gemini_analysis_{timestamp}.txt"
        with open(analysis_path, "w", encoding='utf-8') as f:
            f.write(full_report)
        logger.info(f"--- Полный анализ сохранен в файл '{analysis_path}' ---")

        # ИЗМЕНЕНИЕ: Возвращаем только вторую часть для отправки в Telegram
        if not stage2_report or "[Ошибка" in stage2_report:
             # Если второй этап не удался, отправим информативное сообщение об этом
             return f"Технический анализ не удался. \n\nДетали: {stage2_report}"

        return stage2_report

    except Exception as e:
        error_msg = f"--- Произошла критическая ошибка в 'run_full_analysis': {e} ---"
        logger.error(error_msg, exc_info=True)
        return error_msg


# Этот блок теперь не нужен для основного запуска, но может быть полезен для тестов
if __name__ == '__main__':
    logger.info("Запуск тестового анализа для USA_STOCKS...")
    # run_full_analysis теперь возвращает строку (вторую часть), просто выведем ее
    result_for_bot = run_full_analysis(TOPIC_CONFIGS["USA_STOCKS"])
    logger.info("\n--- РЕЗУЛЬТАТ ДЛЯ ОТПРАВКИ В БОТА ---")
    logger.info(result_for_bot)