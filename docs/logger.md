# Django-Logic Logging

## Loggers

The library provides two loggers:

- **`logger`**: Main logger for logging all activity of django-logic (`django-logic`)
- **`transition_logger`**: Special logger for logging only activity of transitions (`django-logic.transition`)

### Transition Log Format
```
timestamp root_id parent_id tr_id <event_type> ...args
```

### Basic Transition Log Example

```
timestamp root_id parent_id tr_id Start ProcessName TransitionName instance_key     - first is declaration of the transition
timestamp root_id parent_id tr_id Celery celery_task id celery_root_id              - if run into celery add more logs about it
timestamp root_id parent_id tr_id Lock
timestamp root_id parent_id tr_id SideEffect A                                      - side effect is started
timestamp root_id parent_id tr_id SideEffect B                                      - new side effect means the previous one was completed
timestamp root_id parent_id tr_id UnLock
timestamp root_id parent_id tr_id Callback A                                        - a callback is started
timestamp root_id parent_id tr_id Callback B                                        - new callback means the previous one was completed
timestamp root_id parent_id tr_id Done                                              - transition is completed
```

## Celery Integration

Callbacks can be executed in a celery task. Moreover, each callback can be executed in its own celery task. Only `celery_root_id` can connect all the callbacks together.

### Example: All callbacks in a single celery task

```
timestamp root_id parent_id tr_id CeleryCallbacks celery_root_id celery_task_id 
timestamp root_id parent_id tr_id Callback A
timestamp root_id parent_id tr_id Callback B
```

### Example: Each callback in a separate celery task

```
timestamp root_id parent_id tr_id Callback A celery_root_id celery_task_id
timestamp root_id parent_id tr_id Callback B celery_root_id celery_task_id
```

**Note**: The same pattern applies for side effects and failure callbacks.

## Nested Transitions

One transition can be invoked inside another transition in side effects or callbacks.

### Example: Side effect A invokes transition B

```
timestamp root_id parent_a_id tr_a_id Start ProcessName TransitionName instance_key   - parent_a_id == tr_a_id
timestamp root_id parent_a_id tr_b_id Start ProcessName TransitionName instance_key
timestamp root_id parent_b_id tr_c_id Start ProcessName TransitionName instance_key   - parent_b_id == tr_b_id
timestamp root_id parent_b_id tr_c_id Done
timestamp root_id parent_a_id tr_b_id Done
timestamp root_id parent_a_id tr_a_id Done
```

## Future Considerations

**Note**: OpenTelemetry integration is under consideration.

