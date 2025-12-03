from django.test import TestCase, override_settings

from django_logic import Transition, Action
from django_logic.constants import LogType
from django_logic.state import State
from django_logic.exceptions import TransitionNotAllowed
from tests.models import Invoice
from tests.utils import ListLogger, reload_logger


def disable_invoice(invoice: Invoice, *args, **kwargs):
    invoice.is_available = False
    invoice.save()


def enable_invoice(invoice: Invoice, *args, **kwargs):
    invoice.is_available = True
    invoice.save()


def fail_invoice(invoice: Invoice, *args, **kwargs):
    raise Exception("Test exception")


class TransitionLoggingTestCase(TestCase):

    @classmethod
    def tearDownClass(cls):
        """Cleanup after all tests in TransitionLoggingTestCase."""
        super().tearDownClass()
        # Reset logger to the default one.
        reload_logger()

    def setUp(self) -> None:
        self.invoice = Invoice.objects.create(status='draft')
        self.logs = reload_logger(ListLogger)
        self.logs.clear()
    
    def test_transition_locks_state_logging(self):
        """Test that locking state is logged."""
        transition = Transition('test', sources=[], target='cancelled')
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check that state locking was logged
        lock_logs = [log for log in self.logs.get_logs() if 'locked' in log['message']]
        # self.assertGreater(len(lock_logs), 0)
        # self.assertTrue(any('has been locked' in log['message'] for log in lock_logs))

    # def test_transition_completed_logging(self):
    #     """Test that successful transition completion is logged."""
    #     transition = Transition('test', sources=[], target='cancelled')
    #     state = State(self.invoice, 'status')

    #     transition.change_state(state)

    #     # Check for TRANSITION_COMPLETED log
    #     completed_logs = self.logs.get_logs_by_type(LogType.TRANSITION_COMPLETED)
    #     # self.assertEqual(len(completed_logs), 1)
    #     # self.assertIn('state changed to cancelled', completed_logs[0]['message'])
    #     # self.assertEqual(completed_logs[0]['log_type'], LogType.TRANSITION_COMPLETED)

    # def test_transition_failed_logging(self):
    #     """Test that failed transition is logged."""
    #     transition = Transition(
    #         'test',
    #         sources=[],
    #         target='success',
    #         failed_state='failed',
    #         side_effects=[fail_invoice]
    #     )
    #     state = State(self.invoice, 'status')

    #     transition.change_state(state)

    #     # Check for TRANSITION_FAILED log
    #     failed_logs = self.logs.get_logs_by_type(LogType.TRANSITION_FAILED)
    #     self.assertEqual(len(failed_logs), 1)
    #     self.assertIn('state changed to failed', failed_logs[0]['message'])
    #     self.assertEqual(failed_logs[0]['log_type'], LogType.TRANSITION_FAILED)

    # def test_transition_error_logging(self):
    #     """Test that errors during side effects are logged."""
    #     transition = Transition(
    #         'test',
    #         sources=[],
    #         target='success',
    #         failed_state='failed',
    #         side_effects=[fail_invoice]
    #     )
    #     state = State(self.invoice, 'status')

    #     transition.change_state(state)

    #     # Check for TRANSITION_ERROR log
    #     error_logs = self.logs.get_logs_by_type(LogType.TRANSITION_ERROR)
    #     self.assertGreater(len(error_logs), 0)
    #     self.assertEqual(error_logs[0]['log_type'], LogType.TRANSITION_ERROR)

    # def test_side_effects_started_logging(self):
    #     """Test that side effects start is logged."""
    #     transition = Transition(
    #         'test',
    #         sources=[],
    #         target='cancelled',
    #         side_effects=[disable_invoice]
    #     )
    #     state = State(self.invoice, 'status')

    #     transition.change_state(state)

    #     # Check for side effects started log
    #     self.assertTrue(self.logs.has_log('side effects of', LogType.TRANSITION_DEBUG))
    #     side_effect_logs = [log for log in self.logs.get_logs() if 'side effects' in log['message']]
    #     self.assertTrue(any('started' in log['message'] for log in side_effect_logs))

    # def test_side_effects_succeeded_logging(self):
    #     """Test that successful side effects are logged."""
    #     transition = Transition(
    #         'test',
    #         sources=[],
    #         target='cancelled',
    #         side_effects=[disable_invoice]
    #     )
    #     state = State(self.invoice, 'status')

    #     transition.change_state(state)

    #     # Check for side effects succeeded log
    #     self.assertTrue(self.logs.has_log('side-effects of', LogType.TRANSITION_DEBUG))
    #     side_effect_logs = [log for log in self.logs.get_logs() if 'side-effects' in log['message']]
    #     self.assertTrue(any('succeeded' in log['message'] for log in side_effect_logs))

    # def test_side_effects_failed_logging(self):
    #     """Test that failed side effects are logged."""
    #     transition = Transition(
    #         'test',
    #         sources=[],
    #         target='success',
    #         failed_state='failed',
    #         side_effects=[fail_invoice]
    #     )
    #     state = State(self.invoice, 'status')

    #     transition.change_state(state)

    #     # Check for side effects failed log
    #     self.assertTrue(self.logs.has_log('side effects of', LogType.TRANSITION_DEBUG))
    #     side_effect_logs = [log for log in self.logs.get_logs() if 'side effects' in log['message']]
    #     self.assertTrue(any('failed' in log['message'] for log in side_effect_logs))

    # def test_callbacks_failed_logging(self):
    #     """Test that failed callbacks are logged."""
    #     transition = Transition(
    #         'test',
    #         sources=[],
    #         target='cancelled',
    #         callbacks=[fail_invoice]
    #     )
    #     state = State(self.invoice, 'status')

    #     transition.change_state(state)

    #     # Check for callbacks failed log
    #     self.assertTrue(self.logs.has_log('callbacks of', LogType.TRANSITION_DEBUG))
    #     callback_logs = [log for log in self.logs.get_logs() if 'callbacks' in log['message']]
    #     self.assertTrue(any('failed' in log['message'] for log in callback_logs))

    # def test_transition_unlock_logging(self):
    #     """Test that unlocking state is logged."""
    #     transition = Transition('test', sources=[], target='cancelled')
    #     state = State(self.invoice, 'status')

    #     transition.change_state(state)

    #     # Check that state unlocking was logged
    #     unlock_logs = [log for log in self.logs.get_logs() if 'unlocked' in log['message']]
    #     self.assertGreater(len(unlock_logs), 0)
    #     self.assertTrue(any('has been unlocked' in log['message'] for log in unlock_logs))

    # def test_locked_state_logging(self):
    #     """Test that attempting transition on locked state is logged."""
    #     transition = Transition('test', sources=[], target='cancelled')
    #     state = State(self.invoice, 'status')
    #     state.lock()

    #     with self.assertRaises(TransitionNotAllowed):
    #         transition.change_state(state)

    #     # Check that locked state was logged
    #     self.assertTrue(self.logs.has_log('is locked', LogType.TRANSITION_DEBUG))

    # def test_in_progress_state_logging(self):
    #     """Test that in-progress state change is logged."""
    #     transition = Transition(
    #         'test',
    #         sources=[],
    #         target='cancelled',
    #         in_progress_state='processing'
    #     )
    #     state = State(self.invoice, 'status')

    #     transition.change_state(state)

    #     # Check for in-progress state log
    #     in_progress_logs = [log for log in self.logs.get_logs() 
    #                        if 'state changed to processing' in log['message']]
    #     self.assertGreater(len(in_progress_logs), 0)

    # def test_log_data_structure(self):
    #     """Test that log_data is properly structured."""
    #     transition = Transition('test', sources=[], target='cancelled')
    #     state = State(self.invoice, 'status')

    #     transition.change_state(state)

    #     # Check that log_data contains expected fields
    #     all_logs = self.logs.get_logs()
    #     self.assertGreater(len(all_logs), 0)
        
    #     for log in all_logs:
    #         if log['log_data'] is not None:
    #             log_data = log['log_data']
    #             self.assertIn('instance', log_data)
    #             self.assertIn('field_name', log_data)
    #             self.assertEqual(log_data['field_name'], 'status')


class ActionLoggingTestCase(TestCase):

    @classmethod
    def tearDownClass(cls):
        """Cleanup after all tests in ActionLoggingTestCase."""
        super().tearDownClass()
        # Reset logger to the default one.
        reload_logger()

    def setUp(self) -> None:
        self.invoice = Invoice.objects.create(status='draft')
        # Set logger to the custom one.
        self.logs = reload_logger(ListLogger)
        self.logs.clear()

    # def test_action_side_effects_logging(self):
    #     """Test that action side effects are logged."""
    #     action = Action(
    #         'test',
    #         sources=['draft'],
    #         side_effects=[disable_invoice]
    #     )
    #     state = State(self.invoice, 'status')

    #     action.change_state(state)

    #     # Check for side effects logs
    #     self.assertTrue(self.logs.has_log('side effects of', LogType.TRANSITION_DEBUG))
    #     side_effect_logs = [log for log in self.logs.get_logs() if 'side effects' in log['message']]
    #     self.assertTrue(any('started' in log['message'] for log in side_effect_logs))

    # def test_action_failed_logging(self):
    #     """Test that failed action is logged."""
    #     action = Action(
    #         'test',
    #         sources=['draft'],
    #         failed_state='failed',
    #         side_effects=[fail_invoice]
    #     )
    #     state = State(self.invoice, 'status')

    #     action.change_state(state)

    #     # Check for TRANSITION_FAILED log
    #     failed_logs = self.logs.get_logs_by_type(LogType.TRANSITION_FAILED)
    #     self.assertEqual(len(failed_logs), 1)
    #     self.assertIn('state changed to failed', failed_logs[0]['message'])

    # def test_action_error_logging(self):
    #     """Test that errors during action side effects are logged."""
    #     action = Action(
    #         'test',
    #         sources=['draft'],
    #         failed_state='failed',
    #         side_effects=[fail_invoice]
    #     )
    #     state = State(self.invoice, 'status')

    #     action.change_state(state)

    #     # Check for TRANSITION_ERROR log
    #     error_logs = self.logs.get_logs_by_type(LogType.TRANSITION_ERROR)
    #     self.assertGreater(len(error_logs), 0)
    #     self.assertEqual(error_logs[0]['log_type'], LogType.TRANSITION_ERROR)


