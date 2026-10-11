import time
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import requests
from utils.http_policy import HTTPTransport
from utils.google_translate import translate_google
from singletons.translator import translator
from singletons.config import config


def reply(code=200, text='<div class="result-container">Olá</div>', headers=None):
    return SimpleNamespace(status_code=code,content=text.encode(),headers=headers or {},close=lambda:None)

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    import utils.google_translate as module
    import singletons.translator as singleton
    transport=HTTPTransport(interval=2,retries=1)
    monkeypatch.setattr(module,'google_transport',transport)
    monkeypatch.setattr(singleton,'google_transport',transport)
    waits=[]
    monkeypatch.setattr(transport,'_wait',lambda seconds,cancel:waits.append(seconds))
    monkeypatch.setattr(requests,'get',Mock(side_effect=AssertionError('Unexpected network')))
    monkeypatch.setattr(requests,'post',Mock(side_effect=AssertionError('Unexpected network')))
    return transport,waits


def test_429_retry_then_success(monkeypatch,setup):
    post=Mock(side_effect=[reply(429,headers={'Retry-After':'30'}),reply()])
    monkeypatch.setattr(requests,'get',post)
    assert translate_google('Hello','pt')[0] == 200
    assert post.call_count == 2 and setup[1][-1] > 29.9
    assert post.call_args.kwargs['timeout'] == (5,15)


def test_429_exhaustion_keeps_cooldown(monkeypatch,setup):
    monkeypatch.setattr(requests,'get',Mock(return_value=reply(429)))
    code,text=translate_google('Hello','pt')
    assert code == 429 and '429' in text and requests.get.call_count == 2
    assert setup[0]._next_request-time.monotonic() > 59


def test_long_retry_after_not_ignored(monkeypatch,setup):
    monkeypatch.setattr(requests,'get',Mock(return_value=reply(429,headers={'Retry-After':'120'})))
    assert translate_google('Hello','pt')[0] == 429
    assert requests.get.call_count == 1
    assert setup[0]._next_request-time.monotonic() > 119

@pytest.mark.parametrize('code',[403,404])
def test_permanent_no_retry(monkeypatch,code):
    monkeypatch.setattr(requests,'get',Mock(return_value=reply(code)))
    assert translate_google('Hello','pt')[0] == code
    assert requests.get.call_count == 1


def test_challenge_200_not_applied(monkeypatch,setup):
    monkeypatch.setattr(requests,'get',Mock(return_value=reply(text='<div class="g-recaptcha"></div>')))
    assert translate_google('Hello','pt')[0] == 429
    assert requests.get.call_count == 1
    assert setup[0]._next_request-time.monotonic() > 59


def test_nested_html_and_entities(monkeypatch):
    monkeypatch.setattr(requests,'get',Mock(return_value=reply(text='<div class="result-container">Olá <span>mundo</span> &amp; amigos</div>')))
    assert translate_google('Hello','pt') == (200,'Olá mundo & amigos')


def test_request_spacing(monkeypatch,setup):
    monkeypatch.setattr(requests,'get',Mock(return_value=reply()))
    translate_google('One','pt');translate_google('Two','pt')
    assert setup[1][-1] > 1.9


def test_google_preserves_tokens(monkeypatch):
    monkeypatch.setattr(config,'value',lambda s,o:{('translation','destination'):'POR_BR'}.get((s,o)))
    def get(url,**kwargs):
        return reply(text='<div class="result-container">'+kwargs['params']['q'].replace('Hello','Olá')+'</div>')
    monkeypatch.setattr(requests,'get',Mock(side_effect=get))
    assert translator.translate('Google','Hello {0.Name}').text == 'Olá {0.Name}'


def test_cancel_no_google_request():
    event=Event();event.set()
    assert translate_google('Hello','pt',event)[0] == 499
    assert requests.get.call_count == 0
