import time
from types import SimpleNamespace
from unittest.mock import Mock
from PySide6.QtCore import QThread
from PySide6.QtTest import QSignalSpy
from windows.translate_dialog import BatchTranslateWorker, TranslateDialog, split_by_char_limit
from singletons.config import config
from singletons.state import app_state
from singletons.translator import Response
from utils.constants import FLAG_UNVALIDATED, FLAG_VALIDATED


def pump(qapp, condition):
    deadline = time.monotonic() + 3
    while not condition() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(.001)
    assert condition()


def test_oversized_first_chunk():
    item = SimpleNamespace(source='x' * 20000)
    assert split_by_char_limit([item], 16000) == [[item]]
    items = [SimpleNamespace(source='a') for _ in range(51)]
    assert [len(chunk) for chunk in split_by_char_limit(items, 16000)] == [50,1]


def test_worker_always_finishes(qapp, monkeypatch):
    from windows import translate_dialog as module
    monkeypatch.setattr(module.translator, 'translate_many', Mock(side_effect=RuntimeError('failure')))
    item = SimpleNamespace(source='Hello')
    worker = BatchTranslateWorker(item, 'DeepL')
    spy = QSignalSpy(worker.signals.finished)
    worker.run()
    assert spy.count() == 1


def test_batch_failure_preserves_completed_progress(qapp, monkeypatch, tmp_path):
    from windows import translate_dialog as module
    from utils.recovery import RecoveryStore
    monkeypatch.setattr(module, 'recovery', RecoveryStore(tmp_path))
    monkeypatch.setattr(config, 'value', lambda section, option: {
        ('api','deepl_key'): 'fake:fx', ('translation','source'):'ENG_US',
        ('translation','destination'):'POR_BR', ('interface','theme'):'light'}.get((section,option)))
    records = [SimpleNamespace(source='hello', translate='original', flag=FLAG_UNVALIDATED,
                              id=n, resource=SimpleNamespace(group=0,instance=1), package='test') for n in range(3)]
    monkeypatch.setattr(app_state, 'packages_storage', SimpleNamespace(items=lambda: records))
    monkeypatch.setattr(app_state, 'tableview', SimpleNamespace(refresh=lambda:None))
    wraps = []
    monkeypatch.setattr(module.undo, 'wrap', lambda item: wraps.append(QThread.currentThread()))
    monkeypatch.setattr(module.undo, 'commit', lambda: None)
    responses = iter([Response(200, ['Olá']), Response(456, 'Quota exceeded')])
    monkeypatch.setattr(module.translator, 'translate_many', lambda *args: next(responses))
    dialog = TranslateDialog(); dialog.cb_api.addItem('DeepL'); dialog.cb_api.setCurrentText('DeepL')
    dialog.rb_all.setChecked(True); dialog.rb_slow.setChecked(True)
    dialog.translate()
    pump(qapp, lambda: not dialog._TranslateDialog__translating)
    assert records[0].translate == 'Olá' and records[0].flag == FLAG_VALIDATED
    assert [r.translate for r in records[1:]] == ['original','original']
    assert wraps == [qapp.thread()]
    assert len(module.recovery.load('test','ENG_US','POR_BR')) == 1
    assert dialog.btn_translate.isEnabled()
    dialog.close()


def test_cancel_during_retry_keeps_ui_responsive(qapp, monkeypatch):
    from threading import Event
    from windows import translate_dialog as module
    entered = Event()
    def wait_for_cancel(texts, cancel):
        entered.set()
        cancel.wait(2)
        return Response(499, 'Cancelled')
    monkeypatch.setattr(module.translator, 'translate_many', wait_for_cancel)
    records = [SimpleNamespace(source='hello')]
    monkeypatch.setattr(app_state, 'packages_storage', SimpleNamespace(items=lambda: records))
    monkeypatch.setattr(app_state, 'tableview', SimpleNamespace(refresh=lambda:None))
    dialog = TranslateDialog(); dialog.cb_api.addItem('DeepL'); dialog.cb_api.setCurrentText('DeepL')
    dialog.rb_all.setChecked(True)
    dialog.translate()
    pump(qapp, entered.is_set)
    start = time.monotonic(); dialog.stop_translate()
    assert time.monotonic() - start < .1
    pump(qapp, lambda:not dialog._TranslateDialog__translating)
    dialog.close()


def test_application_import_and_window(qapp, monkeypatch):
    from storages.packages import PackagesStorage
    from storages.dictionaries import DictionariesStorage
    from windows.main_window import MainWindow
    monkeypatch.setattr(app_state, 'packages_storage', PackagesStorage())
    monkeypatch.setattr(app_state, 'dictionaries_storage', DictionariesStorage())
    window = MainWindow()
    assert window.windowTitle().startswith('The Sims 4 Translator')
    window.close()


def test_real_main_record_is_single_translation_item(qapp, monkeypatch):
    from storages.records import MainRecord
    from windows import translate_dialog as module
    from utils.constants import RECORD_MAIN_SOURCE
    # MainRecord inherits list; it must not be mistaken for a batch of records.
    record = MainRecord(*([None] * 14))
    record[RECORD_MAIN_SOURCE] = 'hello'
    request = Mock(return_value=Response(200, ['Olá']))
    monkeypatch.setattr(module.translator, 'translate_many', request)
    worker = BatchTranslateWorker(record, 'DeepL')
    results = []
    worker.signals.result.connect(results.append)
    worker.run()
    request.assert_called_once_with(['hello'], None)
    assert results == [[(record, 'Olá')]]
