from threading import Event
from unittest.mock import Mock
from types import SimpleNamespace
import pytest
import requests
from utils.translation import DeepLTransport, TranslationCancelled, protect, restore
from singletons.translator import translator
from singletons.config import config


def reply(code=200, data=None, headers=None):
    return SimpleNamespace(status_code=code, headers=headers or {}, json=lambda: data,
                           close=lambda: None)

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(requests, 'get', Mock(side_effect=AssertionError('Unexpected network')))
    monkeypatch.setattr(requests, 'post', Mock(side_effect=AssertionError('Unexpected network')))

@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(config, 'value', lambda section, option: {
        ('api','deepl_key'): 'test:fx', ('translation','source'): 'ENG_US',
        ('translation','destination'): 'POR_BR'}.get((section, option)))
    from singletons import translator as module
    transport = DeepLTransport(interval=0, retries=3)
    monkeypatch.setattr(module, 'deepl_transport', transport)
    monkeypatch.setattr(transport, '_wait', lambda seconds, cancel: None)
    return transport

@pytest.mark.parametrize('code', [429, 500, 502, 503, 504])
def test_transient_retry(monkeypatch, code):
    post = Mock(side_effect=[reply(code, headers={'Retry-After':'7'}), reply()])
    monkeypatch.setattr(requests, 'post', post)
    transport = DeepLTransport(interval=0)
    waits = []
    monkeypatch.setattr(transport, '_wait', lambda seconds, cancel: waits.append(seconds))
    assert transport.post('https://api-free.deepl.com/v2/translate', {}, 'fake').status_code == 200
    assert post.call_count == 2
    assert waits[-1] > 6.9

@pytest.mark.parametrize('code', [400, 403, 413, 456])
def test_permanent_error_not_retried(monkeypatch, code):
    post = Mock(return_value=reply(code))
    monkeypatch.setattr(requests, 'post', post)
    assert DeepLTransport(interval=0).post('url', {}, 'fake').status_code == code
    assert post.call_count == 1

@pytest.mark.parametrize('error', [requests.Timeout, requests.ConnectionError])
def test_network_retry_exhaustion(monkeypatch, error):
    post = Mock(side_effect=error('secret must never reach UI'))
    monkeypatch.setattr(requests, 'post', post)
    transport = DeepLTransport(interval=0)
    monkeypatch.setattr(transport, '_wait', lambda *args: None)
    with pytest.raises(error):
        transport.post('url', {}, 'fake')
    assert post.call_count == 4


def test_429_exhaustion(monkeypatch, api):
    post = Mock(return_value=reply(429))
    monkeypatch.setattr(requests, 'post', post)
    assert translator.translate('DeepL', 'Hello').status_code == 429
    assert post.call_count == 4


def test_cancel_no_request(monkeypatch):
    cancel = Event(); cancel.set()
    with pytest.raises(TranslationCancelled):
        DeepLTransport().post('url', {}, 'fake', cancel)
    assert requests.post.call_count == 0

@pytest.mark.parametrize('value', ['8','invalid',None])
def test_retry_after(value):
    assert DeepLTransport._retry_after(value) == (8 if value == '8' else 0)

@pytest.mark.parametrize('xml', [False, True])
@pytest.mark.parametrize('text', [
    '(0) {0.SimFirstName} <b> Olá & 漢字 😀 </b>\\n',
    'TS4PH {M0.he}{F0.she} {1.Number}', '{token} {token}', 'literal <root> & >'])
def test_tokens_roundtrip(xml, text):
    encoded, ph = protect(text, xml)
    assert restore(encoded, ph, xml) == text

@pytest.mark.parametrize('xml', [False, True])
def test_missing_token_rejected(xml):
    encoded, ph = protect('Hello {0.SimName}', xml)
    with pytest.raises(ValueError):
        restore(encoded.replace(next(iter(ph)), 'altered'), ph, xml)


def test_deepl_native_batch(monkeypatch, api):
    def echo(url, **kwargs):
        assert url == 'https://api-free.deepl.com/v2/translate'
        assert kwargs['timeout'] == (5, 30)
        assert kwargs['json']['ignore_tags'] == ['ph']
        return reply(data={'translations':[{'text':s.replace('Hello','Olá')} for s in kwargs['json']['text']]})
    monkeypatch.setattr(requests, 'post', Mock(side_effect=echo))
    assert translator.translate_many(['Hello\nworld', 'Hello {0.Name}']).text == ['Olá\nworld', 'Olá {0.Name}']
    assert requests.post.call_count == 1

@pytest.mark.parametrize('data', [{}, {'translations':[]}, {'translations':[{'text':None}]}])
def test_bad_deepl_response(monkeypatch, api, data):
    monkeypatch.setattr(requests, 'post', Mock(return_value=reply(data=data)))
    assert translator.translate('DeepL', 'hello').status_code == 422


def test_request_limit(api):
    assert translator.translate_many(['hi'] * 51).status_code == 413
    assert translator.translate_many(['漢' * 50000]).status_code == 413
    assert requests.post.call_count == 0


def test_mymemory_bytes(monkeypatch, api):
    assert translator.translate('MyMemory', '漢' * 200).status_code != 200
    assert requests.get.call_count == 0


def test_mymemory_body_error(monkeypatch, api):
    monkeypatch.setattr(requests, 'get', Mock(return_value=reply(data={
        'responseStatus':403, 'responseData':{'translatedText':'quota error'}})))
    assert translator.translate('MyMemory', 'hello').status_code == 403


def test_google_html_changed(monkeypatch, api):
    monkeypatch.setattr(requests, 'get', Mock(return_value=SimpleNamespace(status_code=200, content=b'<html>No translation</html>', close=lambda:None)))
    assert translator.translate('Google', 'hello').status_code != 200


def test_transport_serializes_concurrent_callers(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock
    import time
    guard = Lock(); active = 0; peak = 0
    def post(*args, **kwargs):
        nonlocal active, peak
        with guard:
            active += 1; peak = max(peak, active)
        time.sleep(.01)
        with guard:
            active -= 1
        return reply()
    monkeypatch.setattr(requests, 'post', post)
    transport = DeepLTransport(interval=0)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _:transport.post('url', {}, 'fake'), range(4)))
    assert peak == 1


def test_invalid_xml_response_rejected(monkeypatch, api):
    monkeypatch.setattr(requests, 'post', Mock(return_value=reply(data={
        'translations':[{'text':'<root>broken'}]})))
    assert translator.translate('DeepL', 'hello').status_code == 422


def test_actual_json_wire_size_checked(api):
    # requests JSON defaults escape non-ASCII: 23k Han characters exceed 128 KiB.
    assert translator.translate_many(['漢' * 23000]).status_code == 413
    assert requests.post.call_count == 0


def test_actual_linebreaks_are_protected():
    text = 'First\nSecond\r\nThird\rFourth'
    encoded, ph = protect(text, xml=True)
    assert '\n' not in encoded and '\r' not in encoded
    assert restore(encoded, ph, xml=True) == text
