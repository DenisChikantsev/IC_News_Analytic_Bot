import logging
import time
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


def run_bot_polling_old():
    """Запускает бота в режиме polling."""
    logger.info("Запуск Telegram-бота (polling)...")
    try:
        # non_stop=True говорит боту не останавливаться при ошибках
        bot.polling(non_stop=True, allowed_updates=['message', 'callback_query'], skip_pending=True)
    except Exception as e:
        logger.critical(f"Polling остановлен с критической ошибкой: {e}", exc_info=True)


def run_bot_polling():
    """Запускает бота в режиме polling с автоматическим перезапуском."""
    logger.info("Запуск Telegram-бота в режиме вечного опроса...")
    while True:
        try:
            # non_stop=False, так как мы сами управляем перезапуском
            # timeout=90 - это таймаут для получения обновлений, а не для всего соединения
            bot.polling(non_stop=False, interval=15, timeout=90,
                        allowed_updates=['message', 'callback_query'], skip_pending=True)
        except Exception as e:
            logger.error(f"Ошибка в работе бота: {e}", exc_info=True)
            logger.info("Перезапуск через 15 секунд...")
            time.sleep(15)

if __name__ == '__main__':
    logger.info("Запуск приложения...")

    # Запускаем планировщик в отдельном потоке, чтобы он не блокировал бота
    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True  # Поток завершится, когда завершится основная программа
    scheduler_thread.start()

    # Запускаем бота в основном потоке
    run_bot_polling()