from pathlib import Path

import pytest

from learning_os.sessions.service import create_session

REAL_VAULT_PATH = Path("~/Documents/Obsidian-Digital-Brain").expanduser()

pytestmark = pytest.mark.skipif(
    not REAL_VAULT_PATH.exists(),
    reason="Real Obsidian vault not present on this machine",
)


@pytest.fixture(autouse=True)
def _point_at_real_vault(monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(REAL_VAULT_PATH))


def test_create_session_grounded_in_real_vault_content():
    plan = create_session("Adam optimizer")

    assert plan.concepts[0] == "Adam optimizer"
    assert "Gradient descent" in plan.concepts
