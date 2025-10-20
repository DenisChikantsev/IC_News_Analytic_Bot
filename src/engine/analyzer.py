import logging
import sys
import re
from datetime import datetime
from src.services.gemini_client import GeminiClient
from src.config import OUTPUT_DIR, TOPIC_CONFIGS
from src.services.news_collector_goog import gather_strategic_news

logger = logging.getLogger(__name__)

def _prepare_digest_for_ai(articles: list) -> str:
    # ... (этот код без изменений)
    if not articles:
        return "Нет новостей для анализа."
    digest_parts = ["Вот дайджест свежих новостей для анализа:\n"]
    for i, article in enumerate(articles, 1):
        digest_parts.append(f"\n--- Новость #{i} ---\n")
        digest_parts.append(f"Источник: {article.get('source', 'N/A')}\n")
        digest_parts.append(f"Заголовок: {article.get('title', 'Без заголовка')}\n")
        digest_parts.append(f"Краткое содержание:\n{article.get('description', 'Нет данных.')}")
    return "".join(digest_parts)


def _format_theses_block_as_html(raw_text: str) -> str:
    """Преобразует сырой текст блока тезисов в красивый HTML для Telegram."""
    if not raw_text:
        return ""

    # 1. Заменяем маркеры нарративов на жирные заголовки
    # Пример: "*   **Нарратив 1:...** ->" превратится в "<b>Нарратив 1:...</b>"
    formatted_text = re.sub(r'\*\s*\*\*(.*?)\*\*\s*->', r'<b>\1</b>', raw_text)

    # 2. Оборачиваем тикеры и направление в тег <code> для выделения
    # Пример: "BTC: SHORT" превратится в "<code>BTC: SHORT</code>"
    formatted_text = re.sub(r'([A-Z]{2,6}:\s*(?:LONG|SHORT|BUY|SELL))', r'<code>\1</code>', formatted_text)

    # 3. Убираем лишние символы и пробелы для чистоты
    formatted_text = formatted_text.replace('*', '').strip()

    return formatted_text


def _extract_analysis_block(full_text: str, parsing_keys: dict) -> str | None:
    """Извлекает и ФОРМАТИРУЕТ блок с тезисами, используя ключи из конфига."""
    analysis_key = parsing_keys.get("analysis_section", "АНАЛИЗ И ТЕЗИСЫ")
    tickers_key = parsing_keys.get("tickers_section", "ЗАПРОС НА ВТОРОЙ ЭТАП")
    try:
        # 1. Извлекаем сырой текст блока
        after_header = re.split(rf"{analysis_key}:", full_text, maxsplit=1, flags=re.IGNORECASE)[1]
        raw_block = re.split(rf"{tickers_key}:", after_header, maxsplit=1, flags=re.IGNORECASE)[0]

        # --- ИЗМЕНЕНИЕ: Форматируем извлеченный блок ---
        # 2. Передаем сырой текст в нашу новую функцию-форматировщик
        formatted_block = _format_theses_block_as_html(raw_block)

        # 3. Собираем финальное сообщение с жирным заголовком
        return f"<b>{analysis_key.upper()}:</b>\n{formatted_block}"

    except (IndexError, re.error):
        logger.warning(f"Не удалось извлечь блок '{analysis_key}' из отчета первого этапа.")
        return None


def run_full_analysis(analysis_config: dict) -> list[str]:
    """
    Выполняет полный цикл анализа и возвращает список сообщений для отправки в Telegram.
    """
    # ... (весь остальной код функции run_full_analysis остается без изменений)
    messages_to_send = []
    try:
        news_topics = analysis_config.get("news_topics", [])
        prompt_template = analysis_config.get("prompt")
        parsing_keys = analysis_config.get("parsing_keys", {})
        if not prompt_template:
            raise ValueError("Шаблон промпта не найден в конфигурации.")
        logger.info(f"Сбор новостей по темам: {news_topics}")
        news = gather_strategic_news(topics=news_topics)
        digest = _prepare_digest_for_ai(news)
        client = GeminiClient()
        analysis_parts = client.run_two_stage_analysis(
            digest=digest,
            prompt_template=prompt_template,
            parsing_keys=parsing_keys
        )

        # Сохранение полного отчета в файл (логика без изменений)
        full_report_text = analysis_parts.get("stage1", "")
        if analysis_parts.get("stage2"):
            full_report_text += "\n\n" + analysis_parts.get("stage2")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"gemini_analysis_{timestamp}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_report_text)
        logger.info(f"--- Полный анализ сохранен в файл '{output_file}' ---")

        # --- ЛОГИКА ФОРМИРОВАНИЯ СПИСКА СООБЩЕНИЙ ---
        stage1_text = analysis_parts.get("stage1")
        stage2_text = analysis_parts.get("stage2")

        # 1. Добавляем блок с тезисами, если он найден
        if stage1_text:
            theses_block = _extract_analysis_block(stage1_text, parsing_keys)
            if theses_block:
                messages_to_send.append(theses_block)

        # 2. Добавляем технический анализ или сообщение об ошибке
        if not stage2_text or "[Ошибка" in stage2_text:
            error_msg = "Технический анализ не удался или произошла ошибка."
            logger.error(error_msg)
            details = stage2_text or stage1_text
            messages_to_send.append(f"{error_msg}\n\n<b>Детали:</b>\n<pre>{details}</pre>")
        else:
            messages_to_send.append(stage2_text)

    except Exception as e:
        logger.critical(f"--- Произошла критическая ошибка в 'run_full_analysis': {e} ---", exc_info=True)
        messages_to_send.append(f"--- Произошла критическая ошибка в 'run_full_analysis': {e} ---")

    if not messages_to_send:
        messages_to_send.append("Анализ завершился без результата.")

    # Добавляем временную метку в конец ПОСЛЕДНЕГО сообщения
    timestamp_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    footer = f"\n\n<i>Отчет сформирован: {timestamp_str}</i>"
    messages_to_send[-1] += footer

    return messages_to_send


if __name__ == '__main__':
    # Этот блок полезен для быстрого локального теста
    analysis_type_to_test = "CRYPTO"
    logger.info(f"Запуск тестового анализа для {analysis_type_to_test}...")

    if analysis_type_to_test in TOPIC_CONFIGS:
        result_for_bot = run_full_analysis(TOPIC_CONFIGS[analysis_type_to_test])
        logger.info("\n--- РЕЗУЛЬТАТ ДЛЯ ОТПРАВКИ В БОТА ---")
        logger.info(result_for_bot)
    else:
        logger.error(f"Тип анализа '{analysis_type_to_test}' не найден в config.py")
