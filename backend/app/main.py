from fastapi import FastAPI

app = FastAPI(title="Real Estate AI Assistant")


@app.get("/api/health")
def health():
    return {"status": "ok"}
