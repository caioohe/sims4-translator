# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt, QObject, QThreadPool, QRunnable, Signal, Slot, QTimer
from PySide6.QtWidgets import QDialog
from typing import Union, List
from threading import Event
import html
from utils.recovery import recovery

from windows.ui.translate_dialog import Ui_TranslateDialog

from storages.records import MainRecord

import themes.light as light
import themes.dark as dark

from singletons.config import config
from singletons.interface import interface
from singletons.signals import progress_signals, color_signals
from singletons.state import app_state
from singletons.translator import translator
from singletons.undo import undo
from utils.functions import text_to_stbl, text_to_edit
from utils.constants import *


def split_by_char_limit(items: List[MainRecord], char_limit: int = 256) -> list:
    result = []
    current_chunk = []
    current_length = 0

    for item in items:
        text_length = len(item.source)
        if current_length + text_length > char_limit or len(current_chunk) >= 50:
            if current_chunk:
                result.append(current_chunk)
            current_chunk = [item]
            current_length = text_length
        else:
            current_chunk.append(item)
            current_length += text_length

    if current_chunk:
        result.append(current_chunk)

    return result


class TranslateSignals(QObject):
    finished = Signal()
    result = Signal(object)
    warning = Signal(str)
    error = Signal(str)


class BatchTranslateWorker(QRunnable):

    def __init__(self, chunk, engine, cancel=None):
        super().__init__()
        self.chunk = chunk if isinstance(chunk, list) else [chunk]
        self.engine = engine
        self.cancel = cancel
        self.signals = TranslateSignals()

    def run(self):
        try:
            texts = [text_to_edit(item.source) for item in self.chunk]
            if self.engine.lower() == 'deepl':
                response = translator.translate_many(texts, self.cancel)
                values = response.text
            else:
                response = translator.translate(self.engine, texts[0], self.cancel)
                values = [response.text]
            if response.status_code == 200:
                self.signals.result.emit(list(zip(self.chunk, values)))
            elif response.status_code != 499:
                self.signals.error.emit(response.text)
        except Exception:
            self.signals.error.emit('Unexpected translation failure; original strings retained.')
        finally:
            self.signals.finished.emit()


class TranslateDialog(QDialog, Ui_TranslateDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.cb_api.currentTextChanged.connect(self.change_api)

        self.btn_translate.clicked.connect(self.translate_click)
        self.btn_cancel.clicked.connect(self.cancel_click)

        self.__pool = QThreadPool(self)
        self.__pool.setMaxThreadCount(1)
        self.__cancel = Event()
        self.__pending = []
        self.__closing = False
        self.__worker = None

        self.__progress = 0
        self.__translating = False
        self.__error = False
        self.__log = []

        self.check_api()

        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(interface.text('TranslateDialog', 'Batch translate'))
        self.rb_all.setText(interface.text('ImportDialog', 'Everything'))
        self.rb_validated.setText(interface.text('ImportDialog', 'Everything but already validated strings'))
        self.rb_validated_partial.setText(interface.text('ImportDialog',
                                                         'Everything but already validated and partial strings'))
        self.rb_partial.setText(interface.text('ImportDialog', 'Partial strings'))
        self.rb_selection.setText(interface.text('ImportDialog', 'Selection only'))
        self.btn_cancel.setText(interface.text('TranslateDialog', 'Cancel'))
        self.btn_translate.setText(interface.text('TranslateDialog', 'Translate'))
        self.rb_slow.setText(interface.text('TranslateDialog', 'Line-by-line translation'))
        self.rb_fast.setText(interface.text('TranslateDialog', 'Multiline translation'))
        self.lbl_slow.setText(interface.text('TranslateDialog', 'Slow but more accurate translation.'))
        self.lbl_fast.setText(interface.text('TranslateDialog', 'A faster, but perhaps less accurate translation.'))
        self.log_box.setTitle(interface.text('TranslateDialog', 'Log'))

    def showEvent(self, event):
        engine = config.value('api', 'engine')
        self.cb_api.clear()
        self.cb_api.addItems(translator.engines)
        engine_index = self.cb_api.findText(engine)
        self.cb_api.setCurrentIndex(engine_index if engine_index >= 0 else 0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def change_api(self):
        config.set_value('api', 'engine', self.cb_api.currentText())
        self.check_api()

    def check_api(self):
        api = self.cb_api.currentText().lower()
        if api == 'deepl':
            self.rb_fast.setEnabled(True)
        else:
            self.rb_fast.setEnabled(False)
            self.rb_slow.setChecked(True)

    def translate(self):
        progress_signals.initiate.emit(interface.text('System', 'Translating...'), 0)

        if self.rb_selection.isChecked():
            items = app_state.tableview.selected_items()
        else:
            items = app_state.packages_storage.items()
            if self.rb_validated.isChecked():
                items = [i for i in items if i.flag in (FLAG_UNVALIDATED, FLAG_PROGRESS, FLAG_REPLACED)]
            elif self.rb_validated_partial.isChecked():
                items = [i for i in items if i.flag == FLAG_UNVALIDATED]
            elif self.rb_partial.isChecked():
                items = [i for i in items if i.flag in (FLAG_PROGRESS, FLAG_REPLACED)]

        if not items:
            progress_signals.finished.emit()
            return

        self.btn_translate.setText(interface.text('TranslateDialog', 'Stop translate'))

        if self.rb_fast.isChecked():
            chunk_items = split_by_char_limit(items, 16000)
        else:
            chunk_items = items

        self.__closing = False
        self.__progress = len(chunk_items)
        self.__translating = True
        self.__error = False
        self.__log = []

        self.edt_log.clear()

        progress_signals.initiate.emit(interface.text('System', 'Translating...'), self.__progress)

        self.__cancel.clear()
        self.__pending = list(chunk_items)
        self.cb_api.setEnabled(False)
        self.__start_next()

    def __start_next(self):
        if self.__pending and not self.__cancel.is_set():
            chunk = self.__pending.pop(0)
            worker = BatchTranslateWorker(chunk, self.cb_api.currentText(), self.__cancel)
            self.__worker = worker
            worker.signals.result.connect(self.__apply_results)
            worker.signals.error.connect(self.__error_translate_chunk)
            worker.signals.finished.connect(self.__finished_translate_chunk)
            self.__pool.start(worker)
        else:
            self.__finish_translation()

    @Slot(object)
    def __apply_results(self, results):
        # All records, undo state and model notifications are modified on the UI thread.
        for item, value in results:
            undo.wrap(item)
            item.translate = text_to_stbl(value)
            item.flag = FLAG_VALIDATED
        undo.commit()
        try:
            recovery.save([item for item, _ in results], config.value('translation', 'source'),
                          config.value('translation', 'destination'))
        except OSError:
            self.__error_translate_chunk('Could not save recovery checkpoint. Completed strings remain in memory; save your dictionary before closing.')

    def stop_translate(self):
        self.__cancel.set()
        self.__pending.clear()
        self.btn_translate.setEnabled(False)
        # The current HTTP request finishes within its timeout; never wait on the UI thread.

    def closeEvent(self, event):
        if self.__translating:
            self.__closing = True
            self.stop_translate()
            event.ignore()
        else:
            super().closeEvent(event)

    @Slot()
    def __finished_translate_chunk(self):
        self.__progress -= 1
        app_state.tableview.refresh()
        progress_signals.increment.emit()
        if self.__pending and not self.__cancel.is_set():
            QTimer.singleShot(0, self.__start_next)
            return
        self.__finish_translation()

    def __finish_translation(self):
        self.__progress = 0
        self.__translating = False
        self.__worker = None
        self.btn_translate.setText(interface.text('TranslateDialog', 'Translate'))
        self.btn_translate.setEnabled(True)
        self.cb_api.setEnabled(True)
        color_signals.update.emit()
        progress_signals.finished.emit()
        if self.__closing:
            QTimer.singleShot(0, self.close)

    @Slot(str)
    def __error_translate_chunk(self, text: str):
        if not self.__error:
            self.__error = True
            color = dark.TEXT_ERROR if config.value('interface', 'theme') == 'dark' else light.TEXT_ERROR
            self.__log.append(f'<span style="color: {color};">{html.escape(text)}</span>')
            self.print_log()
            self.stop_translate()

    @Slot(str)
    def __warning_translate_chunk(self, text: str):
        self.__log.append(text)
        self.print_log()

    def print_log(self):
        self.edt_log.setText('<br>'.join(self.__log))
        self.edt_log.verticalScrollBar().setValue(self.edt_log.verticalScrollBar().maximum())

    def translate_click(self):
        if not self.__translating:
            self.translate()
        else:
            self.stop_translate()

    def cancel_click(self):
        self.close()
