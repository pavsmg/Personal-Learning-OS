"""decisions.md #63: learning-os-observations list/review/history -- offline."""

import pytest

from learning_os.mistakes import record_evidence, store
from learning_os.mistakes.models import Evidence
from learning_os.mistakes.observations_cli import run


def _evidence(**overrides):
    from datetime import UTC, datetime

    defaults = dict(
        domain="physics",
        concept="Force",
        timestamp=datetime.now(UTC),
        outcome="incorrect",
        quality=0.9,
        source="session_grading",
        session_id="s1",
    )
    defaults.update(overrides)
    return Evidence(**defaults)


def _run_cli(monkeypatch, capsys, argv):
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as exc:
        run()
    return exc.value.code, capsys.readouterr()


def test_list_reports_no_observations(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    code, out = _run_cli(monkeypatch, capsys, ["learning-os-observations", "list"])
    assert code == 0
    assert "No observations found." in out.out


def test_list_shows_reviewed_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    record_evidence([_evidence()])
    from learning_os.mistakes import record_evidence_review

    record_evidence_review(session_id="s1", concept="Force", new_outcome="correct", reason="verified")

    code, out = _run_cli(monkeypatch, capsys, ["learning-os-observations", "list", "--session", "s1"])
    assert code == 0
    assert "correct" in out.out and "[reviewed]" in out.out and "(graded incorrect)" in out.out


def test_review_corrects_outcome(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    record_evidence([_evidence()])

    code, out = _run_cli(
        monkeypatch,
        capsys,
        [
            "learning-os-observations",
            "review",
            "--session",
            "s1",
            "--concept",
            "force",
            "--outcome",
            "partial",
            "--reason",
            "half the derivation was right",
        ],
    )
    assert code == 0
    assert "incorrect -> partial" in out.out
    assert store.query_evidence_effective()[0].outcome == "partial"


def test_review_unknown_row_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    code, out = _run_cli(
        monkeypatch,
        capsys,
        [
            "learning-os-observations",
            "review",
            "--session",
            "nope",
            "--concept",
            "Force",
            "--outcome",
            "correct",
            "--reason",
            "x",
        ],
    )
    assert code == 1
    assert "error:" in out.err


def test_history_shows_review_trail(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    record_evidence([_evidence()])
    from learning_os.mistakes import record_evidence_review

    record_evidence_review(session_id="s1", concept="Force", new_outcome="correct", reason="verified")

    code, out = _run_cli(monkeypatch, capsys, ["learning-os-observations", "history"])
    assert code == 0
    assert "incorrect -> correct" in out.out and "verified" in out.out
