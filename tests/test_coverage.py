import uuid
from abc import ABC
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from django_logic import Process, Transition, Action
from django_logic.commands import BaseCommand, FailureSideEffects, NextTransition, Callbacks
from django_logic.exceptions import TransitionNotAllowed
from django_logic.logger import (
    AbstractLogger, NullLogger, DefaultLogger, get_logger,
)
from django_logic.process import ProcessManager
from django_logic.state import State, RedisState
from django_logic.transition import BaseTransition
from django_logic.utils import (
    restore_user_object, get_process_instance, get_process_and_state, restore_action,
)
from tests.models import Invoice

# TODO: this is test for 100% coverage, move them to correct places 

class CoverageTestProcess(Process):
    process_name = 'coverage_process'
    transitions = [
        Transition('approve', sources=['draft'], target='approved'),
    ]


# --- BaseCommand (line 22) ---

class BaseCommandTestCase(TestCase):
    def test_execute_raises_not_implemented(self):
        cmd = BaseCommand()
        with self.assertRaises(NotImplementedError):
            cmd.execute()


# --- FailureSideEffects exception handling (lines 119-120) ---

class FailureSideEffectsExceptionTestCase(TestCase):
    def setUp(self):
        self.invoice = Invoice.objects.create(status='draft')

    def test_exception_in_failure_side_effect_is_swallowed(self):
        def raise_error(invoice, *args, **kwargs):
            raise ValueError("boom")

        transition = Transition(
            'test', sources=[], target='success', failed_state='failed',
            side_effects=[lambda inv, **kw: (_ for _ in ()).throw(Exception("main"))],
            failure_side_effects=[raise_error],
        )
        state = State(self.invoice, 'status')
        with self.assertRaises(Exception):
            transition.change_state(state)
        self.assertEqual(self.invoice.status, 'failed')


# --- NextTransition (lines 144, 149-152) ---

class NextTransitionTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.invoice = Invoice.objects.create(status=Invoice.STATUS_DRAFT)
        self.state = State(self.invoice, 'status', 'process')

    def test_no_available_next_transition_returns_none(self):
        transition = Transition(
            'test',
            sources=[Invoice.STATUS_DRAFT],
            target=Invoice.STATUS_SUCCESS,
            next_transition='nonexistent_action',
        )

        class TestProcess(Process):
            transitions = [transition]

        process = TestProcess(instance=self.invoice, state=self.state)
        self.invoice.process = process

        transition.change_state(self.state)
        self.assertEqual(self.invoice.status, Invoice.STATUS_SUCCESS)

    def test_next_transition_exception_is_swallowed(self):
        next_tr = Transition(
            'next_step',
            sources=[Invoice.STATUS_SUCCESS],
            target=Invoice.STATUS_CANCELLED,
        )
        transition = Transition(
            'test',
            sources=[Invoice.STATUS_DRAFT],
            target=Invoice.STATUS_SUCCESS,
            next_transition='next_step',
        )

        class TestProcess(Process):
            transitions = [transition, next_tr]

        process = TestProcess(instance=self.invoice, state=self.state)
        self.invoice.process = process

        with patch.object(next_tr, 'change_state', side_effect=RuntimeError("fail")):
            transition.change_state(self.state)

        self.assertEqual(self.invoice.status, Invoice.STATUS_SUCCESS)


# --- Callbacks exception (commands.py line 96-101) ---

class CallbacksExceptionTestCase(TestCase):
    def setUp(self):
        self.invoice = Invoice.objects.create(status='draft')

    def test_callback_exception_is_swallowed(self):
        def bad_callback(invoice, *args, **kwargs):
            raise RuntimeError("callback error")

        transition = Transition(
            'test', sources=[], target='done',
            callbacks=[bad_callback],
        )
        state = State(self.invoice, 'status')
        transition.change_state(state)
        self.assertEqual(self.invoice.status, 'done')


# --- Logger (lines 21, 25, 48, 51, 54, 59, 62-66) ---

class ConcreteLogger(AbstractLogger):
    def info(self, message, **kwargs):
        super().info(message, **kwargs)

    def error(self, exception, **kwargs):
        super().error(exception, **kwargs)


class AbstractLoggerTestCase(TestCase):
    def test_abstract_methods_have_pass_body(self):
        logger = ConcreteLogger()
        logger.info("test message")
        logger.error(Exception("test"))


class NullLoggerTestCase(TestCase):
    def test_null_logger_methods(self):
        logger = NullLogger()
        logger.info("test message", log_type="test")
        logger.error(Exception("test error"), log_type="test")


class GetLoggerTestCase(TestCase):
    @patch('django_logic.logger.DISABLE_LOGGING', True)
    def test_get_logger_returns_null_when_disabled(self):
        result = get_logger()
        self.assertIsInstance(result, NullLogger)

    @patch('django_logic.logger.DISABLE_LOGGING', False)
    @patch('django_logic.logger.CUSTOM_LOGGER', 'django_logic.logger.DefaultLogger')
    def test_get_logger_returns_custom_logger(self):
        result = get_logger(module_name='test')
        self.assertIsInstance(result, DefaultLogger)

    @patch('django_logic.logger.DISABLE_LOGGING', False)
    @patch('django_logic.logger.CUSTOM_LOGGER', 'nonexistent.module.FakeLogger')
    def test_get_logger_raises_on_bad_import(self):
        with self.assertRaises(ImproperlyConfigured):
            get_logger()


# --- Process (lines 50, 106, 143, 216, 226-233, 240-242) ---

class ProcessInitTestCase(TestCase):
    def test_init_with_both_state_and_field_raises(self):
        invoice = Invoice.objects.create(status='draft')
        state = State(invoice, 'status')
        with self.assertRaises(AttributeError):
            Process(field_name='status', instance=invoice, state=state)


class ProcessNonRootTransitionTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def test_non_root_transition_executes(self):
        class TestProcess(Process):
            transitions = [
                Transition('cancel', sources=['draft'], target='cancelled')
            ]

        invoice = Invoice.objects.create(status='draft')
        process = TestProcess(instance=invoice, field_name='status')
        process.cancel(root_id=uuid.uuid4())
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'cancelled')

    def test_non_root_transition_propagates_exception(self):
        def fail(inv, **kw):
            raise RuntimeError("side effect error")

        class TestProcess(Process):
            transitions = [
                Transition('cancel', sources=['draft'], target='cancelled',
                           failed_state='failed', side_effects=[fail])
            ]

        invoice = Invoice.objects.create(status='draft')
        process = TestProcess(instance=invoice, field_name='status')
        with self.assertRaises(RuntimeError):
            process.cancel(root_id=uuid.uuid4())


class ProcessLockedStateTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def test_get_available_transitions_returns_empty_when_locked(self):
        transition = Transition('action', sources=['draft'], target='done')

        class TestProcess(Process):
            transitions = [transition]

        invoice = Invoice.objects.create(status='draft')
        process = TestProcess(instance=invoice, field_name='status')
        process.state.lock()

        result = list(process.get_available_transitions())
        self.assertEqual(result, [])
        process.state.unlock()


class ProcessManagerBindStateFieldsTestCase(TestCase):
    def test_raises_type_error_for_non_process(self):
        with self.assertRaises(TypeError):
            ProcessManager.bind_state_fields(state_field=str)


class ProcessManagerNonStateFieldsTestCase(TestCase):
    def test_non_state_fields_excludes_pk_and_state(self):
        class FakeBase:
            pass

        class TestModel(ProcessManager, FakeBase):
            state_fields = ['status']

        obj = TestModel()
        obj._meta = SimpleNamespace(fields=[
            SimpleNamespace(primary_key=True, name='id', attname='id'),
            SimpleNamespace(primary_key=False, name='status', attname='status'),
            SimpleNamespace(primary_key=False, name='customer', attname='customer_id'),
            SimpleNamespace(primary_key=False, name='is_available', attname='is_available'),
        ])

        result = obj.non_state_fields
        self.assertIn('customer', result)
        self.assertIn('customer_id', result)
        self.assertIn('is_available', result)
        self.assertNotIn('status', result)
        self.assertNotIn('id', result)


class ProcessManagerSaveTestCase(TestCase):
    def _make_model_class(self):
        class FakeBase:
            def save(self, *args, **kwargs):
                self.saved_kwargs = kwargs

        class TestModel(ProcessManager, FakeBase):
            state_fields = ['status']

        return TestModel

    def test_save_adds_update_fields_when_id_present(self):
        cls = self._make_model_class()
        obj = cls()
        obj.id = 1
        non_state = {'field1', 'field2'}

        with patch.object(
            type(obj), 'non_state_fields',
            new_callable=lambda: property(lambda self: non_state),
        ):
            obj.save()

        self.assertEqual(obj.saved_kwargs['update_fields'], non_state)

    def test_save_skips_update_fields_when_no_id(self):
        cls = self._make_model_class()
        obj = cls()
        obj.id = None
        obj.save()
        self.assertNotIn('update_fields', obj.saved_kwargs)

    def test_save_preserves_explicit_update_fields(self):
        cls = self._make_model_class()
        obj = cls()
        obj.id = 1
        obj.save(update_fields=['custom'])
        self.assertEqual(obj.saved_kwargs['update_fields'], ['custom'])


# --- State (line 88) ---

class RedisStateTestCase(TestCase):
    def setUp(self):
        self.invoice = Invoice.objects.create(status='draft')

    @patch('django_logic.state.cache')
    def test_lock_returns_true_on_success(self, mock_cache):
        mock_cache.set.return_value = True
        state = RedisState(self.invoice, 'status')
        self.assertTrue(state.lock())

    @patch('django_logic.state.cache')
    def test_lock_returns_false_when_already_locked(self, mock_cache):
        mock_cache.set.return_value = None
        state = RedisState(self.invoice, 'status')
        self.assertFalse(state.lock())


# --- Transition (lines 25, 28, 31, 34, 83, 86, 152-153, 199, 234-254, 273) ---

class BaseTransitionTestCase(TestCase):
    def test_is_valid_raises(self):
        bt = BaseTransition()
        with self.assertRaises(NotImplementedError):
            bt.is_valid(None)

    def test_change_state_raises(self):
        bt = BaseTransition()
        with self.assertRaises(NotImplementedError):
            bt.change_state(None)

    def test_complete_transition_raises(self):
        bt = BaseTransition()
        with self.assertRaises(NotImplementedError):
            bt.complete_transition(None)

    def test_fail_transition_raises(self):
        bt = BaseTransition()
        with self.assertRaises(NotImplementedError):
            bt.fail_transition(None, None)


class TransitionStrTestCase(TestCase):
    def test_str(self):
        t = Transition('approve', sources=['draft'], target='approved')
        self.assertEqual(str(t), 'Transition: approve to approved')

    def test_repr(self):
        t = Transition('approve', sources=['draft'], target='approved')
        self.assertEqual(repr(t), 'Transition: approve to approved')

    def test_action_str(self):
        a = Action('do_stuff', sources=['draft'])
        self.assertEqual(str(a), 'Action: do_stuff')


class TransitionBackgroundModeTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def test_background_mode_calls_run_in_background(self):
        invoice = Invoice.objects.create(status='draft')
        state = State(invoice, 'status')
        transition = Transition('test', sources=[], target='done')
        tr_id = uuid.uuid4()

        with self.assertRaises(NotImplementedError):
            transition.change_state(
                state, background_mode=True, root_id=tr_id, tr_id=tr_id,
            )

    def test_run_in_background_raises(self):
        invoice = Invoice.objects.create(status='draft')
        state = State(invoice, 'status')
        transition = Transition('test', sources=[], target='done')
        with self.assertRaises(NotImplementedError):
            transition.run_in_background(state)


class TransitionGetTaskKwargsTestCase(TestCase):
    def setUp(self):
        self.invoice = Invoice.objects.create(status='draft')
        self.state = State(self.invoice, 'status', process_name='test_process')
        self.transition = Transition('approve', sources=['draft'], target='approved')

    def test_basic_kwargs(self):
        result = self.transition.get_task_kwargs(self.state, process_class='my.Proc')
        self.assertEqual(result['app_label'], 'tests')
        self.assertEqual(result['model_name'], 'invoice')
        self.assertEqual(result['instance_id'], self.invoice.pk)
        self.assertEqual(result['action_name'], 'approve')
        self.assertEqual(result['target'], 'approved')
        self.assertEqual(result['process_name'], 'test_process')
        self.assertEqual(result['field_name'], 'status')
        self.assertEqual(result['process_class'], 'my.Proc')
        self.assertNotIn('user_id', result)

    def test_with_user_id(self):
        result = self.transition.get_task_kwargs(self.state, user_id=42)
        self.assertEqual(result['user_id'], 42)

    def test_with_user_object(self):
        user = Mock(id=99)
        result = self.transition.get_task_kwargs(self.state, user=user)
        self.assertEqual(result['user_id'], 99)

    def test_with_tr_ids(self):
        tr_id = uuid.uuid4()
        root_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        result = self.transition.get_task_kwargs(
            self.state, tr_id=tr_id, root_id=root_id, parent_id=parent_id,
        )
        self.assertEqual(result['tr_id'], str(tr_id))
        self.assertEqual(result['root_id'], str(root_id))
        self.assertEqual(result['parent_id'], str(parent_id))

    def test_with_none_tr_id(self):
        result = self.transition.get_task_kwargs(self.state, tr_id=None)
        self.assertIsNone(result['tr_id'])


# --- utils.py (lines 1-55) ---

class RestoreUserObjectTestCase(TestCase):
    def test_restores_user_from_id(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user('testuser', 'test@test.com', 'password')
        kwargs = {'user_id': user.id}
        restore_user_object(kwargs)
        self.assertEqual(kwargs['user'], user)

    def test_no_user_id_is_noop(self):
        kwargs = {'other': 'value'}
        restore_user_object(kwargs)
        self.assertNotIn('user', kwargs)


class GetProcessInstanceTestCase(TestCase):
    def test_from_attribute(self):
        invoice = Invoice.objects.create(status='draft')
        process = CoverageTestProcess(field_name='status', instance=invoice)
        invoice.coverage_process = process
        result = get_process_instance(invoice, 'coverage_process')
        self.assertIs(result, process)

    def test_from_process_class_string(self):
        invoice = Invoice.objects.create(status='draft')
        result = get_process_instance(
            invoice, 'nonexistent_attr',
            process_class='tests.test_coverage.CoverageTestProcess',
            field_name='status',
        )
        self.assertIsInstance(result, CoverageTestProcess)

    def test_raises_when_no_attr_and_no_class(self):
        invoice = Invoice.objects.create(status='draft')
        with self.assertRaises(AttributeError) as ctx:
            get_process_instance(invoice, 'nonexistent_attr')
        self.assertIn('Invoice', str(ctx.exception))
        self.assertIn('nonexistent_attr', str(ctx.exception))


class GetProcessAndStateTestCase(TestCase):
    def test_returns_process_and_state(self):
        invoice = Invoice.objects.create(status='draft')
        process, state = get_process_and_state(
            'tests', 'invoice', invoice.pk, 'coverage_process',
            process_class='tests.test_coverage.CoverageTestProcess',
            field_name='status',
        )
        self.assertIsInstance(process, CoverageTestProcess)
        self.assertIsNotNone(state)
        self.assertEqual(state.instance.pk, invoice.pk)


class RestoreActionTestCase(TestCase):
    def test_restores_process_and_transition(self):
        invoice = Invoice.objects.create(status='draft')
        process, transition = restore_action(
            app_label='tests',
            model_name='invoice',
            instance_id=invoice.pk,
            field_name='status',
            process_class='tests.test_coverage.CoverageTestProcess',
            action_name='approve',
            user=None,
        )
        self.assertIsInstance(process, CoverageTestProcess)
        self.assertEqual(transition.action_name, 'approve')
