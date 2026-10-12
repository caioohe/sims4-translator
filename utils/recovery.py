"""Private, atomic checkpoints. No API keys or source file modifications."""
import hashlib
import json
import os
import tempfile
from pathlib import Path


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class RecoveryStore:
    def __init__(self, directory='prefs/recovery'):
        self.directory = Path(directory)

    def _path(self, package, source_language, destination_language):
        identity = json.dumps([package, source_language, destination_language])
        return self.directory / (hashlib.sha256(identity.encode()).hexdigest() + '.json')

    def load(self, package, source_language, destination_language):
        path = self._path(package, source_language, destination_language)
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    @staticmethod
    def key(item):
        return f'{item.resource.group}:{item.resource.instance}:{item.id}'

    def save(self, items, source_language, destination_language):
        groups = {}
        for item in items:
            groups.setdefault(item.package, []).append(item)
        for package, records in groups.items():
            data = self.load(package, source_language, destination_language)
            for item in records:
                data[self.key(item)] = {'source':item.source, 'translation':item.translate}
            atomic_write(self._path(package, source_language, destination_language),
                         json.dumps(data, ensure_ascii=False).encode('utf-8'))


recovery = RecoveryStore()
