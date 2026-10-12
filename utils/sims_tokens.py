"""Tokenize TS4 syntax while leaving gender branch text translatable."""
import re

GENDER = re.compile(r'\{[MF]\d+\.')
SPECIAL = re.compile(r'<[^>]+>|\\[nrt]|\r\n|\n|\r|\t|[{}<>]')


def _balanced_end(text, start):
    depth = 0
    for index in range(start, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return index
    return None


def protect_sims(text):
    prefix = 'TS4GPH'
    while prefix in text:
        prefix += 'X'
    placeholders = {}

    def token(value):
        marker = f'{prefix}{len(placeholders)}END'
        placeholders[marker] = value
        return marker

    def scan(value, depth=0):
        if depth > 32:
            raise ValueError('TS4 token nesting is too deep.')
        result, index = [], 0
        while index < len(value):
            if value[index] == '{':
                end = _balanced_end(value, index)
                if end is not None:
                    gender = GENDER.match(value, index)
                    if gender:
                        result.extend([token(gender.group()), scan(value[gender.end():end], depth + 1), token('}')])
                    else:
                        result.append(token(value[index:end + 1]))
                    index = end + 1
                    continue
            special = SPECIAL.match(value, index)
            if special:
                result.append(token(special.group()))
                index = special.end()
            else:
                result.append(value[index])
                index += 1
        return ''.join(result)

    return scan(text), placeholders


def restore_sims(text, placeholders):
    if not isinstance(text, str):
        raise ValueError('Translation is not a string.')
    # No raw syntax was sent: generated syntax is always unexpected.
    if SPECIAL.search(text):
        raise ValueError('Gemini invented TS4 syntax or changed a protected line break.')
    if placeholders:
        prefix = next(iter(placeholders)).rsplit('0END', 1)[0]
        received = re.findall(re.escape(prefix) + r'\d+END', text)
        if received != list(placeholders):
            raise ValueError('Gemini changed, reordered or removed protected TS4 tokens.')
    for marker, value in placeholders.items():
        text = text.replace(marker, value)
    return text
