import logging
import sys
import threading
from src.bot.handlers import bot
from src.engine.scheduler import start_scheduler

# --- Настройка логгирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run_bot_polling():
    """Запускает бота в режиме polling."""
    logger.info("Запуск Telegram-бота (polling)...")
    try:
        # non_stop=True говорит боту не останавливаться при ошибках
        bot.polling(non_stop=True)
    except Exception as e:
        logger.critical(f"Polling остановлен с критической ошибкой: {e}", exc_info=True)


if __name__ == '__main__':
    logger.info("Запуск приложения...")

    # Запускаем планировщик в отдельном потоке, чтобы он не блокировал бота
    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True  # Поток завершится, когда завершится основная программа
    scheduler_thread.start()

    # Запускаем бота в основном потоке
    run_bot_polling()