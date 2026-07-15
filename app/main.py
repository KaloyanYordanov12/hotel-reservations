from fastapi import FastAPI

app = FastAPI(title="Hotel Reservations")


@app.get("/health")
def health():
    return {"status": "ok"}
