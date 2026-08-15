from learning_os import session_log as session_log_module
from learning_os.session_log import SessionLog


def test_session_log_writes_timestamped_lines_to_file(tmp_path, monkeypatch):
    monkeypatch.setattr(session_log_module, "LOG_DIR", tmp_path / "logs")

    log = SessionLog("session-123")
    log.write("USER: hello")
    log.write("ASSISTANT: hi there")
    log.close()

    content = (tmp_path / "logs" / "session-123.log").read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("USER: hello")
    assert lines[1].endswith("ASSISTANT: hi there")
    assert lines[0].startswith("[")  # timestamp prefix


def test_session_log_creates_log_dir_if_missing(tmp_path, monkeypatch):
    log_dir = tmp_path / "nested" / "logs"
    monkeypatch.setattr(session_log_module, "LOG_DIR", log_dir)

    SessionLog("session-456").close()

    assert log_dir.exists()
    assert (log_dir / "session-456.log").exists()
