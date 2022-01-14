class Error(Exception):
    """Базовый класс"""

    pass


class ListHomeworkEmptyError(Error):
    """Список пуст."""

    pass


class ResponseStatusCodeError(Error):
    """Неверный статус ответа сервера."""

    pass


class RequestExceptionError(Error):
    """Неверный запрос."""

    pass
