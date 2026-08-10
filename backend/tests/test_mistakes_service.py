import pytest

from learning_os.mistakes.service import get_recent_mistakes, save_mistake, search_mistakes


def test_save_mistake_not_implemented():
    with pytest.raises(NotImplementedError):
        save_mistake("concept", "explanation", "category", "high", 0.5)


def test_search_mistakes_not_implemented():
    with pytest.raises(NotImplementedError):
        search_mistakes("query")


def test_get_recent_mistakes_not_implemented():
    with pytest.raises(NotImplementedError):
        get_recent_mistakes()
