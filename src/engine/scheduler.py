from apscheduler.schedulers.blocking import BlockingScheduler
from src.bot.handlers import send_report
from src.engine.analyzer import run_full_analysis
from src.config import CHAT_ID, TOPIC_CONFIGS
from datetime import datetime
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
        logger.error(
            f"CHAT_ID или ID топика для '{analysis_type}' не настроены в .env. Отчет по расписанию не может быть отправлен.")
        return

    try:
        # 1. Получаем URL статьи от анализатора
        telegraph_url = run_full_analysis(analysis_config, analysis_type)

        # 2. Проверяем результат и формируем сообщение
        if not telegraph_url or not telegraph_url.startswith("http"):
            logger.error(f"Анализ '{analysis_type}' завершился с ошибкой или пустым результатом. Отчет не отправлен. "
                         f"Результат: {telegraph_url}")
            return

        # 3. Формируем красивое сообщение, как в ручном режиме
        current_time = datetime.now().strftime('%d.%m.%Y %H:%M')
        disclaimer = (
            f"\n\n—\n"
            f"<i><b>⚠️ Дисклеймер:</b> Данный анализ сгенерирован автоматически и не является "
            f"инвестиционной рекомендацией. Инвестиции сопряжены с риском. "
            f"Принимайте решения обдуманно.</i>\n\n"
            f"<code>Отчет сформирован: {current_time}</code>"
        )
        report_message = (
            f"<b>Анализ по теме: {analysis_type}</b>\n\n"
            f"<a href='{telegraph_url}'><b>➡️ Читать полный анализ</b></a>"
            f"{disclaimer}"
        )

        send_report([report_message], CHAT_ID, topic_id)

        logger.info(f"✅ Отчет '{analysis_type}' по расписанию успешно отправлен.")

    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при выполнении анализа '{analysis_type}' по расписанию: {e}",
                        exc_info=True)


def start_scheduler():
    """
    Настраивает и запускает планировщик.
    """
    scheduler = BlockingScheduler(timezone="Europe/Moscow")

    # Запускаем анализ для акций США каждый день в 9:00 по московскому времени
    # Здесь можно будет легко добавить другие расписания
    # scheduler.add_job(send_analysis_report_job, 'cron', hour=9, minute=0, args=["CRYPTO"])

    scheduler.add_job(send_analysis_report_job, 'cron', hour=9, minute=0, args=["USA_STOCKS"])
    scheduler.add_job(send_analysis_report_job, 'cron', hour=18, minute=0, args=["USA_STOCKS"])

    scheduler.add_job(send_analysis_report_job, 'cron', hour=9, minute=15, args=["CRYPTO"])
    scheduler.add_job(send_analysis_report_job, 'cron', hour=18, minute=15, args=["CRYPTO"])

    scheduler.add_job(send_analysis_report_job, 'cron', hour=9, minute=30, args=["CURRENCY"])
    scheduler.add_job(send_analysis_report_job, 'cron', hour=18, minute=30, args=["CURRENCY"])

    logger.info("Планировщик настроен. Запуск анализа USA_STOCKS каждый день в 9:00 и 18.00 МСК.")
    logger.info("Планировщик настроен. Запуск анализа CRYPTO каждый день в 9:15 и 18.15 МСК.")
    logger.info("Планировщик настроен. Запуск анализа CURRENCY каждый день в 9:30 и 18.30 МСК.")
    scheduler.start()
