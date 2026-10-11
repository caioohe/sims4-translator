# -*- coding: utf-8 -*-

from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import QWidget, QAbstractItemView, QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, \
    QLineEdit, QPushButton, QDoubleSpinBox, QSpinBox, QTableView, QVBoxLayout, QTabWidget, QHeaderView, QScrollArea


class Ui_OptionsDialog(object):

    def setupUi(self, OptionsDialog):
        OptionsDialog.resize(545, 490)
        OptionsDialog.setMinimumSize(545, 490)

        layout = QVBoxLayout(OptionsDialog)

        self.tab_general = QWidget()
        self.tab_dictionaries = QWidget()
        self.general_scroll = QScrollArea()
        self.general_scroll.setWidgetResizable(True)
        self.general_scroll.setWidget(self.tab_general)

        self.tabs = QTabWidget(OptionsDialog)
        self.tabs.addTab(self.general_scroll, '')
        self.tabs.addTab(self.tab_dictionaries, '')

        layout.addWidget(self.tabs)

        self.build_general_tab()
        self.build_dictionaries_tab()


        QMetaObject.connectSlotsByName(OptionsDialog)

    def build_general_tab(self):
        vlayout = QVBoxLayout(self.tab_general)

        self.gb_interface = QGroupBox(self.tab_general)

        layout_group = QVBoxLayout(self.gb_interface)

        layout_lang = QHBoxLayout()
        layout_theme = QHBoxLayout()

        self.lbl_language = QLabel(self.gb_interface)
        self.lbl_language_authors = QLabel(self.gb_interface)
        self.lbl_language_hint = QLabel(self.gb_interface)
        self.cb_language = QComboBox(self.gb_interface)

        self.lbl_theme = QLabel(self.gb_interface)
        self.lbl_theme_hint = QLabel(self.gb_interface)
        self.cb_theme = QComboBox(self.gb_interface)

        self.lbl_language_hint.setWordWrap(True)
        self.lbl_language_hint.setObjectName('muted')

        self.lbl_language.setMinimumHeight(26)
        self.lbl_theme.setMinimumHeight(26)

        self.lbl_theme_hint.setVisible(False)
        self.lbl_theme_hint.setWordWrap(True)

        layout_lang_lbl = QVBoxLayout()
        layout_lang_authors = QHBoxLayout()
        layout_lang_hint = QVBoxLayout()

        layout_theme_lbl = QVBoxLayout()
        layout_theme_plug = QHBoxLayout()
        layout_theme_hint = QVBoxLayout()

        layout_lang_authors.addWidget(self.cb_language)
        layout_lang_authors.addWidget(self.lbl_language_authors)
        layout_lang_authors.addStretch()

        layout_lang_lbl.addWidget(self.lbl_language)
        layout_lang_lbl.addStretch()

        layout_lang_hint.addLayout(layout_lang_authors)
        layout_lang_hint.addWidget(self.lbl_language_hint)

        layout_lang.addLayout(layout_lang_lbl)
        layout_lang.addLayout(layout_lang_hint)

        layout_theme_lbl.addWidget(self.lbl_theme)
        layout_theme_lbl.addStretch()

        layout_theme_plug.addWidget(self.cb_theme)
        layout_theme_plug.addStretch()

        layout_theme_hint.addLayout(layout_theme_plug)
        layout_theme_hint.addWidget(self.lbl_theme_hint)

        layout_theme.addLayout(layout_theme_lbl)
        layout_theme.addLayout(layout_theme_hint)

        self.lbl_language.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_theme.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_language.setMinimumWidth(75)
        self.lbl_theme.setMinimumWidth(75)

        layout_group.addLayout(layout_lang)
        layout_group.addLayout(layout_theme)

        vlayout.addWidget(self.gb_interface)

        gbox = QGroupBox(self.tab_general)
        layout_group = QVBoxLayout(gbox)

        self.cb_backup = QCheckBox(gbox)
        self.cb_experemental = QCheckBox(gbox)
        self.cb_strong = QCheckBox(gbox)

        layout_group.addWidget(self.cb_backup)
        layout_group.addWidget(self.cb_experemental)
        layout_group.addWidget(self.cb_strong)

        vlayout.addWidget(gbox)

        self.gb_lang = QGroupBox(self.tab_general)

        layout_lang = QHBoxLayout(self.gb_lang)

        self.label_source = QLabel(self.gb_lang)
        self.label_dest = QLabel(self.gb_lang)

        self.cb_source = QComboBox(self.gb_lang)
        self.cb_dest = QComboBox(self.gb_lang)

        layout_lang.addStretch()
        layout_lang.addWidget(self.label_source)
        layout_lang.addWidget(self.cb_source)
        layout_lang.addStretch()
        layout_lang.addWidget(self.label_dest)
        layout_lang.addWidget(self.cb_dest)
        layout_lang.addStretch()

        vlayout.addWidget(self.gb_lang)

        self.gb_deepl = QGroupBox(self.tab_general)

        layout_deepl = QHBoxLayout(self.gb_deepl)

        self.txt_deepl_key = QLineEdit(self.gb_deepl)
        self.txt_deepl_key.setEchoMode(QLineEdit.EchoMode.Password)

        layout_deepl.addWidget(self.txt_deepl_key)

        vlayout.addWidget(self.gb_deepl)

        self.gb_batch = QGroupBox(self.tab_general)
        batch_layout = QVBoxLayout(self.gb_batch)
        self.spin_batch_size = QSpinBox(self.gb_batch)
        self.spin_batch_size.setRange(1, 100)
        self.lbl_batch_hint = QLabel(self.gb_batch)
        self.lbl_batch_hint.setWordWrap(True)
        batch_layout.addWidget(self.lbl_batch_hint)
        batch_layout.addWidget(self.spin_batch_size)
        vlayout.addWidget(self.gb_batch)
        self.build_ai_tab(vlayout)
        vlayout.addStretch()

    def build_ai_tab(self, layout):
        self.gb_gemini = QGroupBox(self.tab_general)
        gemini_layout = QVBoxLayout(self.gb_gemini)
        self.txt_gemini_key = QLineEdit(self.gb_gemini)
        self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_gemini_key.setPlaceholderText('Gemini API key (or GEMINI_API_KEY environment variable)')
        self.cb_gemini_model = QComboBox(self.gb_gemini)
        self.cb_gemini_model.setEditable(True)
        self.cb_gemini_model.addItems(['gemini-3.8-flash', 'gemini-3.6-flash'])
        self.lbl_gemini_hint = QLabel(self.gb_gemini)
        self.lbl_gemini_hint.setWordWrap(True)
        self.btn_gemini_key = QPushButton(self.gb_gemini)
        self.btn_gemini_test = QPushButton(self.gb_gemini)
        self.btn_gemini_key.setAutoDefault(False)
        self.btn_gemini_test.setAutoDefault(False)
        self.lbl_gemini_status = QLabel(self.gb_gemini)
        self.lbl_gemini_status.setWordWrap(True)
        self.lbl_gemini_status.setTextFormat(Qt.TextFormat.PlainText)
        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_gemini_key)
        buttons.addWidget(self.btn_gemini_test)
        gemini_layout.addWidget(self.txt_gemini_key)
        gemini_layout.addWidget(self.cb_gemini_model)
        gemini_layout.addWidget(self.lbl_gemini_hint)
        gemini_layout.addLayout(buttons)
        gemini_layout.addWidget(self.lbl_gemini_status)
        layout.addWidget(self.gb_gemini)
        self.gb_google = QGroupBox(self.tab_general)
        google_layout = QVBoxLayout(self.gb_google)
        self.lbl_google_hint = QLabel(self.gb_google)
        self.lbl_google_hint.setWordWrap(True)
        self.spin_google_interval = QDoubleSpinBox(self.gb_google)
        self.spin_google_interval.setRange(2, 60)
        self.spin_google_interval.setDecimals(1)
        self.spin_google_interval.setSuffix(' s')
        google_layout.addWidget(self.lbl_google_hint)
        google_layout.addWidget(self.spin_google_interval)
        layout.addWidget(self.gb_google)
        self.gb_microsoft = QGroupBox(self.tab_general)
        ms_layout = QVBoxLayout(self.gb_microsoft)
        self.txt_microsoft_key = QLineEdit(self.gb_microsoft)
        self.txt_microsoft_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_microsoft_key.setPlaceholderText('Azure Translator API key / AZURE_TRANSLATOR_KEY')
        self.txt_microsoft_region = QLineEdit(self.gb_microsoft)
        self.txt_microsoft_region.setPlaceholderText('Azure region, e.g. brazilsouth; blank for a global resource')
        self.lbl_microsoft_hint = QLabel(self.gb_microsoft)
        self.lbl_microsoft_hint.setWordWrap(True)
        self.btn_microsoft_key = QPushButton(self.gb_microsoft)
        self.btn_microsoft_test = QPushButton(self.gb_microsoft)
        self.btn_microsoft_key.setAutoDefault(False)
        self.btn_microsoft_test.setAutoDefault(False)
        self.lbl_microsoft_status = QLabel(self.gb_microsoft)
        self.lbl_microsoft_status.setWordWrap(True)
        self.lbl_microsoft_status.setTextFormat(Qt.TextFormat.PlainText)
        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_microsoft_key)
        buttons.addWidget(self.btn_microsoft_test)
        ms_layout.addWidget(self.txt_microsoft_key)
        ms_layout.addWidget(self.txt_microsoft_region)
        ms_layout.addWidget(self.lbl_microsoft_hint)
        ms_layout.addLayout(buttons)
        ms_layout.addWidget(self.lbl_microsoft_status)
        layout.addWidget(self.gb_microsoft)

    def build_dictionaries_tab(self):
        vlayout = QVBoxLayout(self.tab_dictionaries)
        vlayout.setSpacing(8)

        self.gb_path = QGroupBox(self.tab_dictionaries)

        layout_path = QHBoxLayout(self.gb_path)

        self.txt_path = QLineEdit(self.gb_path)

        self.btn_path = QPushButton(self.gb_path)
        self.btn_path.setText('...')
        self.btn_path.setAutoDefault(False)

        layout_path.addWidget(self.txt_path)
        layout_path.addWidget(self.btn_path)

        vlayout.addWidget(self.gb_path)

        self.tableview = QTableView(self.tab_dictionaries)
        self.tableview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableview.setAutoScroll(False)
        self.tableview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableview.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tableview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableview.setShowGrid(False)
        self.tableview.setGridStyle(Qt.PenStyle.NoPen)
        self.tableview.setWordWrap(False)
        self.tableview.horizontalHeader().setVisible(False)

        header = self.tableview.verticalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setDefaultSectionSize(26)
        header.setVisible(False)
        
        self.btn_build = QPushButton(self.tab_dictionaries)
        self.btn_build.setAutoDefault(False)

        vlayout.addWidget(self.tableview)
        vlayout.addWidget(self.btn_build)
