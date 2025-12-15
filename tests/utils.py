import logging
from typing import List, Dict, Any, Optional


class ListHandler(logging.Handler):
    """A logging handler that collects log records into a list."""
    
    def __init__(self):
        super().__init__()
        self.logs: List[Dict[str, Any]] = []
    
    def emit(self, record: logging.LogRecord) -> None:
        """Collect log record into the list."""
        # Standard log record fields
        log_entry = {
            'message': record.getMessage(),
            'level': record.levelname,
            'levelno': record.levelno,
            'logger_name': record.name,
            'module': record.module,
            'funcName': record.funcName,
            'lineno': record.lineno,
            'created': record.created,
        }
        
        # Standard LogRecord attributes (built-in, don't capture these as extras)
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName', 'levelname',
            'levelno', 'lineno', 'module', 'msecs', 'message', 'pathname', 'process',
            'processName', 'relativeCreated', 'thread', 'threadName', 'exc_info',
            'exc_text', 'stack_info', 'getMessage', 'exc_info', 'exc_text', 'stack_info'
        }
        
        # Capture all custom attributes (from extra parameter in logger calls)
        # These become direct attributes on the LogRecord object
        for attr_name in dir(record):
            if attr_name.startswith('_') or attr_name in standard_attrs:
                continue
            try:
                value = getattr(record, attr_name)
                # Only include non-callable attributes
                if not callable(value):
                    log_entry[attr_name] = value
            except (AttributeError, TypeError):
                pass
        
        self.logs.append(log_entry)
    
    def clear(self) -> None:
        """Clear all collected logs."""
        self.logs.clear()
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all collected logs."""
        return self.logs.copy()
    
    def has_log(self, message_substring: str) -> bool:
        """Check if a log exists with the given message substring and optionally log type."""
        for log in self.logs:
            if message_substring in log['message']:
                return True
        return False


class ListLogger(logging.Logger):
    """A logger that extends standard logger and provides convenient access to collected logs."""
    
    def __init__(self, handler: ListHandler, logger: logging.Logger):
        # Initialize the parent Logger class with the logger's name
        super().__init__(logger.name, logger.level)
        # Copy all handlers and configuration from the original logger
        self.handlers = logger.handlers[:]
        self.propagate = logger.propagate
        self.filters = logger.filters[:]
        self.disabled = logger.disabled
        # Store the handler for log collection
        self.handler = handler
    
    def clear(self) -> None:
        """Clear all collected logs."""
        self.handler.clear()
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all collected logs."""
        return self.handler.get_logs()
    
    def has_log(self, message_substring: str) -> bool:
        """Check if a log exists with the given message substring and optionally log type."""
        return self.handler.has_log(message_substring)


# Global handler instance - set up once when module is imported
_handler: Optional[ListHandler] = None
_list_logger: Optional[ListLogger] = None


def _setup_handler():
    """Set up the handler once at module level."""
    global _handler, _list_logger
    
    if _handler is None:
        # Get the transition logger
        transition_logger = logging.getLogger('django-logic.transition')
        
        # Create and attach the list handler
        _handler = ListHandler()
        _handler.setLevel(logging.DEBUG)
        transition_logger.addHandler(_handler)
        transition_logger.setLevel(logging.DEBUG)
        
        # Prevent propagation to avoid duplicate logs
        transition_logger.propagate = False
        
        _list_logger = ListLogger(_handler, transition_logger)
    
    return _list_logger


# Set up the handler when module is imported
_setup_handler()


def get_test_logger() -> ListLogger:
    """Get the global ListLogger instance for tests."""
    return _list_logger


def assert_dict_contains(dict_a: Dict[str, Any], dict_b: Dict[str, Any]) -> bool:
    """
    Checks if dictionary A contains all keys from dictionary B with the same values.
    
    Args:
        dict_a: Dictionary that may contain more keys
        dict_b: Dictionary whose keys are used for comparison
    
    Returns:
        True if dict_a contains all keys from dict_b with matching values, False otherwise
    
    Example usage:
        def test_something(self):
            obj_a = {'field1': 'value1', 'field2': 'value2', 'extra': 'extra'}
            obj_b = {'field1': 'value1', 'field2': 'value2'}
            self.assertTrue(assert_dict_contains(obj_a, obj_b))
    """
    # Check that all keys from B are present in A
    missing_keys = set(dict_b.keys()) - set(dict_a.keys())
    if missing_keys:
        print(f"Missing keys in dict_a: {missing_keys}")
        return False
    
    # Create a subset of A with keys from B
    subset_a = {k: dict_a[k] for k in dict_b.keys()}
    
    # Compare the dictionaries and print differences
    mismatches = []
    for key in dict_b.keys():
        if subset_a[key] != dict_b[key]:
            mismatches.append({
                'key': key,
                'expected': dict_b[key],
                'actual': subset_a[key]
            })
    
    if mismatches:
        print("Mismatched values:")
        for mismatch in mismatches:
            print(f"  Key '{mismatch['key']}':")
            print(f"    Expected: {mismatch['expected']!r}")
            print(f"    Actual:   {mismatch['actual']!r}")
        return False
    
    return True
