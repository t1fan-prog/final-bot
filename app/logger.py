import logging


def create_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger_handler = logging.FileHandler('bot_logger.log')
    logger_handler.setLevel(logging.INFO)
    logger_formatter = logging.Formatter('%(name)s - %(asctime)s - %(levelname)s - %(message)s')

    logger_handler.setFormatter(logger_formatter)

    logger.addHandler(logger_handler)
    return logger
