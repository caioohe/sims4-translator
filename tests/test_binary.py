import pytest
from packer import Packer
from packer.stbl import Stbl
from packer.resource import ResourceID
from packer.dbpf import DbpfPackage


def test_unicode_stbl_package_roundtrip(tmp_path):
    rid = ResourceID(0, 123, 0x220557DA)
    table = Stbl(rid)
    table.add(0, 'Olá 漢字 😀 {0.Name} <b>ok</b>')
    table.add(1, '')
    path = tmp_path / 'synthetic.package'
    with DbpfPackage.write(path) as package:
        package.put(rid, table.binary)
    with DbpfPackage.read(path) as package:
        assert Stbl(rid, package[rid].content).strings == table._strings


def test_truncated_stbl_rejected():
    table = Stbl(None); table.add(1, 'abc')
    with pytest.raises(ValueError, match='Truncated'):
        Stbl(None, table.binary[:-1]).strings


def test_truncated_integer_rejected():
    with pytest.raises(ValueError):
        Packer(b'\x01').get_uint32()


def test_package_write_failure_preserves_target(tmp_path):
    path = tmp_path / 'existing.package'
    path.write_bytes(b'original')
    with pytest.raises(RuntimeError):
        with DbpfPackage.write(path):
            raise RuntimeError('export failed')
    assert path.read_bytes() == b'original'


def test_finalization_keeps_unreplaced_destination_and_empty_resource(tmp_path, monkeypatch):
    from storages.packages import PackagesStorage
    from singletons.config import config
    source = tmp_path / 'source.package'; target = tmp_path / 'target.package'
    destination = ResourceID(0, 0x1100000000000123, 0x220557DA)
    other = ResourceID(0, 7, 0x12345678)
    table = Stbl(destination); table.add(1, 'Olá')
    with DbpfPackage.write(source) as package:
        package.put(destination, table.binary); package.put(other, b'')
    monkeypatch.setattr(config, 'value', lambda section, option: {
        ('translation','destination'):'POR_BR', ('save','backup'):False}.get((section,option)))
    fake_storage = type('Storage', (), {'get_stbl':lambda self, convert: {}})()
    PackagesStorage.finalize(fake_storage, source, target)
    with DbpfPackage.read(target) as package:
        assert package[destination].content == table.binary
        assert package[other].content == b''


def test_search_stbl_does_not_hide_other_resources(tmp_path):
    stbl = ResourceID(0,1,0x220557DA); other = ResourceID(0,2,0x12345678)
    path = tmp_path / 'mixed.package'
    with DbpfPackage.write(path) as package:
        package.put(stbl, b'a'); package.put(other, b'b')
    with DbpfPackage.read(path) as package:
        assert list(package.search_stbl()) == [stbl]
        assert set(package.search()) == {stbl, other}
        assert package[other].content == b'b'


def test_backup_preserves_original_and_previous_backup(tmp_path):
    from storages.container import Container
    path = tmp_path / 'mod.package'; path.write_bytes(b'current')
    backup = tmp_path / 'mod.package.backup'; backup.write_bytes(b'previous')
    created = Container(str(path)).backup()
    assert path.read_bytes() == b'current'
    assert backup.read_bytes() == b'previous'
    assert open(created,'rb').read() == b'current'
