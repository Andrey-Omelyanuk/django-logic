import logging

# Lib logger for logging all activity of django-logic.
logger: logging.Logger = logging.getLogger('django-logic')
# Special logger for logging only activity of transitions.
transition_logger: logging.Logger = logging.getLogger('django-logic.transition')
