"""Legacy Google Translate HTML client; no private RPC or bot-block bypass."""
from html.parser import HTMLParser
import requests
from utils.http_policy import google_transport
from utils.translation import TranslationCancelled


class ResultParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.results = []
        self.current = []

    def handle_starttag(self, tag, attrs):
        if self.depth:
            if tag == 'br':
                self.current.append('\n')
            elif tag not in ('img','input','hr','meta','link'):
                self.depth += 1
        elif set(dict(attrs).get('class', '').split()) & {'t0','result-container'}:
            self.depth = 1
            self.current = []

    def handle_endtag(self, tag):
        if self.depth and tag not in ('br','img','input','hr','meta','link'):
            self.depth -= 1
            if self.depth == 0:
                self.results.append(''.join(self.current))

    def handle_data(self, data):
        if self.depth:
            self.current.append(data)


def translate_google(text, language, cancel=None):
    if not language:
        return 404, 'Google language code not configured.'
    try:
        response = google_transport.request('GET', 'https://translate.google.com/m',
            cancel=cancel, backoff=15, cooldown=60,
            params={'sl':'auto','tl':language,'q':text},
            headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36'},
            timeout=(5, 15))
        try:
            if response.status_code == 429:
                return 429, 'Google Translate temporarily limited automated requests (429). Wait before resuming, or select Gemini/DeepL. Completed translations are retained.'
            if response.status_code != 200:
                return response.status_code, f'Google Translate HTTP {response.status_code}. Original strings retained.'
            content = response.content.decode('utf-8')
        finally:
            response.close()
        lower = content.lower()
        if ('our systems have detected unusual traffic' in lower or 'g-recaptcha' in lower
                or 'id="captcha' in lower or "id='captcha" in lower):
            google_transport.defer(60)
            return 429, 'Google requires browser verification. Automatic translation paused; no challenge was bypassed.'
        parser = ResultParser()
        parser.feed(content)
        parser.close()
        if len(parser.results) != 1 or not parser.results[0]:
            return 422, 'Google returned no usable translation (page changed or consent/sign-in required). Original strings retained.'
        return 200, parser.results[0]
    except TranslationCancelled:
        return 499, 'Translation cancelled.'
    except requests.RequestException:
        return 503, 'Google Translate connection failed or timed out. Original strings retained.'
    except (UnicodeError, ValueError):
        return 422, 'Google returned invalid HTML. Original strings retained.'
