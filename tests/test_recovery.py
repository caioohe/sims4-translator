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


def test_recovery_on_package_reopen_only_matches_source(qapp, tmp_path, monkeypatch):
    from packer.stbl import Stbl
    from packer.dbpf import DbpfPackage
    from packer.resource import ResourceID
    from storages.packages import PackagesStorage
    from storages.dictionaries import DictionariesStorage
    from singletons.state import app_state
    from singletons.config import config
    from utils.constants import FLAG_VALIDATED, FLAG_UNVALIDATED
    import storages.packages as module
    monkeypatch.setattr(config, 'value', lambda section, option: {
        ('translation','source'):'ENG_US', ('translation','destination'):'POR_BR',
        ('group','original'):True, ('dictionaries','strong'):True,
        ('interface','theme'):'light'}.get((section,option)))
    store = RecoveryStore(tmp_path / 'recovery')
    monkeypatch.setattr(module, 'recovery', store)
    monkeypatch.setattr(app_state, 'current_package', None)
    monkeypatch.setattr(app_state, 'current_instance', 0)
    monkeypatch.setattr(app_state, 'dictionaries_storage', DictionariesStorage())
    path = tmp_path / 'mod.package'
    rid = ResourceID(0, 42, 0x220557DA)
    table = Stbl(rid); table.add(1, 'Hello'); table.add(2, 'Changed')
    with DbpfPackage.write(path) as package:
        package.put(rid, table.binary)
    first = PackagesStorage(); first.load(str(path))
    records = first.items(); records[0].translate = 'Olá'; records[1].source_old = None
    store.save(records, 'ENG_US', 'POR_BR')
    # Source change invalidates the second recovered entry.
    saved = store.load(records[0].package, 'ENG_US','POR_BR')
    saved[store.key(records[1])]['source'] = 'Old source'
    atomic_write(store._path(records[0].package,'ENG_US','POR_BR'),
                 __import__('json').dumps(saved).encode())
    reopened = PackagesStorage(); reopened.load(str(path))
    assert reopened.items()[0].translate == 'Olá'
    assert reopened.items()[0].flag == FLAG_VALIDATED
    assert reopened.items()[1].flag == FLAG_UNVALIDATED
