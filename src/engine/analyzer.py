import logging
import sys
import re
from datetime import datetime
from src.services.gemini_client import GeminiClient
from src.config import OUTPUT_DIR, TOPIC_CONFIGS, SUPERGROUP_LINK
from src.services.news_collector_goog import gather_strategic_news
from data.allowed_tags_for_telegraph import ALLOWED_TAGS
from src.services.telegraph_client import TelegraphClient
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def _prepare_digest_for_ai(articles: list) -> str:
    """Готовит новостной дайджест для передачи в AI."""
    if not articles:
        return "Нет новостей для анализа."
    digest_parts = ["Вот дайджест свежих новостей для анализа:\n"]
    for i, article in enumerate(articles, 1):
        digest_parts.append(f"\n--- Новость #{i} ---\n")
        digest_parts.append(f"Источник: {article.get('source', 'N/A')}\n")
        digest_parts.append(f"Заголовок: {article.get('title', 'Без заголовка')}\n")
        digest_parts.append(f"Краткое содержание:\n{article.get('description', 'Нет данных.')}")
    return "".join(digest_parts)


def _sanitize_html_for_telegraph_old(html_content: str) -> str:
    """
    Очищает и адаптирует HTML для Telegraph, используя BeautifulSoup.
    - Заменяет неподдерживаемые теги заголовков (h1, h2) на поддерживаемые (h3, h4).
    - Удаляет все теги, не входящие в ALLOWED_TAGS.
    - Корректно обрабатывает маркеры списков и заголовки, которые "слиплись" с текстом.
    """
    if not html_content:
        return ""

    # --- ВОЗВРАЩАЕМ ПРЕДЫДУЩУЮ, БОЛЕЕ ПРОСТУЮ ЛОГИКУ ---
    # 1. Добавляем переносы строк перед ключевыми заголовками, чтобы BeautifulSoup
    #    гарантированно распознал их как отдельные блоки.
    separators = [
        "<b>КЛЮЧЕВЫЕ ТЕМЫ:</b>",
        "<b>РЕЗЮМЕ ТОРГОВЫХ ИДЕЙ:</b>",
        "<b>РЕЗЮМЕ ТОП-4 ИДЕЙ:</b>",
        "<b>АНАЛИЗ И ТЕЗИСЫ:</b>",
        "<b>АНАЛИЗ СИЛЫ ВАЛЮТ:</b>",
        "<b>ТЕХНИЧЕСКИЙ АНАЛИЗ И РЕКОМЕНДАЦИИ:</b>",
        "<b>Тема",
        "<b>Нарратив",
        "<b>Тикер:"
    ]
    for sep in separators:
        html_content = html_content.replace(sep, f"<br>{sep}")

    # 2. Заменяем маркеры списков на параграфы для лучшего форматирования
    # html_content = html_content.replace('•', '<p>•')

    soup = BeautifulSoup(html_content, 'html.parser')

    # 3. Замена неподдерживаемых тегов на поддерживаемые
    for h1_tag in soup.find_all('h1'):
        h1_tag.name = 'h3'
    for h2_tag in soup.find_all('h2'):
        h2_tag.name = 'h4'

    # 4. Удаление всех тегов, которых нет в разрешенном списке
    for tag in soup.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            # .unwrap() удаляет тег, но оставляет его содержимое
            tag.unwrap()

    return str(soup)

def _sanitize_html_for_telegraph(html_content: str) -> str:
    """
    Упрощенная очистка HTML для Telegraph.
    - Заменяет h1/h2 на h3/h4.
    - Удаляет все теги, не входящие в разрешенный список.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')

    # Замена неподдерживаемых тегов заголовков
    for h1_tag in soup.find_all('h1'):
        h1_tag.name = 'h3'
    for h2_tag in soup.find_all('h2'):
        h2_tag.name = 'h4'

    # Удаление всех тегов, которых нет в разрешенном списке
    for tag in soup.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()  # .unwrap() удаляет тег, но оставляет его содержимое

    return str(soup)


def run_full_analysis(analysis_config: dict) -> str:
    """
    Выполняет полный цикл анализа, создает страницу в Telegraph и возвращает
    сообщение со ссылкой для отправки в Telegram.
    """
    try:
        analysis_type = analysis_config.get("type_name", "Unknown")
        analysis_config['type_name'] = analysis_type

        prompt_template = analysis_config.get("prompt")
        parsing_keys = analysis_config.get("parsing_keys", {})

        # 1. Сбор новостей и запуск анализа Gemini
        logger.info(f"Сбор новостей для '{analysis_type}'...")
        news = gather_strategic_news(topics=analysis_config.get("news_topics", []))
        digest = _prepare_digest_for_ai(news)

        client = GeminiClient()
        analysis_parts = client.run_two_stage_analysis(
            digest=digest,
            prompt_template=prompt_template,
            parsing_keys=parsing_keys
        )

        stage1_text = analysis_parts.get("stage1")
        stage2_text = analysis_parts.get("stage2")

        # 2. Проверка результатов
        if not stage1_text or "[Ошибка" in stage1_text:
            error_msg = f"<b>Ошибка на 1-м этапе анализа ({analysis_type}):</b>\n<pre>{stage1_text or 'Нет ответа от модели.'}</pre>"
            logger.error(error_msg)
            return error_msg

        # Убираем техническую часть из первого блока
        stage1_clean = stage1_text.split("ЗАПРОС НА ВТОРОЙ ЭТАП")[0].strip()

        # 3. Формируем контент для Telegraph
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        page_title = f"Аналитический отчет: {analysis_type} ({timestamp})"

        # Собираем и очищаем весь HTML
        # Заголовок статьи
        full_html_content = f"<h3>{page_title}</h3>"
        # Добавляем очищенный HTML первого этапа
        full_html_content += _sanitize_html_for_telegraph(stage1_clean)

        # Добавляем очищенный HTML второго этаpa
        if stage2_text and "[Ошибка" not in stage2_text:
            # Теперь просто добавляем текст, так как он уже содержит заголовок <h4>
            full_html_content += _sanitize_html_for_telegraph(stage2_text)
        else:
            # Сообщение об ошибке, если второй этап не удался
            full_html_content += ("<h4>Технический анализ</h4><p><i>Технический анализ не был выполнен из-за ошибки "
                                  "или отсутствия данных.</i></p>")
        # 4. Публикация в Telegraph
        author_link = analysis_config.get("link", SUPERGROUP_LINK)
        telegraph_client = TelegraphClient(author_url=author_link)
        page_url = telegraph_client.create_page(title=page_title, html_content=full_html_content)

        if not page_url:
            return f"<b>Ошибка публикации в Telegraph.</b> Анализ ({analysis_type}) был выполнен, но не удалось создать страницу."

        # 5. Формирование финального сообщения для Telegram
        summary_section_key = "РЕЗЮМЕ ТОРГОВЫХ ИДЕЙ:"
        if "РЕЗЮМЕ ТОП-4 ИДЕЙ:" in stage1_clean:
            summary_section_key = "РЕЗЮМЕ ТОП-4 ИДЕЙ:"

        try:
            # Используем BeautifulSoup для надежного извлечения блока с резюме
            soup = BeautifulSoup(stage1_clean, 'html.parser')
            summary_header = soup.find('h4', string=re.compile(summary_section_key))
            summary_list = summary_header.find_next_sibling('ul')
            summary_html = str(summary_list)

            preview_text = f"<b>{page_title}</b>\n\n<h4>{summary_section_key}</h4>{summary_html}"
        except (AttributeError, IndexError):
            preview_text = f"<b>{page_title}</b>\n\n<i>Подробный анализ доступен по ссылке.</i>"

        final_message = f"{preview_text}\n\n<a href='{page_url}'><b>➡️ Читать полный анализ</b></a>"

        return final_message

    except Exception as e:
        logger.critical(f"Критическая ошибка в 'run_full_analysis': {e}", exc_info=True)
        return f"<b>Критическая ошибка в 'run_full_analysis':</b>\n<pre>{e}</pre>"


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
