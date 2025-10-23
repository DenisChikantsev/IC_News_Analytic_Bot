import logging
from os import access

from telegraph import Telegraph
from telegraph.exceptions import TelegraphException
from src.config import TELEGRAPH_ACCESS_TOKEN, SUPERGROUP_LINK

logger = logging.getLogger(__name__)


class TelegraphClient:
    def __init__(self, author_name="Author", author_url=SUPERGROUP_LINK):
        """
        Инициализирует клиент Telegraph.
        author_name: Имя автора, которое будет отображаться на странице.
        author_url: Ссылка, которая будет привязана к имени автора.
        """
        if not TELEGRAPH_ACCESS_TOKEN:
            raise ValueError("Токен TELEGRAPH_ACCESS_TOKEN не найден в переменных окружения.")

        self.client = Telegraph(access_token=TELEGRAPH_ACCESS_TOKEN)
        self.author_name = author_name
        self.author_url = author_url
        logger.info("Клиент Telegraph успешно инициализирован.")

    def create_page(self, title: str, html_content: str) -> str | None:
        """
        Создает новую страницу в Telegraph и возвращает ссылку на нее.

        Args:
            title: Заголовок страницы.
            html_content: Содержимое страницы в формате HTML.

        Returns:
            URL созданной страницы или None в случае ошибки.
        """
        try:
            response = self.client.create_page(
                title=title,
                html_content=html_content,
                author_name=self.author_name,
                author_url=self.author_url
            )
            page_url = f"https://telegra.ph/{response['path']}"
            logger.info(f"Страница Telegraph успешно создана: {page_url}")
            return page_url
        except TelegraphException as e:
            logger.error(f"Ошибка при создании страницы в Telegraph: {e}", exc_info=True)
            return None


# Пример использования (можно удалить или закомментировать)
if __name__ == '__main__':
    client = TelegraphClient()
    test_title = "Тестовый отчет"
    test_content = "<h2>Заголовок</h2><p>Это <b>тестовый</b> параграф с <i>курсивом</i> и <code>кодом</code>.</p>"
    url = client.create_page(test_title, test_content)
    if url:
        print(f"Страница создана: {url}")