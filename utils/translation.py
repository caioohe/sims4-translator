"""Network policy and lossless token protection, independent of Qt."""
import html
import random
import re
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests

TOKEN = re.compile(r"{[^{}]*}|<[^>]+>|\\[nr]|\r\n|\n|\r")


def protect(text, xml=False):
    # A prefix absent from the source avoids replacing literal numbers or markers.
    prefix = 'TS4PH'
    while prefix in text:
        prefix += 'X'
    placeholders = {}
    def replace(match):
        marker = f'{prefix}{len(placeholders)}END'
        placeholders[marker] = match.group(0)
        return f'<ph>{marker}</ph>' if xml else marker
    if xml:
        parts, offset = [], 0
        for match in TOKEN.finditer(text):
            parts.extend([html.escape(text[offset:match.start()]), replace(match)])
            offset = match.end()
        parts.append(html.escape(text[offset:]))
        return '<root>' + ''.join(parts) + '</root>', placeholders
    return TOKEN.sub(replace, text), placeholders


def restore(text, placeholders, xml=False):
    if not isinstance(text, str):
        raise ValueError('Translation text is not a string.')
    if xml:
        from xml.etree import ElementTree as ET
        root = ET.fromstring(text)
        if root.tag != 'root':
            raise ValueError('Translation XML root was changed.')
        text = ''.join(root.itertext())
    for marker in placeholders:
        if text.count(marker) != 1:
            raise ValueError('Translation changed or removed a protected token; original text retained.')
    for marker, value in placeholders.items():
        text = text.replace(marker, value)
    return text


class TranslationCancelled(Exception):
    pass


class DeepLTransport:
    def __init__(self, interval=0.5, retries=3):
        self.interval = interval
        self.retries = retries
        self._lock = threading.Lock()
        self._next_request = 0.0

    @staticmethod
    def _wait(seconds, cancel):
        if cancel is not None:
            if cancel.wait(max(0, seconds)):
                raise TranslationCancelled()
        elif seconds > 0:
            time.sleep(seconds)

    @staticmethod
    def _retry_after(value):
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            try:
                return max(0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return 0.0

    def post(self, url, payload, key, cancel=None):
        # Shared lock covers retries, preventing other callers from defeating cooldown.
        with self._lock:
            for attempt in range(self.retries + 1):
                self._wait(self._next_request - time.monotonic(), cancel)
                if cancel is not None and cancel.is_set():
                    raise TranslationCancelled()
                try:
                    response = requests.post(url, json=payload,
                        headers={'Authorization': f'DeepL-Auth-Key {key}'}, timeout=(5, 30))
                except (requests.ConnectionError, requests.Timeout):
                    self._next_request = time.monotonic() + self.interval
                    if attempt == self.retries:
                        raise
                    delay = 2 ** attempt + random.uniform(0, 0.25)
                else:
                    self._next_request = time.monotonic() + self.interval
                    if response.status_code not in (429, 500, 502, 503, 504):
                        return response
                    if attempt == self.retries:
                        return response
                    delay = max(2 ** attempt + random.uniform(0, 0.25),
                                self._retry_after(response.headers.get('Retry-After')))
                    response.close()
                # Longer server delays are respected, with cancellable waits.
                self._next_request = time.monotonic() + delay
        raise AssertionError('Unreachable')


deepl_transport = DeepLTransport()
