import logging
from typing import Type
from django.conf import settings


CUSTOM_LOGGER: Type[logging.Logger] = getattr(settings, 'DJANGO_LOGIC_CUSTOM_LOGGER', logging.Logger)
logging.setLoggerClass(CUSTOM_LOGGER)
logger: logging.Logger = logging.getLogger('django_logic')
logger.setLevel(getattr(settings, 'DJANGO_LOGIC_LOG_LEVEL', logging.INFO))
