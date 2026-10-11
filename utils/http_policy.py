"""Serialized provider requests with cancellable cooldowns, without bypasses."""
import random
import re
import time
import requests
from utils.translation import DeepLTransport, TranslationCancelled


class HTTPTransport(DeepLTransport):
    def defer(self, seconds):
        with self._lock:
            self._next_request = max(self._next_request, time.monotonic() + seconds)

    def request(self, method, url, *, cancel=None, backoff=2, cooldown=60,
                stop_retry=None, body_delay=None, **kwargs):
        with self._lock:
            for attempt in range(self.retries + 1):
                self._wait(self._next_request - time.monotonic(), cancel)
                if cancel is not None and cancel.is_set():
                    raise TranslationCancelled()
                try:
                    caller = requests.get if method == 'GET' else requests.post
                    response = caller(url, **kwargs)
                except (requests.ConnectionError, requests.Timeout):
                    self._next_request = time.monotonic() + self.interval
                    if attempt == self.retries:
                        raise
                    delay = backoff * 2 ** attempt + random.uniform(0, 0.25)
                else:
                    self._next_request = time.monotonic() + self.interval
                    if response.status_code not in (429, 500, 502, 503, 504):
                        return response
                    delay = max(backoff * 2 ** attempt + random.uniform(0, 0.25),
                                self._retry_after(response.headers.get('Retry-After')),
                                body_delay(response) if body_delay else 0)
                    if (attempt == self.retries or delay > 60
                            or (stop_retry is not None and stop_retry(response))):
                        if response.status_code == 429:
                            self._next_request = time.monotonic() + max(cooldown, delay)
                        return response
                    response.close()
                self._next_request = time.monotonic() + delay
        raise AssertionError('Unreachable')


def gemini_error_details(response):
    try:
        details = response.json().get('error', {}).get('details', [])
        return details if isinstance(details, list) else []
    except (TypeError, AttributeError, ValueError):
        return []


def gemini_daily_quota(response):
    if response.status_code != 429:
        return False
    for detail in gemini_error_details(response):
        if not isinstance(detail, dict):
            continue
        violations = detail.get('violations', [])
        if not isinstance(violations, list):
            continue
        for violation in violations:
            if isinstance(violation, dict):
                quota = str(violation.get('quotaId', '')).lower()
                if 'perday' in quota or 'per_day' in quota:
                    return True
    return False


def gemini_retry_delay(response):
    delays = [0.0]
    for detail in gemini_error_details(response):
        if isinstance(detail, dict):
            value = detail.get('retryDelay')
            if isinstance(value, str) and re.fullmatch(r'\d+(?:\.\d+)?s', value):
                delays.append(float(value[:-1]))
    return max(delays)


google_transport = HTTPTransport(interval=2, retries=1)
gemini_transport = HTTPTransport(interval=6, retries=2)
