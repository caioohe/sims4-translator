from types import SimpleNamespace
from threading import Event
from unittest.mock import Mock
import pytest
import requests
from utils.http_policy import HTTPTransport
import utils.microsoft as ms

class Config:
    def value(self, section, option):
        return {'microsoft_key':'synthetic-key','microsoft_region':'brazilsouth'}.get(option)


def response(code=200, body=None, headers=None):
    return SimpleNamespace(status_code=code, json=lambda:body, headers=headers or {}, close=lambda:None)

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.delenv('AZURE_TRANSLATOR_KEY',raising=False)
    monkeypatch.delenv('AZURE_TRANSLATOR_REGION',raising=False)
    transport=HTTPTransport(interval=2,retries=2)
    waits=[]
    monkeypatch.setattr(transport,'_wait',lambda delay,cancel:waits.append(delay))
    monkeypatch.setattr(ms,'microsoft_transport',transport)
    monkeypatch.setattr(requests,'post',Mock(side_effect=AssertionError('Unexpected network')))
    return waits


def echo(monkeypatch, change=lambda t:t):
    def post(url, **kwargs):
        return response(body=[{'translations':[{'to':kwargs['params']['to'],'text':change(item['Text'])}]} for item in kwargs['json']])
    mock=Mock(side_effect=post)
    monkeypatch.setattr(requests,'post',mock)
    return mock


def test_official_batch_gender_tokens_unicode(monkeypatch):
    mock=echo(monkeypatch,lambda t:t.replace('Hello','Olá').replace('He','Ele').replace('She','Ela'))
    source=['Hello {0.SimFirstName} & <b>🍀</b>\\n','{M0.He likes {1.Name}}{F0.She likes {1.Name}}','  Hello  ']
    code, result=ms.translate_microsoft(Config(),source,'ENG_US','POR_BR')
    assert code == 200
    assert result == ['Olá {0.SimFirstName} & <b>🍀</b>\\n','{M0.Ele likes {1.Name}}{F0.Ela likes {1.Name}}','  Olá  ']
    args=mock.call_args
    assert args.args[0] == 'https://api.cognitive.microsofttranslator.com/translate'
    assert args.kwargs['headers']['Ocp-Apim-Subscription-Key'] == 'synthetic-key'
    assert args.kwargs['headers']['Ocp-Apim-Subscription-Region'] == 'brazilsouth'
    assert args.kwargs['params']['textType'] == 'html'
    assert 'synthetic-key' not in args.args[0]
    assert '<span class="notranslate">' in args.kwargs['json'][0]['Text']

@pytest.mark.parametrize('change',[
    lambda s:s.replace('TS4GPH0END',''),lambda s:s.replace('TS4GPH0END','TS4GPH0ENDTS4GPH0END'),
    lambda s:s.replace('Hello','{new}'),lambda s:s.replace('Hello','<b>Hi</b>'),
    lambda s:s.replace('Hello','\nHi'),lambda s:s.replace('</div>',''),
    lambda s:s+'text',lambda s:s.replace('Hello','<!-- test -->Hello')])
def test_corrupt_output_rejected_whole_batch(monkeypatch,change):
    echo(monkeypatch,change)
    assert ms.translate_microsoft(Config(),['Hello {0.Name}','Other'],'ENG_US','POR_BR')[0] == 422

@pytest.mark.parametrize('body',[None,[],[{}],[{'translations':[]}],[{'translations':[{'to':'de','text':'<div>Hi</div>'}]}]])
def test_invalid_response(monkeypatch,body):
    monkeypatch.setattr(requests,'post',Mock(return_value=response(body=body)))
    assert ms.translate_microsoft(Config(),['Hello'],'ENG_US','POR_BR')[0] == 422

@pytest.mark.parametrize('code',[400,401,403,404])
def test_permanent_error_no_retry(monkeypatch,code):
    mock=Mock(return_value=response(code));monkeypatch.setattr(requests,'post',mock)
    assert ms.translate_microsoft(Config(),['Hello'],'ENG_US','POR_BR')[0] == code
    assert mock.call_count == 1

@pytest.mark.parametrize('code',[429,503])
def test_transient_then_success(monkeypatch,setup,code):
    mock=Mock(side_effect=[response(code,headers={'Retry-After':'30'}),response(body=[{'translations':[{'to':'pt','text':'<div>Olá</div>'}]}])])
    monkeypatch.setattr(requests,'post',mock)
    assert ms.translate_microsoft(Config(),['Hello'],'ENG_US','POR_BR') == (200,['Olá'])
    assert mock.call_count == 2 and max(setup) > 29

@pytest.mark.parametrize('exc',[requests.Timeout,requests.ConnectionError])
def test_connection_exhaustion_safe_message(monkeypatch,exc):
    mock=Mock(side_effect=exc('SECRET-KEY'));monkeypatch.setattr(requests,'post',mock)
    code,message=ms.translate_microsoft(Config(),['Hello'],'ENG_US','POR_BR')
    assert code == 503 and 'SECRET' not in message and mock.call_count == 3


def test_cancel(monkeypatch):
    cancel=Event();cancel.set()
    assert ms.translate_microsoft(Config(),['Hello'],'ENG_US','POR_BR',cancel)[0] == 499
    assert requests.post.call_count == 0


def test_env_and_language_variants(monkeypatch):
    monkeypatch.setenv('AZURE_TRANSLATOR_KEY','env-key')
    monkeypatch.setenv('AZURE_TRANSLATOR_REGION','westeurope')
    mock=echo(monkeypatch)
    assert ms.translate_microsoft(Config(),['Hello'],'ENG_US','POR_PT')[0] == 200
    assert mock.call_args.kwargs['params']['to'] == 'pt-pt'
    assert mock.call_args.kwargs['headers']['Ocp-Apim-Subscription-Key'] == 'env-key'


def test_bounds_no_network():
    assert ms.translate_microsoft(Config(),['x']*101,'ENG_US','POR_BR')[0] == 413
    assert ms.translate_microsoft(Config(),['x'],'BAD','POR_BR')[0] == 404
    assert ms.translate_microsoft(Config(),['{0.Name}'*1300],'ENG_US','POR_BR')[0] == 413
    assert requests.post.call_count == 0


def test_translator_single_and_worker_routing(monkeypatch,qapp):
    from singletons.config import config
    from singletons.translator import translator
    from windows.translate_dialog import BatchTranslateWorker
    from storages.records import MainRecord
    monkeypatch.setattr(config,'value',lambda section,option:{'source':'ENG_US','destination':'POR_BR','microsoft_key':'synthetic'}.get(option))
    echo(monkeypatch,lambda s:s.replace('Hello','Olá'))
    assert 'Microsoft' in translator.engines
    assert translator.translate('Microsoft','Hello {0.Name}').text == 'Olá {0.Name}'
    from utils.constants import RECORD_MAIN_SOURCE
    record=MainRecord(*([None]*14));record[RECORD_MAIN_SOURCE]='Hello {0.Name}'
    worker=BatchTranslateWorker(record,'Microsoft')
    results=[];worker.signals.result.connect(results.append)
    worker.run()
    assert results[0][0][1] == 'Olá {0.Name}'


def test_one_hundred_texts_allowed(monkeypatch):
    mock=echo(monkeypatch)
    assert ms.translate_microsoft(Config(),['Hello']*100,'ENG_US','POR_BR')[0] == 200
    assert len(mock.call_args.kwargs['json']) == 100
