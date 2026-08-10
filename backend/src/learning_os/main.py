from fastapi import FastAPI

app = FastAPI(title="Personal Learning OS")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "learning-os"}


def run() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
