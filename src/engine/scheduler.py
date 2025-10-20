from apscheduler.schedulers.blocking import BlockingScheduler
from src.bot.handlers import _send_report  # <<< ИЗМЕНЕНИЕ: Импортируем новую функцию
from src.engine.analyzer import run_full_analysis
from src.config import CHAT_ID, TOPIC_CONFIGS
import logging

logger = logging.getLogger(__name__)

def send_analysis_report_job(analysis_type: str):
    """
    Функция, которая запускает анализ и отправляет отчет в Telegram.
    """
    logger.info(f"🚀 Запуск анализа по расписанию для '{analysis_type}'...")

    analysis_config = TOPIC_CONFIGS.get(analysis_type)
    if not analysis_config:
        logger.error(f"Конфигурация для анализа '{analysis_type}' не найдена.")
        return

    topic_id = analysis_config.get("id")
    if not CHAT_ID or not topic_id:
        logger.error(f"CHAT_ID или ID топика для '{analysis_type}' не настроены в .env. Отчет по расписанию не может быть отправлен.")
        return

    try:
        report = run_full_analysis(analysis_config)
        if not report or "[Ошибка" in report:
            logger.error(f"Анализ '{analysis_type}' завершился с ошибкой или пустым результатом. Отчет не отправлен. Результат: {report}")
            return

        # --- ИЗМЕНЕНИЕ ---
        # Используем новую функцию для отправки отчета
        _send_report(report, CHAT_ID, topic_id)
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---

        logger.info(f"✅ Отчет '{analysis_type}' по расписанию успешно отправлен.")

    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при выполнении анализа '{analysis_type}' по расписанию: {e}", exc_info=True)


def start_scheduler():
    """
    Настраивает и запускает планировщик.
    """
    scheduler = BlockingScheduler(timezone="Europe/Moscow")

    # Запускаем анализ для акций США каждый день в 9:00 по московскому времени
    # Здесь можно будет легко добавить другие расписания
    # scheduler.add_job(send_analysis_report_job, 'cron', hour=10, minute=0, args=["CRYPTO"])

    scheduler.add_job(send_analysis_report_job, 'cron', hour=9, minute=0, args=["USA_STOCKS"])
    scheduler.add_job(send_analysis_report_job, 'cron', hour=18, minute=0, args=["USA_STOCKS"])
    scheduler.add_job(send_analysis_report_job, 'cron', hour=9, minute=10, args=["CRYPTO"])
    scheduler.add_job(send_analysis_report_job, 'cron', hour=18, minute=10, args=["CRYPTO"])

    # scheduler.add_job(send_analysis_report_job, 'cron', hour=9, minute=0, args=["USA_STOCKS"])
    # scheduler.add_job(send_analysis_report_job, 'cron', hour=18, minute=0, args=["USA_STOCKS"])


    logger.info("Планировщик настроен. Запуск анализа USA_STOCKS каждый день в 9:00 МСК.")
    logger.info("Планировщик настроен. Запуск анализа CRYPTO каждый день в 9:10 МСК.")
    scheduler.start()