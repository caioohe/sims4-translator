import pytest
from singletons.config import ConfigManager


def test_keys_roundtrip_and_stable_path(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    config=ConfigManager()
    for name in ('gemini_key','microsoft_key','deepl_key'):
        config.set_value('api',name,'00123')
    elsewhere=tmp_path/'elsewhere';elsewhere.mkdir();monkeypatch.chdir(elsewhere)
    config.save()
    assert not (elsewhere/'prefs').exists()
    monkeypatch.chdir(tmp_path)
    loaded=ConfigManager()
    for name in ('gemini_key','microsoft_key','deepl_key'):
        assert loaded.value('api',name) == '00123'


def test_atomic_save_failure_retains_existing_config(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    config=ConfigManager();config.set_value('api','gemini_key','saved-key');config.save()
    before=(tmp_path/'prefs/config.xml').read_bytes()
    config.set_value('api','gemini_key','new-key')
    monkeypatch.setattr('os.replace',lambda *args:(_ for _ in ()).throw(OSError('disk failure')))
    with pytest.raises(OSError):config.save()
    assert (tmp_path/'prefs/config.xml').read_bytes() == before
    assert not list((tmp_path/'prefs').glob('.config-*'))
