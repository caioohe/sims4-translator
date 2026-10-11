from types import SimpleNamespace
import pytest
from utils.recovery import RecoveryStore, atomic_write


def test_checkpoint_language_and_source(tmp_path):
    store = RecoveryStore(tmp_path)
    item = SimpleNamespace(package='synthetic', resource=SimpleNamespace(group=0, instance=1),
                           id=5, source='Hello', translate='Olá')
    store.save([item], 'ENG_US', 'POR_BR')
    assert store.load('synthetic', 'ENG_US', 'POR_BR')[store.key(item)] == {
        'source':'Hello', 'translation':'Olá'}
    assert store.load('synthetic', 'ENG_US', 'RUS_RU') == {}


def test_atomic_failure_retains_previous_file(tmp_path, monkeypatch):
    path = tmp_path / 'checkpoint'
    path.write_bytes(b'old')
    monkeypatch.setattr('os.replace', lambda *args: (_ for _ in ()).throw(OSError('disk error')))
    with pytest.raises(OSError):
        atomic_write(path, b'new')
    assert path.read_bytes() == b'old'
    assert list(tmp_path.iterdir()) == [path]
