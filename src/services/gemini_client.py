import re
import logging
import google.genai as genai
from google.genai.types import Tool, GoogleSearch, GenerateContentConfig
from google.genai.errors import ServerError
from src.config import GEMINI_API_KEY
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Клиент для взаимодействия с Google Gemini API, использующий
    современный способ подключения инструментов.
    """

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("Ключ GEMINI_API_KEY не найден в переменных окружения.")
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = 'gemini-2.5-flash'
        search_tool = Tool(google_search=GoogleSearch())
        self.generation_config = GenerateContentConfig(
            tools=[search_tool],
            temperature=0.7
        )
        logger.info(
            f"Клиент Gemini инициализирован с моделью '{self.model_name}' и доступом в интернет."
        )

    @retry(
        # Ждем с экспоненциальной задержкой: 1с, 2с, 4с, 8с...
        wait=wait_exponential(multiplier=1, min=1, max=60),
        # Останавливаемся после 5 попыток
        stop=stop_after_attempt(5),
        # Повторяем только при серверных ошибках (503, 500) или таймаутах
        retry=retry_if_exception_type((ServerError)),
        # Логируем каждую попытку
        before_sleep=lambda retry_state: logger.warning(
            f"Получена ошибка от Gemini, повторная попытка #{retry_state.attempt_number} "
            f"через {int(retry_state.next_action.sleep)} секунд..."
        )
    )

    def _execute_analysis(self, prompt: str) -> str:
        """Приватный метод для выполнения запроса к Gemini."""
        logger.info("Отправка запроса в Gemini... (Это может занять некоторое время)")
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self.generation_config
            )

            logger.info("Ответ от Gemini получен.")
            return response.text or ""
        except Exception as e:
            error_message = f"[Ошибка при обращении к Gemini API: {e}]"
            logger.error(error_message, exc_info=True)
            return error_message

    def _parse_stage1_tickers(self, analysis_text: str, parsing_keys: dict) -> list[str]:
        # Используем ключ из конфига, с запасным вариантом по умолчанию
        tickers_key = parsing_keys.get("tickers_section", "ЗАПРОС НА ВТОРОЙ ЭТАП")

        match = re.search(rf"{tickers_key}:.*", analysis_text, re.IGNORECASE | re.DOTALL)
        if not match:
            logger.warning(f"Не удалось найти секцию '{tickers_key}'.")
            return []

        section_text = match.group(0)
        # Этот Regex найдет и тикеры (BTC), и валютные пары (EUR/USD)
        tickers = re.findall(r'\b[A-Z]{2,6}(?:/[A-Z]{2,3})?\b', section_text)

        if not tickers:
            logger.warning(f"В секции '{tickers_key}' не найдено тикеров.")
            return []

        logger.info(f"Найдены тикеры для 2-го этапа: {tickers}")
        return tickers

    def _parse_stage1_analysis_block(self, analysis_text: str, parsing_keys: dict) -> str | None:
        # Используем ключи из конфига
        analysis_key = parsing_keys.get("analysis_section", "АНАЛИЗ И ТЕЗИСЫ")
        tickers_key = parsing_keys.get("tickers_section", "ЗАПРОС НА ВТОРОЙ ЭТАП")

        try:
            # Разделяем по ключу начала анализа
            after_header = re.split(rf"{analysis_key}:", analysis_text, maxsplit=1, flags=re.IGNORECASE)[1]
            # Разделяем по ключу конца анализа (началу следующей секции)
            analysis_block = re.split(rf"{tickers_key}:", after_header, maxsplit=1, flags=re.IGNORECASE)[0]
            return analysis_block.strip()
        except IndexError:
            logger.warning(f"Не удалось найти или корректно распарсить блок '{analysis_key}'.")
            return None

    def _construct_stage2_prompt(self, tickers: list[str], analysis_block: str) -> str:
        """Создает промпт для второго, технического, этапа анализа."""
        prompt_parts = [
            "Ты — продвинутый технический аналитик. Твоя задача - дополнить существующий фундаментальный анализ техническими данными.",
            "Вот первоначальный анализ, основанный на новостях:",
            "--- НАЧАЛО ИСХОДНОГО АНАЛИЗА ---",
            analysis_block,
            "--- КОНЕЦ ИСХОДНОГО АНАЛИЗА ---",
            f"\nТеперь, для следующих тикеров, которые были отобраны для второго этапа ({', '.join(tickers)}), выполни технический анализ."
        ]
        task_prompt = """
                                Для каждого тикера из списка:
                                1.  **Найди актуальные технические данные:** Используя поиск в интернете, найди:
                                    *   Текущая цена закрытия (Current Closing Price)
                                    *   50-дневная скользящая средняя (MA50)
                                    *   200-дневная скользящая средняя (MA200)
                                    *   Индекс относительной силы (RSI, 14 дней)
                                2.  **Сформулируй финальную рекомендацию:** Основываясь на этих технических данных, подтверди, отмени или скорректируй исходную торговую идею. Дай конкретную **Целевую Цену (Target Price)** или **Уровень Стоп-Лосса (Stop-Loss)**.

                                <b>ФОРМАТ ВЫХОДА (строго соблюдай структуру HTML для Telegraph):</b>

                                <h4>ТЕХНИЧЕСКИЙ АНАЛИЗ И РЕКОМЕНДАЦИИ:</h4>

                                <h4>Тикер: [Тикер 1]</h4>
                                <ul>
                                    <li><i>Технические данные:</i> Цена: [значение], MA50: [значение], MA200: [значение], RSI: [значение]</li>
                                    <li><i>Рекомендация:</i> [Твоя краткая рекомендация и уровни]</li>
                                    <li><i>Срок реализации:</i> [Краткосрочный/Среднесрочный/Долгосрочный]</li>
                                </ul>

                                <h4>Тикер: [Тикер 2]</h4>
                                ... и так далее.
                                """
        prompt_parts.append(task_prompt)
        return "\n".join(prompt_parts)


    def run_two_stage_analysis(self, digest: str, prompt_template: str, parsing_keys: dict) -> dict[str, str]:
        logger.info("--- Запуск 1-го этапа анализа (фундаментальный) ---")
        stage1_prompt = prompt_template.replace("[Вставь полный дайджест новостей]", digest)
        analysis_part_1 = self._execute_analysis(stage1_prompt)

        if "[Ошибка" in analysis_part_1:
            return {"stage1": analysis_part_1, "stage2": ""}

        # Передаем ключи в парсеры
        tickers = self._parse_stage1_tickers(analysis_part_1, parsing_keys)
        analysis_block = self._parse_stage1_analysis_block(analysis_part_1, parsing_keys)

        if not tickers or not analysis_block:
            logger.warning("Не удалось извлечь данные для 2-го этапа. Возвращаю только 1-й этап.")
            return {"stage1": analysis_part_1, "stage2": ""}

        logger.info("--- Запуск 2-го этапа анализа (технический) ---")
        stage2_prompt = self._construct_stage2_prompt(tickers, analysis_block)
        analysis_part_2 = self._execute_analysis(stage2_prompt)

        return {"stage1": analysis_part_1, "stage2": analysis_part_2}