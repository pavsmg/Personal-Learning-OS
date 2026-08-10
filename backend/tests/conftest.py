import pytest

from learning_os.config import get_settings
from learning_os.retrieval.index import get_vault_index


@pytest.fixture(autouse=True)
def _clear_lru_caches():
    get_settings.cache_clear()
    get_vault_index.cache_clear()
    yield
    get_settings.cache_clear()
    get_vault_index.cache_clear()
