import telebot
from src.config import BOT_TOKEN, CHAT_ID, TOPIC_ID
from src.engine.analyzer import run_full_analysis
import logging

logger = logging.getLogger(__name__)

# Убедимся, что CHAT_ID и TOPIC_ID загружены, но не будем падать, если их нет
# Это позволит боту работать и без них (например, для получения ID)
CHAT_ID_INT = int(CHAT_ID) if CHAT_ID else None
TOPIC_ID_INT = int(TOPIC_ID) if TOPIC_ID else None

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    bot.reply_to(message, "Привет! Я бот-аналитик. Готов к работе.")


@bot.message_handler(commands=['get_chat_info'])
def get_chat_info(message):
    """Отправляет ID чата и топика. Полезно для настройки."""
    chat_id = message.chat.id
    topic_id = message.message_thread_id
    text = (
        f"ℹ️ Информация о чате:\n\n"
        f"**Chat ID:** `{chat_id}`\n"
    )
    if topic_id:
        text += f"**Topic ID:** `{topic_id}`"
    else:
        text += "Это не топик."

    text += "\n\nСкопируй эти значения в свой `.env` файл."
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=['run_analysis'])
def analysis_handler(message):
    """Запускает полный цикл анализа вручную."""
    # TODO: Добавить проверку, что команду вызывает только админ
    bot.reply_to(message, "⏳ Начинаю анализ новостей... Это может занять несколько минут.")
    logger.info("Ручной запуск анализа по команде /run_analysis")

    try:
        report = run_full_analysis()

        if CHAT_ID_INT and TOPIC_ID_INT:
            bot.reply_to(message, "✅ Анализ завершен, отправляю отчет в целевой чат.")
            # Разделяем сообщение, если оно слишком длинное для Telegram
            for part in telebot.util.smart_split(report, 4096):
                bot.send_message(
                    chat_id=CHAT_ID_INT,
                    text=part,
                    message_thread_id=TOPIC_ID_INT,
                    parse_mode="Markdown"
                )
            logger.info(f"Отчет успешно отправлен в чат {CHAT_ID_INT}, топик {TOPIC_ID_INT}")
        else:
            logger.warning("CHAT_ID или TOPIC_ID не настроены. Отправляю отчет в текущий чат.")
            for part in telebot.util.smart_split(report, 4096):
                bot.reply_to(message, part, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка при выполнении ручного анализа: {e}", exc_info=True)
        bot.reply_to(message, f"❌ Произошла ошибка во время анализа: {e}")


@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'sticker'])
def moderate_topic(message):
    """Удаляет все сообщения в защищенном топике, кроме сообщений от самого бота."""
    is_correct_chat = str(message.chat.id) == CHAT_ID
    is_correct_topic = str(message.message_thread_id) == TOPIC_ID
    is_from_bot = message.from_user.id == bot.get_me().id

    if is_correct_chat and is_correct_topic and not is_from_bot:
        try:
            bot.delete_message(message.chat.id, message.message_id)
            logger.info(f"Удалено сообщение от пользователя {message.from_user.username} в модерируемом топике.")
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение: {e}")