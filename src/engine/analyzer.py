import logging
import sys
from datetime import datetime
from src.services.gemini_client import GeminiClient
from src.config import OUTPUT_DIR, TOPIC_CONFIGS
from src.services.news_collector_goog import gather_strategic_news, prepare_digest_for_ai

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

def run_full_analysis(analysis_config: dict) -> str:
    """
    Выполняет полный цикл анализа: сбор новостей, двухэтапный анализ Gemini
    и сохранение результата.
    """
    try:
        news_topics = analysis_config.get("news_topics", [])
        prompt_template = analysis_config.get("prompt")

        if not prompt_template:
            raise ValueError("Шаблон промпта не найден в конфигурации.")

        logger.info(f"Сбор новостей по темам: {news_topics}")
        news = gather_strategic_news(topics=news_topics)
        digest = prepare_digest_for_ai(news)

        client = GeminiClient()

        # --- ИЗМЕНЕНИЕ: Передаем `parsing_keys` в метод анализа ---
        analysis_parts = client.run_two_stage_analysis(
            digest=digest,
            prompt_template=prompt_template,
            parsing_keys=analysis_config.get("parsing_keys", {})
        )

        # Собираем полный отчет для сохранения в файл
        full_report_text = analysis_parts.get("stage1", "")
        if analysis_parts.get("stage2"):
            full_report_text += "\n\n" + analysis_parts.get("stage2")

        # Сохранение полного отчета в файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"gemini_analysis_{timestamp}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_report_text)
        logger.info(f"--- Полный анализ сохранен в файл '{output_file}' ---")

        # --- УЛУЧШЕНИЕ: Более информативный ответ при ошибке ---
        if not analysis_parts.get("stage2"):
            error_msg = "Технический анализ не удался. Не удалось извлечь данные для 2-го этапа из ответа ИИ."
            logger.error(error_msg)
            # Возвращаем первую часть отчета для отладки
            stage1_preview = (analysis_parts.get("stage1") or "")
            return f"{error_msg}\n\n<b>Детали (ответ 1-го этапа):</b>\n<pre>{stage1_preview}</pre>"

        # Возвращаем только вторую, техническую часть для отправки в Telegram
        return analysis_parts.get("stage2")

    except Exception as e:
        logger.critical(f"--- Произошла критическая ошибка в 'run_full_analysis': {e} ---", exc_info=True)
        return f"--- Произошла критическая ошибка в 'run_full_analysis': {e} ---"

# Этот блок теперь не нужен для основного запуска, но может быть полезен для тестов
if __name__ == '__main__':
    logger.info("Запуск тестового анализа для USA_STOCKS...")
    # run_full_analysis теперь возвращает строку (вторую часть), просто выведем ее
    result_for_bot = run_full_analysis(TOPIC_CONFIGS["USA_STOCKS"])
    logger.info("\n--- РЕЗУЛЬТАТ ДЛЯ ОТПРАВКИ В БОТА ---")
    logger.info(result_for_bot)
