import re
import logging
import google.genai as genai
from google.genai.types import Tool, GoogleSearch, GenerateContentConfig
from src.config import GEMINI_API_KEY, USA_STOCKS_PROMPT

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
        # ----------------------------------------------------
        logger.info(
            f"Клиент Gemini инициализирован с моделью '{self.model_name}' и доступом в интернет."
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
            return response.text
        except Exception as e:
            error_message = f"[Ошибка при обращении к Gemini API: {e}]"
            logger.error(error_message, exc_info=True)
            return error_message

    def _parse_stage1_tickers(self, analysis_text: str) -> list[str]:
        """
        Извлекает тикеры из блока 'ЗАПРОС НА ВТОРОЙ ЭТАП'.
        Поддерживает нумерованные списки, списки с маркерами (* или -) и списки в скобках.
        """
        section_match = re.search(r"ЗАПРОС НА ВТОРОЙ ЭТАП:.*", analysis_text, re.IGNORECASE | re.DOTALL)
        if not section_match:
            logger.warning("Не удалось найти секцию 'ЗАПРОС НА ВТОРОЙ ЭТАП'.")
            return []

        section_text = section_match.group(0)

        tickers = re.findall(r"[\*\-]\s*\*?([A-Z]{1,5})\*?", section_text)
        if tickers:
            tickers = [t.strip() for t in tickers]
            logger.info(f"Найдены тикеры для 2-го этапа (формат списка с маркерами): {tickers}")
            return tickers

        # Затем ищем нумерованные списки
        tickers = re.findall(r"\d+\.\s*\*?([A-Z]{1,5})\*?", section_text)
        if tickers:
            tickers = [t.strip() for t in tickers]
            logger.info(f"Найдены тикеры для 2-го этапа (формат нумерованного списка): {tickers}")
            return tickers

        # Резервный вариант: ищем формат в скобках
        match = re.search(r"\((.*?)\)", section_text, re.IGNORECASE | re.DOTALL)
        if match:
            tickers_str = match.group(1)
            potential_tickers = [t.strip() for t in tickers_str.split(',')]
            tickers = [t for t in potential_tickers if re.fullmatch(r'[A-Z]{1,5}', t)]
            if tickers:
                logger.info(f"Найдены тикеры для 2-го этапа (формат в скобках): {tickers}")
                return tickers

        logger.warning(
            "Не удалось найти тикеры для второго этапа анализа. Формат ответа модели не соответствует ожидаемому.")
        return []

    def _parse_stage1_analysis_block(self, analysis_text: str) -> str | None:
        """Извлекает весь блок 'АНАЛИЗ И ТЕЗИСЫ' для передачи в следующий этап."""
        match = re.search(r"АНАЛИЗ И ТЕЗИСЫ:\s*(.*)", analysis_text, re.DOTALL | re.IGNORECASE)
        if not match:
            logger.warning("Не удалось найти блок 'Анализ и Тезисы'.")
            return None
        analysis_block = match.group(1).split('ЗАПРОС НА ВТОРОЙ ЭТАП:')[0].strip()
        return analysis_block

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

                        **ФОРМАТ ВЫХОДА (строго соблюдай структуру и верни весь ответ в формате Markdown):**

                        **ТЕХНИЧЕСКИЙ АНАЛИЗ И РЕКОМЕНДАЦИИ:**

                        **Тикер: [Тикер 1]**
                        *   **Технические данные:** Цена: [значение], MA50: [значение], MA200: [значение], RSI: [значение]
                        *   **Рекомендация:** [Твоя краткая рекомендация и уровни]
                        *   **Срок реализации:** [Краткосрочный/Среднесрочный/Долгосрочный]

                        **Тикер: [Тикер 2]**
                        ... и так далее.
                        """
        prompt_parts.append(task_prompt)
        return "\n".join(prompt_parts)

    def run_two_stage_analysis(self, digest: str, prompt_template: str) -> dict[str, str]:
        """
        Выполняет полный двухэтапный анализ и возвращает результат в виде словаря.
        Возвращает: {"stage1": "текст первого этапа", "stage2": "текст второго этапа"}
        """
        logger.info("--- Запуск 1-го этапа анализа (фундаментальный) ---")
        stage1_prompt = prompt_template.replace("[Вставь полный дайджест новостей]", digest)
        analysis_part_1 = self._execute_analysis(stage1_prompt)

        if "[Ошибка" in analysis_part_1:
            return {"stage1": analysis_part_1, "stage2": ""}

        tickers = self._parse_stage1_tickers(analysis_part_1)
        analysis_block = self._parse_stage1_analysis_block(analysis_part_1)

        if not tickers or not analysis_block:
            logger.warning("Не удалось извлечь данные для 2-го этапа. Возвращаю только 1-й этап.")
            # ИЗМЕНЕНИЕ: Возвращаем словарь, но вторая часть пустая.
            return {"stage1": analysis_part_1, "stage2": ""}

        logger.info("--- Запуск 2-го этапа анализа (технический) ---")
        stage2_prompt = self._construct_stage2_prompt(tickers, analysis_block)
        analysis_part_2 = self._execute_analysis(stage2_prompt)

        # ИЗМЕНЕНИЕ: Возвращаем словарь с двумя частями.
        return {"stage1": analysis_part_1, "stage2": analysis_part_2}