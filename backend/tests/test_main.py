from fastapi.testclient import TestClient

from learning_os.main import app


def test_root_reports_ok() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "learning-os"}


def test_health_reports_ok_without_config(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("VAULT_PATH", raising=False)
    # A real backend/.env can exist on a dev machine (it does — see .env.example)
    # and pydantic-settings reads that file directly, not just os.environ, so
    # deleting the env var alone doesn't guarantee "no config source". Run from
    # an empty directory so there's truly no .env to fall back to.
    monkeypatch.chdir(tmp_path)
    from learning_os.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "config_loaded": False}


def test_health_reports_config_when_vault_path_set(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    from learning_os.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["config_loaded"] is True
    assert body["vault_path_exists"] is True
