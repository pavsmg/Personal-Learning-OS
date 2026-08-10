import pytest

from learning_os.sessions.service import create_session, finish_session, summarize_session


def test_create_session_not_implemented():
    with pytest.raises(NotImplementedError):
        create_session("algorithms")


def test_finish_session_not_implemented():
    with pytest.raises(NotImplementedError):
        finish_session("session-1")


def test_summarize_session_not_implemented():
    with pytest.raises(NotImplementedError):
        summarize_session("session-1")
