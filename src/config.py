import os
from pathlib import Path
from dotenv import load_dotenv
from src.prompts import *

# Загружаем переменные из .env файла
load_dotenv()

# --- Пути ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "output"

# Убедимся, что директория для вывода существует
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Ключи API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN")
# Проверяем наличие токена
if not BOT_TOKEN:
    raise ValueError("Токен телеграм-бота (BOT_TOKEN) не найден в .env файле.")

# --- Настройки Telegram ---
ADMIN_ID = os.getenv("ADMIN_ID")
SUPERGROUP_LINK = os.getenv("SUPERGROUP_LINK")
CHAT_ID = os.getenv("SUPERGROUP_ID")
CURRENCY_ID = os.getenv("CURRENCY_ID")
CRYPTO_ID = os.getenv("CRYPTO_ID")
USA_STOCKS_ID = os.getenv("USA_STOCKS_ID")

# --- Опции парсинга новостей ---
NEWS_SOURCE = "google"  # Варианты: "google", "newsapi"


# --- Конфигурация топиков для анализа ---
TOPIC_CONFIGS = {
    "USA_STOCKS": {
        "id": os.getenv("USA_STOCKS_ID"),
        "prompt": USA_STOCKS_PROMPT,
        "news_source": "google",
        "news_topics": ['WORLD','BUSINESS','TECHNOLOGY',
                        'ECONOMY','FINANCE','ENERGY', 'GEOPOLITICS'],
        "parsing_keys": {
            "analysis_section": "АНАЛИЗ И ТЕЗИСЫ",
            "tickers_section": "ЗАПРОС НА ВТОРОЙ ЭТАП"
        }
    },
    "CRYPTO": {
        "id": os.getenv("CRYPTO_ID"),
        "prompt": CRYPTO_PROMPT,
        "news_source": "google",
        "news_topics": ['CRYPTOCURRENCIES', 'BITCOIN', 'ETHEREUM',
                        'REGULATION', 'LAWS', 'ENERGY', 'TECHNOLOGY',
                        'FINANCE', 'COMPANIES'],
        "parsing_keys": {
            "analysis_section": "АНАЛИЗ И ТЕЗИСЫ",
            "tickers_section": "ЗАПРОС НА ВТОРОЙ ЭТАП"
        }
    },
    "CURRENCY": {
        "id": os.getenv("CURRENCY_ID"),
        "prompt": CURRENCY_PROMPT,
        "news_source": "google",
        "news_topics": ['FOREX', 'CURRENCY', 'ECONOMY',
                        'FINANCE', 'POLITICS', 'MARKETS',
                        'COMMODITIES'],
        "parsing_keys": {
            "analysis_section": "АНАЛИЗ СИЛЫ ВАЛЮТ",
            "tickers_section": "ЗАПРОС НА ВТОРОЙ ЭТАП"
        }
    }
}