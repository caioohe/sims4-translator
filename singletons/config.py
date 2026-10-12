# -*- coding: utf-8 -*-

import os
import ctypes
import copy
import tempfile
import ctypes.wintypes
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
from typing import Union

from utils.constants import *


def is_dark_theme():
    if os.name != 'nt':
        return False
    registry = ctypes.windll.advapi32
    hkey_current_user = 0x80000001
    sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize'
    value_name = 'AppsUseLightTheme'

    hkey = ctypes.wintypes.HKEY()
    result = registry.RegOpenKeyExW(hkey_current_user, sub_key, 0, 0x20019, ctypes.byref(hkey))

    if result != 0:
        return False

    value = ctypes.wintypes.DWORD()
    value_length = ctypes.wintypes.DWORD(ctypes.sizeof(value))
    result = registry.RegQueryValueExW(hkey, value_name, 0, None, ctypes.byref(value), ctypes.byref(value_length))
    registry.RegCloseKey(hkey)

    if result != 0:
        return False

    return value.value == 0


class ConfigManager:

    DEFAULTS = {
        'interface': {
            'language': 'en_US',
            'theme': ''
        },
        'dictionaries': {
            'gamepath': '',
            'dictpath': '',
            'strong': True
        },
        'save': {
            'backup': True,
            'experemental': False
        },
        'group': {
            'original': True,
            'highbit': False,
            'lowbit': False
        },
        'template': {
            'conflict': '1_{name}_{lang_d}',
            'non_conflict': 'z_{name}_{lang_d}'
        },
        'translation': {
            'source': 'ENG_US',
            'destination': 'RUS_RU'
        },
        'api': {
            'engine': '',
            'deepl_key': '',
            'gemini_key': '',
            'gemini_model': 'gemini-3.8-flash',
            'google_interval': 2,
            'microsoft_key': '',
            'microsoft_region': '',
            'batch_size': 50
        },
        'view': {
            'id': True,
            'instance': False,
            'group': False,
            'source': True,
            'comment': False,
            'colorbar': True,
            'numeration': NUMERATION_STANDART
        },
        'temporary': {
            'directory': os.path.abspath(os.path.expanduser('~/Documents'))
        }
    }

    def __init__(self) -> None:
        self.__config_file = os.path.abspath('./prefs/config.xml')
        self.__config = copy.deepcopy(self.DEFAULTS)
        self.__load()

    def __load(self) -> None:
        try:
            self.__update_defaults_from_file()
        except (ElementTree.ParseError, FileNotFoundError) as e:
            self.save()

    def save(self) -> None:
        root = ElementTree.Element('config')
        for section, options in self.__config.items():
            section_element = ElementTree.SubElement(root, section)
            for option, value in options.items():
                option_element = ElementTree.SubElement(section_element, option)
                option_element.text = self.__convert_to_str(value)

        rough = ElementTree.tostring(root, encoding='utf-8').decode('utf-8')
        reparsed = minidom.parseString(rough)
        prettyxml = reparsed.toprettyxml(indent='  ', encoding='utf-8')

        os.makedirs(os.path.dirname(self.__config_file), exist_ok=True)
        directory = os.path.dirname(self.__config_file)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=directory, prefix='.config-', delete=False) as fp:
                temp_path = fp.name
                fp.write(prettyxml)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(temp_path, self.__config_file)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    def value(self, section: str, option: str) -> Union[str, int, bool, None]:
        return self.__config.get(section, {}).get(option)

    def set_value(self, section: str, option: str, value: Union[str, int, bool]) -> None:
        if section not in self.__config:
            self.__config[section] = {}
        self.__config[section][option] = value

    def __update_defaults_from_file(self) -> None:
        tree = ElementTree.parse(self.__config_file)
        root = tree.getroot()
        for section in root:
            section_name = section.tag
            for option in section:
                option_name = option.tag
                option_value = (option.text or '') if (section_name == 'api' and option_name not in ('google_interval', 'batch_size')) else self.__convert_value(option.text)
                if section_name not in self.__config:
                    self.__config[section_name] = {}
                self.__config[section_name][option_name] = option_value

    @staticmethod
    def __convert_value(value: str) -> Union[str, int, bool, None]:
        if value is None:
            return ''
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        try:
            return int(value)
        except ValueError:
            return value
    
    @staticmethod
    def __convert_to_str(value: Union[str, int, bool]) -> str:
        if isinstance(value, bool):
            return 'true' if value else 'false'
        return str(value)

    @property
    def theme_name(self):
        name = self.value('interface', 'theme')
        if name:
            return name
        name = 'dark' if is_dark_theme() else 'light'
        self.set_value('interface', 'theme', name)
        return name

    def is_dark_theme(self):
        return self.theme_name == 'dark'


config = ConfigManager()
