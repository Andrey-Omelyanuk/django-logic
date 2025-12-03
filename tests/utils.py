import logging
from typing import List, Dict, Any, Type
from django_logic.constants import LogType
from django.conf import settings


class ListLogger(logging.Logger):
    """
    A custom logger class that stores all log records in a list.
    Use it only for testing purposes.
    """
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self.records: List[logging.LogRecord] = []
        # Add a handler that stores records
        self.addHandler(self._ListLogHandler(self))

    class _ListLogHandler(logging.Handler):
        """Internal handler that stores records in the parent logger's list."""
        def __init__(self, parent_logger):
            super().__init__()
            self.parent_logger = parent_logger

        def emit(self, record: logging.LogRecord) -> None:
            """Store the log record in the parent logger's list."""
            self.parent_logger.records.append(record)

    def clear(self) -> None:
        """Clear all stored log records."""
        self.records.clear()

    def get_logs(self) -> List[Dict[str, Any]]:
        """
        Get all logs as a list of dictionaries with useful information.
        Returns a list of dicts with keys: levelname, message, log_type, log_data
        """
        result = []
        for record in self.records:
            log_dict = {
                'levelname': record.levelname,
                'message': record.getMessage(),
                'log_type': getattr(record, 'log_type', None),
                'log_data': getattr(record, 'log_data', None),
            }
            result.append(log_dict)
        return result

    def get_logs_by_type(self, log_type: LogType) -> List[Dict[str, Any]]:
        """Get logs filtered by log_type."""
        return [log for log in self.get_logs() if log['log_type'] == log_type]

    def get_logs_by_level(self, level: str) -> List[Dict[str, Any]]:
        """Get logs filtered by level (e.g., 'INFO', 'ERROR')."""
        return [log for log in self.get_logs() if log['levelname'] == level]

    def has_log(self, message_substring: str, log_type: LogType = None) -> bool:
        """Check if a log exists with the given message substring and optionally log_type."""
        logs = self.get_logs()
        for log in logs:
            if message_substring in log['message']:
                if log_type is None or log['log_type'] == log_type:
                    return True
        return False


def reload_logger(new_logger_class: Type[logging.Logger] = None):
    """
    Reload django_logic logger class
    Only for testing purposes when test overrides DJANGO_LOGIC_CUSTOM_LOGGER.
    """
    logger_manager = logging.Logger.manager
    # Remove existing logger instance if it exists
    del logger_manager.loggerDict['django-logic.transition']
    logger_class = new_logger_class or getattr(settings, 'DJANGO_LOGIC_CUSTOM_LOGGER', logging.Logger)
    logging.setLoggerClass(logger_class)
    return logging.getLogger('django-logic.transition')
