from fastapi import FastAPI
from pydantic import ValidationError

from learning_os.config import get_settings

app = FastAPI(title="Personal Learning OS")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "learning-os"}


@app.get("/health")
def health() -> dict[str, object]:
    try:
        settings = get_settings()
    except ValidationError:
        return {"status": "ok", "config_loaded": False}

    return {
        "status": "ok",
        "config_loaded": True,
        "vault_path_exists": settings.vault_path.exists(),
        "openai_api_key_set": settings.openai_api_key is not None,
    }


def run() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
