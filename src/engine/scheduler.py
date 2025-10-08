from apscheduler.schedulers.blocking import BlockingScheduler
from src.bot.handlers import bot
from src.engine.analyzer import run_full_analysis
from src.config import CHAT_ID, TOPIC_CONFIGS
import telebot
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
        report = run_full_analysis(analysis_config)
        if not report or "[Ошибка" in report:
            logger.error(
                f"Анализ '{analysis_type}' завершился с ошибкой или пустым результатом. Отчет не отправлен. Результат: {report}")
            return

        chat_id_int = int(CHAT_ID)
        topic_id_int = int(topic_id)

        logger.info(f"Отправка отчета '{analysis_type}' в чат {chat_id_int}, топик {topic_id_int}")
        for part in telebot.util.smart_split(report, 4096):
            try:
                # Пытаемся отправить с Markdown
                bot.send_message(
                    chat_id=chat_id_int,
                    text=part,
                    message_thread_id=topic_id_int,
                    parse_mode="Markdown"
                )
            except telebot.apihelper.ApiTelegramException as e:
                if "can't parse entities" in e.description:
                    # Если не получилось, отправляем как обычный текст
                    logger.warning(
                        f"Ошибка парсинга Markdown в планировщике, отправляю как обычный текст. Ошибка: {e.description}")
                    bot.send_message(
                        chat_id=chat_id_int,
                        text=part,
                        message_thread_id=topic_id_int
                    )
                else:
                    # Если ошибка другая, пробрасываем ее дальше
                    raise

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
    scheduler.add_job(send_analysis_report_job, 'cron', hour=9, minute=0, args=["USA_STOCKS"])

    # Здесь можно будет легко добавить другие расписания
    # scheduler.add_job(send_analysis_report_job, 'cron', hour=10, minute=0, args=["CRYPTO"])

    logger.info("Планировщик настроен. Запуск анализа USA_STOCKS каждый день в 9:00 МСК.")

    # ИСПРАВЛЕНИЕ: Используем get_schedules() вместо get_jobs() для APScheduler v4+
    schedules = scheduler.get_schedules()
    if schedules:
        logger.info(f"Следующий запуск: {schedules[0].next_run_time}")

    scheduler.start()