"""Official Azure Translator v3 adapter; no paid-resource provisioning."""
import html
import os
import re
from html.parser import HTMLParser
import requests
from utils.http_policy import HTTPTransport
from utils.sims_tokens import protect_sims, restore_sims
from utils.translation import TranslationCancelled

LANGUAGES = dict(zip(
    ['ENG_US','CHS_CN','CHT_CN','CZE_CZ','DAN_DK','DUT_NL','FIN_FI','FRE_FR','GER_DE',
     'ITA_IT','JPN_JP','KOR_KR','NOR_NO','POL_PL','POR_PT','POR_BR','RUS_RU','SPA_ES','SWE_SE','THA_TH','UKR_UA'],
    ['en','zh-Hans','zh-Hant','cs','da','nl','fi','fr','de','it','ja','ko','nb','pl','pt-pt','pt','ru','es','sv','th','uk']))
microsoft_transport = HTTPTransport(interval=2, retries=2)


def api_key(config):
    return (os.environ.get('AZURE_TRANSLATOR_KEY') or config.value('api','microsoft_key') or '').strip()


class _Result(HTMLParser):
    """Flatten only our wrapper and notranslate spans, rejecting invented HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []
        self.root_seen = False

    def handle_starttag(self, tag, attrs):
        if tag == 'div' and not attrs and not self.stack and not self.root_seen:
            self.root_seen = True
        elif tag == 'span' and dict(attrs) == {'class':'notranslate'} and self.stack == ['div']:
            pass
        else:
            raise ValueError('Unexpected translation HTML.')
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            raise ValueError('Unbalanced translation HTML.')

    def handle_data(self, data):
        if not self.stack:
            if data.strip():
                raise ValueError('Text outside wrapper.')
        else:
            self.parts.append(data)

    def handle_comment(self, data):
        raise ValueError('Unexpected HTML comment.')

    def handle_decl(self, decl):
        raise ValueError('Unexpected HTML declaration.')


def _prepare(text):
    protected, tokens = protect_sims(text)
    encoded = html.escape(protected)
    for marker in tokens:
        encoded = encoded.replace(marker, '<span class="notranslate">'+marker+'</span>')
    return '<div>'+encoded+'</div>', tokens


def translate_microsoft(config, texts, source, destination, cancel=None):
    key = api_key(config)
    if not key:
        return 403, 'Microsoft Translator API key is missing. Add it in Options.'
    if source not in LANGUAGES or destination not in LANGUAGES:
        return 404, 'Microsoft Translator language is not configured.'
    region = (os.environ.get('AZURE_TRANSLATOR_REGION') or config.value('api','microsoft_region') or '').strip()
    if region and not re.fullmatch(r'[a-z0-9-]{1,64}',region):
        return 400, 'Invalid Azure region. Use the region from your Translator resource.'
    if not 1 <= len(texts) <= 100 or sum(len(t) for t in texts) > 16000:
        return 413, 'Microsoft batch exceeds 100 strings or 16000 characters.'
    try:
        prepared = [_prepare(t) for t in texts]
        # Azure counts the HTML too. Stay below the official 50,000-character request limit.
        if sum(len(t[0].encode('utf-16-le')) // 2 for t in prepared) > 50000:
            return 413, 'Protected Microsoft batch exceeds 50000 characters. Use smaller batches.'
        headers = {'Ocp-Apim-Subscription-Key':key,'Content-Type':'application/json; charset=UTF-8'}
        if region:
            headers['Ocp-Apim-Subscription-Region'] = region
        response = microsoft_transport.request('POST',
            'https://api.cognitive.microsofttranslator.com/translate', cancel=cancel, backoff=5,
            params={'api-version':'3.0','from':LANGUAGES[source],'to':LANGUAGES[destination],
                    'textType':'html','profanityAction':'NoAction'},
            headers=headers, json=[{'Text':p[0]} for p in prepared], timeout=(5,60))
        try:
            if response.status_code != 200:
                messages = {400:'Microsoft rejected the request.',401:'Invalid Microsoft key or region.',
                            403:'Microsoft access denied or quota exhausted.',429:'Microsoft rate limit or quota reached. Resume later.'}
                return response.status_code, messages.get(response.status_code, f'Microsoft HTTP {response.status_code}. Try again later.')
            body = response.json()
        finally:
            response.close()
        if not isinstance(body,list) or len(body) != len(texts):
            raise ValueError('Invalid result count.')
        results = []
        for original, (_, tokens), entry in zip(texts,prepared,body):
            translations = entry['translations']
            if len(translations) != 1 or translations[0]['to'].lower() != LANGUAGES[destination].lower():
                raise ValueError('Unexpected target language.')
            parser = _Result()
            parser.feed(translations[0]['text'])
            parser.close()
            if parser.stack or not parser.root_seen:
                raise ValueError('Invalid HTML wrapper.')
            translated = restore_sims(''.join(parser.parts),tokens)
            if bool(original.strip()) != bool(translated.strip()):
                raise ValueError('Empty or invented translation.')
            if not original.strip():
                results.append(original)
                continue
            leading = original[:len(original)-len(original.lstrip(' \t'))]
            trailing = original[len(original.rstrip(' \t')):]
            results.append(leading+translated.strip(' \t')+trailing)
        return 200, results
    except TranslationCancelled:
        return 499, 'Translation cancelled.'
    except requests.RequestException:
        return 503, 'Microsoft connection failed or timed out. Original strings retained.'
    except (ValueError,TypeError,KeyError,AttributeError):
        return 422, 'Microsoft returned invalid results or changed TS4 tokens. Original strings retained.'
