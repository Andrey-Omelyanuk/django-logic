from django.test import TestCase
from django.core.cache import cache
from django_logic import Transition, Action
from django_logic.state import State
from django_logic.exceptions import TransitionNotAllowed
from tests.models import Invoice
from tests.utils import get_test_logger


def disable_invoice(invoice: Invoice, *args, **kwargs):
    invoice.is_available = False
    invoice.save()


def enable_invoice(invoice: Invoice, *args, **kwargs):
    invoice.is_available = True
    invoice.save()


def fail_invoice(invoice: Invoice, *args, **kwargs):
    raise Exception("Test exception")


class TransitionLoggingTestCase(TestCase):

    def setUp(self) -> None:
        cache.clear()
        self.invoice = Invoice.objects.create(status='draft')
        self.logs = get_test_logger()
        self.logs.clear()
    
    def test_transition_locks_state_logging(self):
        """Test that locking state is logged."""
        transition = Transition('test', sources=[], target='cancelled')
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check that state locking was logged
        lock_logs = [log for log in self.logs.get_logs() if log.get('activity') == 'Lock']
        self.assertGreater(len(lock_logs), 0)
        self.assertTrue(any('Lock' in log['message'] for log in lock_logs))

    def test_transition_completed_logging(self):
        """Test that successful transition completion is logged."""
        transition = Transition('test', sources=[], target='cancelled')
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check for Set State log (state changed to cancelled)
        completed_logs = [log for log in self.logs.get_logs() 
                         if log.get('activity') == 'Set State' and log.get('state') == 'cancelled']
        self.assertEqual(len(completed_logs), 1)
        self.assertIn('Set State', completed_logs[0]['message'])
        self.assertEqual(completed_logs[0]['state'], 'cancelled')

    def test_transition_failed_logging(self):
        """Test that failed transition is logged."""
        transition = Transition(
            'test',
            sources=[],
            target='success',
            failed_state='failed',
            side_effects=[fail_invoice]
        )
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check for Set State log (state changed to failed)
        failed_logs = [log for log in self.logs.get_logs() 
                      if log.get('activity') == 'Set State' and log.get('state') == 'failed']
        self.assertEqual(len(failed_logs), 1)
        self.assertIn('Set State', failed_logs[0]['message'])
        self.assertEqual(failed_logs[0]['state'], 'failed')

    def test_transition_error_logging(self):
        """Test that errors during side effects are logged."""
        transition = Transition(
            'test',
            sources=[],
            target='success',
            failed_state='failed',
            side_effects=[fail_invoice]
        )
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check for error logs (level should be ERROR)
        error_logs = [log for log in self.logs.get_logs() if log.get('level') == 'ERROR']
        self.assertGreater(len(error_logs), 0)
        self.assertEqual(error_logs[0]['level'], 'ERROR')

    def test_side_effects_started_logging(self):
        """Test that side effects start is logged."""
        transition = Transition(
            'test',
            sources=[],
            target='cancelled',
            side_effects=[disable_invoice]
        )
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check for side effects started log
        self.assertTrue(self.logs.has_log('SideEffect'))
        side_effect_logs = [log for log in self.logs.get_logs() 
                           if log.get('activity') == 'SideEffect']
        self.assertGreater(len(side_effect_logs), 0)
        self.assertTrue(any('SideEffect' in log['message'] for log in side_effect_logs))

    def test_side_effects_succeeded_logging(self):
        """Test that successful side effects are logged."""
        transition = Transition(
            'test',
            sources=[],
            target='cancelled',
            side_effects=[disable_invoice]
        )
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check for side effects succeeded log (SideEffect activity should be present)
        self.assertTrue(self.logs.has_log('SideEffect'))
        side_effect_logs = [log for log in self.logs.get_logs() 
                           if log.get('activity') == 'SideEffect']
        self.assertGreater(len(side_effect_logs), 0)
        self.assertTrue(any('SideEffect' in log['message'] for log in side_effect_logs))

    def test_side_effects_failed_logging(self):
        """Test that failed side effects are logged."""
        transition = Transition(
            'test',
            sources=[],
            target='success',
            failed_state='failed',
            side_effects=[fail_invoice]
        )
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check for side effects failed log (should have SideEffect activity and error)
        self.assertTrue(self.logs.has_log('SideEffect'))
        side_effect_logs = [log for log in self.logs.get_logs() 
                           if log.get('activity') == 'SideEffect']
        self.assertGreater(len(side_effect_logs), 0)
        # Should also have error logs
        error_logs = [log for log in self.logs.get_logs() if log.get('level') == 'ERROR']
        self.assertGreater(len(error_logs), 0)

    def test_callbacks_failed_logging(self):
        """Test that failed callbacks are logged."""
        transition = Transition(
            'test',
            sources=[],
            target='cancelled',
            callbacks=[fail_invoice]
        )
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check for callbacks failed log
        self.assertTrue(self.logs.has_log('callbacks'))
        callback_logs = [log for log in self.logs.get_logs() if 'callbacks' in log['message']]
        self.assertTrue(any('failed' in log['message'] for log in callback_logs))
        # Should also have error logs
        error_logs = [log for log in self.logs.get_logs() if log.get('level') == 'ERROR']
        self.assertGreater(len(error_logs), 0)

    def test_transition_unlock_logging(self):
        """Test that unlocking state is logged."""
        transition = Transition('test', sources=[], target='cancelled')
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check that state unlocking was logged
        unlock_logs = [log for log in self.logs.get_logs() if log.get('activity') == 'Unlock']
        self.assertGreater(len(unlock_logs), 0)
        self.assertTrue(any('Unlock' in log['message'] for log in unlock_logs))

    def test_locked_state_logging(self):
        """Test that attempting transition on locked state is logged."""
        transition = Transition('test', sources=[], target='cancelled')
        state = State(self.invoice, 'status')
        state.lock()

        with self.assertRaises(TransitionNotAllowed):
            transition.change_state(state)

        # Check that locked state was logged (should have error log)
        error_logs = [log for log in self.logs.get_logs() if log.get('level') == 'ERROR']
        self.assertGreater(len(error_logs), 0)
        self.assertTrue(any('locked' in log['message'].lower() or 'Locked' in log['message'] 
                           for log in error_logs))

    def test_in_progress_state_logging(self):
        """Test that in-progress state change is logged."""
        transition = Transition(
            'test',
            sources=[],
            target='cancelled',
            in_progress_state='processing'
        )
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check for in-progress state log
        in_progress_logs = [log for log in self.logs.get_logs() 
                           if log.get('activity') == 'Set State' and log.get('state') == 'processing']
        self.assertGreater(len(in_progress_logs), 0)
        self.assertIn('Set State', in_progress_logs[0]['message'])
        self.assertEqual(in_progress_logs[0]['state'], 'processing')

    def test_log_data_structure(self):
        """Test that log data is properly structured."""
        transition = Transition('test', sources=[], target='cancelled')
        state = State(self.invoice, 'status')

        transition.change_state(state)

        # Check that log entries contain expected fields
        all_logs = self.logs.get_logs()
        self.assertGreater(len(all_logs), 0)
        
        # Check that Start activity log has expected fields
        start_logs = [log for log in all_logs if log.get('activity') == 'Start']
        self.assertGreater(len(start_logs), 0)
        start_log = start_logs[0]
        self.assertIn('field_name', start_log)
        self.assertEqual(start_log['field_name'], 'status')
        self.assertIn('instance_pk', start_log)
        self.assertIn('transition', start_log)


class ActionLoggingTestCase(TestCase):

    def setUp(self) -> None:
        cache.clear()
        self.invoice = Invoice.objects.create(status='draft')
        self.logs = get_test_logger()
        self.logs.clear()

    def test_action_side_effects_logging(self):
        """Test that action side effects are logged."""
        action = Action(
            'test',
            sources=['draft'],
            side_effects=[disable_invoice]
        )
        state = State(self.invoice, 'status')

        action.change_state(state)

        # Check for side effects logs
        self.assertTrue(self.logs.has_log('SideEffect'))
        side_effect_logs = [log for log in self.logs.get_logs() 
                           if log.get('activity') == 'SideEffect']
        self.assertGreater(len(side_effect_logs), 0)
        self.assertTrue(any('SideEffect' in log['message'] for log in side_effect_logs))

    def test_action_failed_logging(self):
        """Test that failed action is logged."""
        action = Action(
            'test',
            sources=['draft'],
            failed_state='failed',
            side_effects=[fail_invoice]
        )
        state = State(self.invoice, 'status')

        action.change_state(state)

        # Check for Set State log (state changed to failed)
        failed_logs = [log for log in self.logs.get_logs() 
                      if log.get('activity') == 'Set State' and log.get('state') == 'failed']
        self.assertEqual(len(failed_logs), 1)
        self.assertIn('Set State', failed_logs[0]['message'])
        self.assertEqual(failed_logs[0]['state'], 'failed')

    def test_action_error_logging(self):
        """Test that errors during action side effects are logged."""
        action = Action(
            'test',
            sources=['draft'],
            failed_state='failed',
            side_effects=[fail_invoice]
        )
        state = State(self.invoice, 'status')

        action.change_state(state)

        # Check for error logs (level should be ERROR)
        error_logs = [log for log in self.logs.get_logs() if log.get('level') == 'ERROR']
        self.assertGreater(len(error_logs), 0)
        self.assertEqual(error_logs[0]['level'], 'ERROR')


