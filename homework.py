import logging
import os
import requests
import telegram
import time
from http import HTTPStatus

from dotenv import load_dotenv

from exceptions import (ListHomeworkEmptyError, ResponseStatusCodeError,
                        RequestExceptionError)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Обращается к API Telegram и отправляет сообщение боту."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info(
            f'Отправлено сообщение в Telegram: {message}')
    except telegram.TelegramError as error:
        logger.error(
            f'Сообщение в Telegram не отправлено: {error}')


def get_api_answer(current_timestamp):
    """Обращается к API Яндекс Практикум и получает статус домашней работы."""
    if current_timestamp is None:
        current_timestamp = int(time.time())
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            url_error_message = (
                f'Ссылка {ENDPOINT} недоступна.'
                f'Код ответа: {response.status_code}.')
            logger.error(url_error_message)
            raise ResponseStatusCodeError(url_error_message)
        return response.json()
    except ConnectionError:
        logging.error('Ошибка сервера')
    except requests.exceptions.RequestException as request_error:
        request_error_message = f'Код ответа API: {request_error}'
        logger.error(request_error_message)
        raise RequestExceptionError(request_error_message)


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        message = 'Ответ не является словарем!'
        logger.error(message)
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'Ключа homeworks нет в словаре.'
        logger.error(message)
        raise KeyError(message)
    if type(response['homeworks']) is not list:
        message = 'Домашние работы не являются списком'
        logger.error(message)
        raise TypeError(message)
    if not response['homeworks']:
        message = 'Список работ пуст'
        logger.error(message)
        raise ListHomeworkEmptyError(message)
    else:
        return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_name is None:
        raise Exception('Not correct name')
    if homework_status is None:
        raise Exception('Not correct status')
    verdict = HOMEWORK_STATUSES[homework.get('status')]
    if homework.get("status") not in HOMEWORK_STATUSES.keys():
        message = 'Статус работы неверный.'
        logger.error(message)
        raise KeyError(message)
    if verdict is None:
        raise Exception("No verdict")
    logging.info(f'got verdict {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = ('Отсутствует переменная окружения:')
    tokens_bool = True
    if PRACTICUM_TOKEN is None:
        tokens_bool = False
        logger.critical(
            f'{tokens} PRACTICUM_TOKEN')
    if TELEGRAM_TOKEN is None:
        tokens_bool = False
        logger.critical(
            f'{tokens} TELEGRAM_TOKEN')
    if TELEGRAM_CHAT_ID is None:
        logger.critical(
            f'{tokens} TELEGRAM_CHAT_ID')
    return tokens_bool


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            new_homework = get_api_answer(ENDPOINT, current_timestamp)
            check_response_result = check_response(new_homework)
            if check_response_result:
                for homework in check_response_result:
                    parse_status_result = parse_status(homework)
                    send_message(bot, parse_status_result)
            time.sleep(RETRY_TIME)
        except Exception as error:
            logging.error('Бот упал')
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f'Сбой в работе программы: {error}'
            )
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
