import logging

# Lib logger for logging all activity of django-logic.
logger: logging.Logger = logging.getLogger('django-logic')
# Special logger for logging only activity of transitions.
transition_logger: logging.Logger = logging.getLogger('django-logic.transition')

# Template for transition logs:
# timestamp parent_id tr_id <action_name> ...args
# ------------------------------------------
# Transition logs example:
# timestamp parent_id tr_id Start ProcessName TransitionName instance_key     - first is declaretion of the transition
# timestamp parent_id tr_id Celery celery_task id celery_root_id              - if run into celery add more logs about it
# timestamp parent_id tr_id Lock
# timestamp parent_id tr_id SideEffect A                                      - side effect is started
# timestamp parent_id tr_id SideEffect B                                      - new side effect means the previous one was completed
# timestamp parent_id tr_id UnLock
# timestamp parent_id tr_id Callback A                                        - a callback is started
# timestamp parent_id tr_id Callback B                                        - new callback means the previous one was completed
# timestamp parent_id tr_id Done                                              - transition is completed

#############################################################
# Callbacks can be executed in a celery task, more over, each callback can be executed in own celery task.
# Only celery_root_id can connect all the callbacks together.

# example if we run all callbacks in a celery task:
# -------------------------------------------
# timestamp parent_id tr_id Callbacks celery_root_id celery_task_id 
# timestamp parent_id tr_id Callback A
# timestamp parent_id tr_id Callback B

# example if we run each callback in a separate celery task:
# -------------------------------------------
# timestamp parent_id tr_id Callback A celery_root_id celery_task_id
# timestamp parent_id tr_id Callback B celery_root_id celery_task_id

# The same for side effects and failure callbacks

#############################################################
# Nested transitions
# One transition can be invoked inside another transition in side effects or callbacks.

# example (side effect A invokes transition B):
# timestamp parent_a_id tr_a_id Start ProcessName TransitionName instance_key   - parent_a_id == tr_a_id
# timestamp parent_a_id tr_b_id Start ProcessName TransitionName instance_key
# timestamp parent_b_id tr_c_id Start ProcessName TransitionName instance_key   - parent_b_id == tr_b_id
# timestamp parent_b_id tr_c_id Done
# timestamp parent_a_id tr_b_id Done
# timestamp parent_a_id tr_a_id Done

# NOTE: OpenTelemetry integration ?
