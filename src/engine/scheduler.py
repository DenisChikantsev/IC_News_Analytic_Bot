from apscheduler.schedulers.blocking import BlockingScheduler
from src.bot.handlers import bot
from src.engine.analyzer import run_full_analysis
from src.config import USA_STOCKS_ID, CHAT_ID
import telebot
import logging

logger = logging.getLogger(__name__)


def send_analysis_report_job():
    """
    Функция, которая запускает анализ и отправляет отчет в Telegram.
    """
    logger.info("🚀 Запуск анализа по расписанию...")
    try:
        report = run_full_analysis()
        if not report or "[Ошибка" in report:
            logger.error(f"Анализ завершился с ошибкой или пустым результатом. Отчет не отправлен. Результат: {report}")
            return

        chat_id_int = int(CHAT_ID) if CHAT_ID else None
        topic_id_int = int(USA_STOCKS_ID) if USA_STOCKS_ID else None

        if chat_id_int and topic_id_int:
            logger.info(f"Отправка отчета в чат {chat_id_int}, топик {topic_id_int}")
            for part in telebot.util.smart_split(report, 4096):
                bot.send_message(
                    chat_id=chat_id_int,
                    text=part,
                    message_thread_id=topic_id_int,
                    parse_mode="Markdown"
                )
            logger.info("✅ Отчет по расписанию успешно отправлен.")
        else:
            logger.error("CHAT_ID или TOPIC_ID не настроены в .env. Отчет по расписанию не может быть отправлен.")

    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при выполнении анализа по расписанию: {e}", exc_info=True)


def start_scheduler():
    """
    Настраивает и запускает планировщик.
    """
    # Используем 'Europe/Moscow' как пример. Можешь поменять на свой часовой пояс.
    scheduler = BlockingScheduler(timezone="Europe/Moscow")

    # Запускать каждый день в 9:00 по московскому времени
    scheduler.add_job(send_analysis_report_job, 'cron', hour=9, minute=0)

    logger.info("Планировщик настроен. Запуск каждый день в 9:00 МСК.")
    logger.info(f"Следующий запуск: {scheduler.get_jobs()[0].next_run_time}")

    scheduler.start()