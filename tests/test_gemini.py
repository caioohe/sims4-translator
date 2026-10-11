import json
from types import SimpleNamespace
from threading import Event
from unittest.mock import Mock
import pytest
import requests
from singletons.translator import translator
from singletons.config import config
from utils.http_policy import HTTPTransport
from utils.sims_tokens import protect_sims, restore_sims


def reply(status=200, body=None, headers=None):
    return SimpleNamespace(status_code=status, headers=headers or {}, json=lambda:body, close=lambda:None)


def generated(entries, finish='STOP', extra=None):
    body = {'candidates':[{'finishReason':finish, 'content':{'parts':[{'text':json.dumps({'translations':entries})}]}}]}
    if extra:
        body.update(extra)
    return body

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    import utils.gemini as gemini
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    settings = {('api','gemini_key'):'synthetic-secret', ('api','gemini_model'):'gemini-3.8-flash',
        ('translation','source'):'ENG_US', ('translation','destination'):'POR_BR'}
    monkeypatch.setattr(config, 'value', lambda s,o:settings.get((s,o)))
    transport = HTTPTransport(interval=0, retries=2)
    monkeypatch.setattr(transport, '_wait', lambda *args:None)
    monkeypatch.setattr(gemini, 'gemini_transport', transport)
    monkeypatch.setattr(requests, 'get', Mock(side_effect=AssertionError('Unexpected network')))
    monkeypatch.setattr(requests, 'post', Mock(side_effect=AssertionError('Unexpected network')))
    return settings, transport


def test_official_request_and_id_mapping(monkeypatch):
    def post(url, **kwargs):
        assert url == 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent'
        assert 'synthetic-secret' not in url
        assert kwargs['headers'] == {'x-goog-api-key':'synthetic-secret'}
        assert kwargs['timeout'] == (5,60)
        assert kwargs['json']['generationConfig']['responseMimeType'] == 'application/json'
        assert 'Portuguese (Brazil)' in kwargs['json']['systemInstruction']['parts'][0]['text']
        records=json.loads(kwargs['json']['contents'][0]['parts'][0]['text'])
        assert '{' not in records[0]['text'] and '<' not in records[0]['text']
        output=[{'id':r['id'], 'text':r['text'].replace('Hello','Olá').replace('world','mundo')} for r in reversed(records)]
        return reply(body=generated(output))
    monkeypatch.setattr(requests, 'post', Mock(side_effect=post))
    result=translator.translate_gemini_many(['Hello {0.SimFirstName}', '<b>Hello world</b>\\n😀'])
    assert result.status_code == 200
    assert result.text == ['Olá {0.SimFirstName}', '<b>Olá mundo</b>\\n😀']
    assert requests.post.call_count == 1


def test_gender_words_translate_without_changing_structure(monkeypatch):
    def post(url, **kwargs):
        rows=json.loads(kwargs['json']['contents'][0]['parts'][0]['text'])
        content=rows[0]['text'].replace('He likes','Ele gosta de').replace('She likes','Ela gosta de')
        return reply(body=generated([{'id':0,'text':content}]))
    monkeypatch.setattr(requests, 'post', Mock(side_effect=post))
    source='{M0.He likes {1.SimFirstName}}{F0.She likes {1.SimFirstName}}'
    assert translator.translate('Gemini',source).text == '{M0.Ele gosta de {1.SimFirstName}}{F0.Ela gosta de {1.SimFirstName}}'

@pytest.mark.parametrize('source', [
    'Olá 漢字 😀 {0.Name} <b>bold</b>\\n', 'Literal (0) TS4GPH {0.Name}',
    '{M0.He}{F0.She}', '{M0.He {F1.said}}', '{{nested}}', 'incomplete { x } }',
    'line\nline\r\nlast\tend', '<font color="#fff">hello</font>', '< >', '{M0.}'])
def test_tokenizer_roundtrip(source):
    encoded, placeholders=protect_sims(source)
    assert restore_sims(encoded,placeholders) == source

@pytest.mark.parametrize('change', ['missing','duplicate','reordered','unknown','raw_brace','raw_tag','raw_newline'])
def test_token_corruption_rejected(change):
    encoded, ph=protect_sims('{0.Name} <b>Hello</b>')
    markers=list(ph)
    altered={'missing':encoded.replace(markers[0],''), 'duplicate':encoded+markers[0],
        'reordered':encoded.replace(markers[0],'SWAP').replace(markers[1],markers[0]).replace('SWAP',markers[1]),
        'unknown':encoded+'TS4GPH999END', 'raw_brace':encoded+'{0.Bad}',
        'raw_tag':encoded+'<i>', 'raw_newline':encoded+'\n'}[change]
    with pytest.raises(ValueError):
        restore_sims(altered,ph)

@pytest.mark.parametrize('entries', [[], [{'id':0,'text':'a'},{'id':0,'text':'b'}],
    [{'id':0,'text':'a'},{'id':2,'text':'b'}], [{'id':False,'text':'a'},{'id':1,'text':'b'}],
    [{'id':'0','text':'a'},{'id':1,'text':'b'}], [{'id':0,'text':None},{'id':1,'text':'b'}],
    [{'id':0,'text':''},{'id':1,'text':'b'}], [{'id':0,'text':'a','extra':'x'},{'id':1,'text':'b'}]])
def test_invalid_ids_or_texts_reject_entire_batch(monkeypatch, entries):
    monkeypatch.setattr(requests,'post',Mock(return_value=reply(body=generated(entries))))
    assert translator.translate_gemini_many(['hello','world']).status_code == 422

@pytest.mark.parametrize('finish', ['MAX_TOKENS','SAFETY','RECITATION',None])
def test_incomplete_candidate_rejected(monkeypatch, finish):
    monkeypatch.setattr(requests,'post',Mock(return_value=reply(body=generated([{'id':0,'text':'hi'}],finish))))
    assert translator.translate('Gemini','hello').status_code == 422


def test_invalid_json_and_duplicate_property(monkeypatch):
    for text in ['```json\n{}\n```','{"translations":[], "translations":[]}']:
        body=generated([])
        body['candidates'][0]['content']['parts'][0]['text']=text
        monkeypatch.setattr(requests,'post',Mock(return_value=reply(body=body)))
        assert translator.translate('Gemini','hello').status_code == 422


def test_blocked_prompt(monkeypatch):
    monkeypatch.setattr(requests,'post',Mock(return_value=reply(body={'promptFeedback':{'blockReason':'SAFETY'}})))
    assert translator.translate('Gemini','hello').status_code == 422

@pytest.mark.parametrize('code', [400,401,403,404])
def test_permanent_http_errors_not_retried(monkeypatch, code):
    monkeypatch.setattr(requests,'post',Mock(return_value=reply(code,{})))
    result=translator.translate('Gemini','hello')
    assert result.status_code == code and requests.post.call_count == 1
    assert 'synthetic-secret' not in result.text


def test_retry_429_and_google_retry_info(monkeypatch, setup):
    _, transport=setup
    delays=[]
    monkeypatch.setattr(transport,'_wait',lambda seconds,cancel:delays.append(seconds))
    post=Mock(side_effect=[reply(429,{'error':{'details':[{'retryDelay':'12s'}]}}), reply(body=generated([{'id':0,'text':'Olá'}]))])
    monkeypatch.setattr(requests,'post',post)
    assert translator.translate('Gemini','hello').status_code == 200
    assert post.call_count == 2 and delays[-1] > 11.9


def test_daily_quota_not_retried(monkeypatch):
    body={'error':{'details':[{'violations':[{'quotaId':'GenerateRequestsPerDayPerProjectPerModel'}]}]}}
    monkeypatch.setattr(requests,'post',Mock(return_value=reply(429,body)))
    assert translator.translate('Gemini','hello').status_code == 429
    assert requests.post.call_count == 1

@pytest.mark.parametrize('error', [requests.Timeout, requests.ConnectionError])
def test_network_failures_are_safe(monkeypatch, error):
    monkeypatch.setattr(requests,'post',Mock(side_effect=error('synthetic-secret')))
    response=translator.translate('Gemini','hello')
    assert response.status_code == 503 and 'synthetic-secret' not in response.text
    assert requests.post.call_count == 3


def test_environment_key_and_missing_key(monkeypatch, setup):
    settings,_=setup
    settings[('api','gemini_key')]=''
    assert 'Gemini' not in translator.engines
    assert translator.translate('Gemini','hello').status_code == 403
    monkeypatch.setenv('GEMINI_API_KEY','env-secret')
    assert 'Gemini' in translator.engines
    def post(url,**kwargs):
        assert kwargs['headers']['x-goog-api-key'] == 'env-secret'
        return reply(body=generated([{'id':0,'text':'Olá'}]))
    monkeypatch.setattr(requests,'post',Mock(side_effect=post))
    assert translator.translate('Gemini','hello').status_code == 200


def test_invalid_model_and_limits_no_network(setup):
    settings,_=setup
    assert translator.translate_gemini_many(['x']*51).status_code == 413
    assert translator.translate_gemini_many(['x'*16001]).status_code == 413
    settings[('api','gemini_model')]='../../host?key=secret'
    assert translator.translate('Gemini','hi').status_code == 400
    assert requests.post.call_count == 0


def test_cancel_before_request():
    event=Event();event.set()
    # The test fixture stubs waits, but the explicit cancellation check remains.
    assert translator.translate('Gemini','hello',event).status_code == 499
    assert requests.post.call_count == 0


def test_boundary_spaces_preserved(monkeypatch):
    monkeypatch.setattr(requests,'post',Mock(return_value=reply(body=generated([{'id':0,'text':'Olá'}]))))
    assert translator.translate('Gemini','  hello ').text == '  Olá '


def test_tokens_corrupted_by_gemini_reject_batch(monkeypatch):
    monkeypatch.setattr(requests,'post',Mock(return_value=reply(body=generated([{'id':0,'text':'Olá'}]))))
    assert translator.translate('Gemini','Hello {0.Name}').status_code == 422


def test_empty_source_cannot_gain_generated_content(monkeypatch):
    monkeypatch.setattr(requests,'post',Mock(return_value=reply(body=generated([{'id':0,'text':'invented'}]))))
    assert translator.translate('Gemini','').status_code == 422


def test_portugal_language_is_distinct(monkeypatch,setup):
    settings,_=setup;settings[('translation','destination')]='POR_PT'
    def post(url,**kwargs):
        assert 'Portuguese (Portugal)' in kwargs['json']['systemInstruction']['parts'][0]['text']
        return reply(body=generated([{'id':0,'text':'Olá'}]))
    monkeypatch.setattr(requests,'post',Mock(side_effect=post))
    assert translator.translate('Gemini','hello').status_code == 200
