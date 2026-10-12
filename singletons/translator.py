# -*- coding: utf-8 -*-

import requests
import json
from xml.etree.ElementTree import ParseError
from utils.translation import protect, restore, deepl_transport, TranslationCancelled
from utils.gemini import api_key as gemini_key, translate_gemini
from utils.microsoft import api_key as microsoft_key, translate_microsoft
from utils.google_translate import translate_google
from utils.http_policy import google_transport
from collections import namedtuple
from typing import List

from singletons.config import config
from singletons.interface import interface
from singletons.languages import languages


Response = namedtuple('Response', 'status_code text')


class Translator:

    @property
    def engines(self) -> List[str]:
        engines = ['Google', 'MyMemory']
        if config.value('api', 'deepl_key'):
            engines.append('DeepL')
        if gemini_key(config):
            engines.append('Gemini')
        if microsoft_key(config):
            engines.append('Microsoft')
        return engines

    @property
    def available(self) -> bool:
        return len(self.engines) > 0

    def translate(self, engine: str, text: str, cancel=None) -> Response:
        if engine.lower() in ('deepl', 'gemini', 'microsoft'):
            if engine.lower() == 'microsoft':
                response = self.translate_microsoft_many([text], cancel)
                return Response(response.status_code, response.text[0] if response.status_code == 200 else response.text)
            response = (self.translate_gemini_many([text], cancel) if engine.lower() == 'gemini'
                        else self.translate_many([text], cancel))
            return Response(response.status_code, response.text[0] if response.status_code == 200 else response.text)
        protected, placeholders = protect(text)
        response = self.__mymemory(protected) if engine.lower() == 'mymemory' else self.__google(protected, cancel)
        if response.status_code != 200:
            return response
        try:
            return Response(200, restore(response.text, placeholders))
        except (ValueError, ParseError) as exc:
            return Response(422, str(exc))

    def translate_many(self, texts, cancel=None):
        api_key = config.value('api', 'deepl_key') or ''
        src, dst = languages.source, languages.destination
        if not api_key:
            return Response(403, 'DeepL API key is missing.')
        if not (src and src.deepl and dst and dst.deepl):
            return Response(404, interface.text('Errors', 'Language code not found!'))
        prepared = [protect(text, xml=True) for text in texts]
        payload = {'text': [entry[0] for entry in prepared],
                   'source_lang': src.deepl, 'target_lang': dst.deepl,
                   'tag_handling': 'xml', 'ignore_tags': ['ph'],
                   'split_sentences': 'nonewlines'}
        if not 1 <= len(texts) <= 50 or len(json.dumps(payload).encode('utf-8')) > 128 * 1024:
            return Response(413, 'DeepL request exceeds 50 texts or 128 KiB.')
        url = 'https://api-free.deepl.com/v2/translate' if api_key.endswith(':fx') else 'https://api.deepl.com/v2/translate'
        try:
            resp = deepl_transport.post(url, payload, api_key, cancel)
            if resp.status_code != 200:
                messages = {403: 'Invalid DeepL API key.', 456: 'DeepL quota exceeded. Check your account usage limits.',
                            429: 'DeepL rate limit persists after retries. Wait before resuming.'}
                return Response(resp.status_code, messages.get(resp.status_code, f'DeepL HTTP {resp.status_code}.'))
            entries = resp.json()['translations']
            if len(entries) != len(texts):
                raise ValueError('DeepL returned an unexpected number of translations.')
            return Response(200, [restore(entry['text'], ph, xml=True) for entry, (_, ph) in zip(entries, prepared)])
        except TranslationCancelled:
            return Response(499, 'Translation cancelled.')
        except requests.RequestException:
            return Response(503, 'DeepL connection failed or timed out after retries. You can resume the untranslated strings.')
        except (KeyError, IndexError, TypeError, ValueError, ParseError) as exc:
            return Response(422, f'Invalid DeepL response: {exc}')

    def translate_microsoft_many(self, texts, cancel=None):
        return Response(*translate_microsoft(config, texts,
            config.value('translation', 'source'), config.value('translation', 'destination'), cancel))

    def translate_gemini_many(self, texts, cancel=None):
        return Response(*translate_gemini(config, texts,
            config.value('translation', 'source'), config.value('translation', 'destination'), cancel))

    @staticmethod
    def __google(text: str, cancel=None) -> Response:
        language = languages.destination
        try:
            google_transport.interval = max(2.0, min(60.0, float(config.value('api', 'google_interval') or 2)))
        except (ValueError, TypeError):
            google_transport.interval = 2.0
        return Response(*translate_google(text, language.google if language else None, cancel))

    @staticmethod
    def __mymemory(text: str) -> Response:
        if len(text.encode('utf-8')) > 500:
            return Response(404, interface.text('Errors', 'A maximum of 500 UTF-8 bytes is allowed.'))

        src = languages.source
        dst = languages.destination

        if src and src.google and dst and dst.google:
            payload = {
                'langpair': '{}|{}'.format(src.google, dst.google),
                'q': text
            }

            url = 'https://api.mymemory.translated.net/get'
            ua = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36')

            try:
                req = requests.get(url, params=payload, headers={'User-Agent': ua}, timeout=10)
                if req.status_code == 200:
                    content = req.json()
                    status = int(content.get('responseStatus', 200))
                    if status != 200 or content.get('quotaFinished'):
                        return Response(status if status != 200 else 429, 'MyMemory rejected the request or exhausted its quota.')
                    return Response(200, content['responseData']['translatedText'])
                else:
                    return Response(req.status_code,
                                    interface.text('Errors', 'Translation failed with error code: {}').format(
                                        req.status_code))
            except Exception as e:
                return Response(500, 'Translation service returned an invalid response or the connection failed.')

        return Response(404, interface.text('Errors', 'Language code not found!'))



translator = Translator()
