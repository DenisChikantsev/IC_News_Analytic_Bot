import telebot
from telebot.apihelper import ApiTelegramException
from src.config import BOT_TOKEN, CHAT_ID, TOPIC_CONFIGS
from src.engine.analyzer import run_full_analysis
import logging

logger = logging.getLogger(__name__)

# Получаем список всех ID топиков, которые нужно модерировать
MODERATED_TOPIC_IDS = [
    config['id'] for config in TOPIC_CONFIGS.values() if config.get('id')
]

bot = telebot.TeleBot(BOT_TOKEN)


def _send_report(reports: list[str], chat_id: str, topic_id: str):
    """
    Отправляет серию отчетов в указанный чат и топик.
    Каждый элемент списка reports отправляется как отдельное сообщение.
    """
    try:
        cid = int(chat_id)
        tid = int(topic_id)

        if not reports:
            logger.warning(f"Попытка отправить пустой список отчетов в чат {cid}, топик {tid}.")
            return
        for report_text in reports:
            # Разбиваем каждое сообщение на части, если оно слишком длинное
            for part in telebot.util.smart_split(report_text, 4096):
                try:
                    # Сначала пытаемся отправить с форматированием HTML
                    bot.send_message(
                        chat_id=cid,
                        text=part,
                        message_thread_id=tid,
                        parse_mode="HTML"
                    )
                except ApiTelegramException as e:
                    if "can't parse entities" in e.description:
                        logger.warning(f"Ошибка парсинга HTML, отправляю как обычный текст. Ошибка: {e.description}")
                        bot.send_message(
                            chat_id=cid,
                            text=part,
                            message_thread_id=tid
                        )
                    else:
                        # Перебрасываем другие исключения API
                        raise
        logger.info(f"Серия отчетов ({len(reports)} шт.) успешно отправлена в чат {cid}, топик {tid}")

    except Exception as e:
        logger.error(f"Не удалось отправить отчет в чат {chat_id}, топик {topic_id}: {e}", exc_info=True)
        # bot.send_message(chat_id, "Не удалось отправить отчет.")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    bot.reply_to(message, "Привет! Я бот-аналитик. Готов к работе.")


# @bot.message_handler(commands=['get_chat_info'])
# def get_chat_info(message):
#     """Отправляет ID чата и топика. Полезно для настройки."""
#     chat_id = message.chat.id
#     topic_id = message.message_thread_id
#     text = (
#         f"ℹ️ Информация о чате:\n\n"
#         f"**ID Группы (SUPERGROUP_ID):** `{chat_id}`\n"
#     )
#     if topic_id:
#         text += f"**ID Топика (e.g., USA_STOCKS_ID):** `{topic_id}`"
#     else:
#         text += "Это не топик."
#
#     text += "\n\nСкопируй эти значения в свой `.env` файл."
#     bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=['run_analysis'])
def analysis_handler(message):
    """Запускает полный цикл анализа вручную для указанного типа."""
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "Пожалуйста, укажите тип анализа.\n"
                              f"Доступные типы: {', '.join(TOPIC_CONFIGS.keys())}\n"
                              "Пример: /run_analysis USA_STOCKS")
        return

    analysis_type = args[1].upper()
    if analysis_type not in TOPIC_CONFIGS:
        bot.reply_to(message, f"Неизвестный тип анализа: '{analysis_type}'.\n"
                              f"Доступные типы: {', '.join(TOPIC_CONFIGS.keys())}")
        return

    analysis_config = TOPIC_CONFIGS[analysis_type]
    topic_id = analysis_config.get("id")

    if not CHAT_ID or not topic_id:
        bot.reply_to(message, "Ошибка: SUPERGROUP_ID или ID топика не настроены в .env файле.")
        return

    bot.reply_to(message, f"⏳ Начинаю анализ '{analysis_type}'... Это может занять несколько минут.")
    logger.info(f"Ручной запуск анализа '{analysis_type}' по команде /run_analysis")

    try:
        reports = run_full_analysis(analysis_config)
        bot.reply_to(message, f"✅ Анализ '{analysis_type}' завершен, отправляю отчет в целевой топик.")

        _send_report(reports, CHAT_ID, topic_id)

    except Exception as e:
        logger.error(f"Ошибка при выполнении ручного анализа '{analysis_type}': {e}", exc_info=True)
        bot.reply_to(message, f"❌ Произошла ошибка во время анализа '{analysis_type}': {e}")


@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'sticker'])
def moderate_topic(message):
    """Удаляет все сообщения в защищенных топиках, кроме сообщений от самого бота."""
    is_correct_chat = str(message.chat.id) == CHAT_ID
    is_correct_topic = str(message.message_thread_id) in MODERATED_TOPIC_IDS
    is_from_bot = message.from_user.id == bot.get_me().id

    if is_correct_chat and is_correct_topic and not is_from_bot:
        try:
            bot.delete_message(message.chat.id, message.message_id)
            logger.info(f"Удалено сообщение от пользователя {message.from_user.username} в модерируемом топике.")
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение: {e}")