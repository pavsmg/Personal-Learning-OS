import pytest

from learning_os import session_log as session_log_module
from learning_os.config import get_settings
from learning_os.retrieval.index import get_vault_index


@pytest.fixture(autouse=True)
def _isolate_session_logs(tmp_path, monkeypatch):
    """start_session now opens a real transcript log, so without this every
    test that starts a conversation would litter the repo's own logs/."""
    monkeypatch.setattr(session_log_module, "LOG_DIR", tmp_path / "logs")


@pytest.fixture(autouse=True)
def _clear_lru_caches():
    get_settings.cache_clear()
    get_vault_index.cache_clear()
    yield
    get_settings.cache_clear()
    get_vault_index.cache_clear()
